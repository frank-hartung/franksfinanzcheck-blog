// ============================================================
//  KI-ASSISTENT – Client (2026-10-08)
//  ------------------------------------------------------------
//  Benutzerfrontender Chat für FranksFinanzcheck.de.
//  DSGVO: session-only, kein Tracking, keine Cookies.
//  Sprache: Deutsch.
//  Quelle: Erste Partei, keine externen Abhängigkeiten.
// ============================================================
(function () {
  "use strict";

  // ---- Konfiguration ----
  const CONFIG_EL = document.getElementById("ff-ki-config");
  if (!CONFIG_EL) return;

  let CFG;
  try {
    CFG = JSON.parse(CONFIG_EL.textContent);
  } catch {
    return;
  }

  const ENDPOINT = CFG.endpoint || "";
  const MAX_HISTORY = 10; // Nachrichten für Kontext
  const MAX_QUESTION = 2000;
  // Zeitlimit je Anfrage (R4). Der Worker probiert bis zu vier Provider
  // nacheinander, je 30 s (cloudflare/ki-assistent/worker.js). Darunter
  // würde ein erfolgreicher Failover abgeschnitten – darüber hinaus wartet
  // der Leser ohne Rückmeldung. 4 × 30 s + Puffer.
  const ANTWORT_ZEITLIMIT_MS = 130000;

  // ---- State ----
  let history = []; // {role, content}
  let isOpen = false;
  let isSending = false;

  // ---- DOM-Elemente ----
  const trigger = document.getElementById("ff-ki-trigger");
  const panel = document.getElementById("ff-ki-panel");
  const messages = document.getElementById("ff-ki-messages");
  const input = document.getElementById("ff-ki-input-field");
  const sendBtn = document.getElementById("ff-ki-send");
  const closeBtn = document.getElementById("ff-ki-close");

  if (!trigger || !panel || !messages || !input || !sendBtn || !closeBtn) return;

  // ---- Hilfsfunktionen ----
  // Antworten werden NIE als HTML-Text eingesetzt (R7): Jeder Teil landet als
  // textContent bzw. als eigens erzeugtes Element. Fremder oder berechneter
  // Text kann so nicht als Markup ins Dokument geraten.

  // Inline-Auszeichnung: **fett**, `code`, *kursiv* (in dieser Reihenfolge geprüft).
  function inlineNodes(text, parent) {
    const muster = /\*\*(.+?)\*\*|`(.+?)`|(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g;
    let letzter = 0;
    let treffer;
    while ((treffer = muster.exec(text)) !== null) {
      if (treffer.index > letzter) {
        parent.appendChild(document.createTextNode(text.slice(letzter, treffer.index)));
      }
      let el;
      if (treffer[1] !== undefined) {
        el = document.createElement("strong");
        el.textContent = treffer[1];
      } else if (treffer[2] !== undefined) {
        el = document.createElement("code");
        el.textContent = treffer[2];
      } else {
        el = document.createElement("em");
        el.textContent = treffer[3];
      }
      parent.appendChild(el);
      letzter = muster.lastIndex;
    }
    if (letzter < text.length) {
      parent.appendChild(document.createTextNode(text.slice(letzter)));
    }
  }

  // Absätze (Leerzeile), Zeilenumbrüche, Listen (- oder * am Zeilenanfang).
  function renderAnswer(text, container) {
    String(text)
      .split(/\n\n+/)
      .forEach(function (absatz) {
        const p = document.createElement("p");
        absatz.split("\n").forEach(function (zeile, i) {
          if (i > 0) p.appendChild(document.createElement("br"));
          const listenEintrag = zeile.match(/^[*-]\s+(.+)/);
          inlineNodes(listenEintrag ? "• " + listenEintrag[1] : zeile, p);
        });
        container.appendChild(p);
      });
  }

  function scrollToBottom() {
    requestAnimationFrame(function () {
      messages.scrollTop = messages.scrollHeight;
    });
  }

  function addMessage(text, type, formatiert) {
    const el = document.createElement("div");
    el.className = "ff-ki-msg ff-ki-msg--" + type;
    if (formatiert) {
      renderAnswer(text, el);
    } else {
      el.textContent = text;
    }
    el.setAttribute("role", type === "user" ? "status" : "log");
    messages.appendChild(el);
    scrollToBottom();
    return el;
  }

  function showTyping() {
    const el = document.createElement("div");
    el.className = "ff-ki-typing";
    el.id = "ff-ki-typing";
    el.setAttribute("aria-label", "Assistent schreibt…");
    for (let i = 0; i < 3; i++) {
      const punkt = document.createElement("span");
      punkt.className = "ff-ki-typing__dot";
      el.appendChild(punkt);
    }
    messages.appendChild(el);
    scrollToBottom();
  }

  function hideTyping() {
    const el = document.getElementById("ff-ki-typing");
    if (el) el.remove();
  }

  // ---- Suggestions entfernen (nach erstem Senden) ----
  function removeSuggestions() {
    const sug = messages.querySelector(".ff-ki-suggestions");
    if (sug) sug.remove();
  }

  // ---- Panel öffnen/schließen ----
  function openPanel() {
    isOpen = true;
    panel.setAttribute("aria-hidden", "false");
    trigger.setAttribute("aria-expanded", "true");
    // Fokus ins Eingabefeld (verzögert für Animation)
    setTimeout(function () {
      input.focus();
    }, 250);
  }

  function closePanel() {
    isOpen = false;
    panel.setAttribute("aria-hidden", "true");
    trigger.setAttribute("aria-expanded", "false");
    trigger.focus();
  }

  // ---- Nachricht senden ----
  async function sendMessage() {
    const question = input.value.trim();
    if (!question || question.length < 3 || isSending) return;

    if (question.length > MAX_QUESTION) {
      addMessage(
        "Die Frage ist zu lang. Bitte kürze sie auf " +
          MAX_QUESTION +
          " Zeichen.",
        "error"
      );
      return;
    }

    removeSuggestions();
    isSending = true;
    input.value = "";
    input.style.height = "auto";
    sendBtn.disabled = true;
    input.disabled = true;

    // User-Nachricht anzeigen
    addMessage(question, "user");
    history.push({ role: "user", content: question });

    // Typing-Indicator
    showTyping();

    const steuerung = new AbortController();
    const zeitlimit = setTimeout(function () {
      steuerung.abort();
    }, ANTWORT_ZEITLIMIT_MS);

    try {
      const resp = await fetch(ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question,
          history: history.slice(-MAX_HISTORY),
        }),
        signal: steuerung.signal,
      });

      hideTyping();

      if (!resp.ok) {
        let errorMsg =
          "Der Assistent ist gerade nicht erreichbar. Bitte versuch es später erneut.";
        try {
          const errData = await resp.json();
          if (errData.error) errorMsg = errData.error;
        } catch {
          /* Default-Text */
        }
        addMessage(errorMsg, "error");
        return;
      }

      const data = await resp.json();

      if (data.answer) {
        addMessage(data.answer, "bot", true);
        history.push({ role: "assistant", content: data.answer });
      } else {
        addMessage(
          "Der Assistent konnte keine Antwort finden. Bitte formuliere die Frage anders.",
          "error"
        );
      }
    } catch (err) {
      hideTyping();
      if (err && err.name === "AbortError") {
        addMessage(
          "Der Assistent hat zu lange gebraucht. Bitte stell die Frage gleich noch einmal.",
          "error"
        );
      } else {
        addMessage(
          "Verbindungsfehler. Bitte prüfe deine Internetverbindung und versuch es erneut.",
          "error"
        );
      }
    } finally {
      clearTimeout(zeitlimit);
      isSending = false;
      sendBtn.disabled = false;
      input.disabled = false;
      input.focus();
    }
  }

  // ---- Event Handler ----
  trigger.addEventListener("click", function () {
    if (isOpen) {
      closePanel();
    } else {
      openPanel();
    }
  });

  closeBtn.addEventListener("click", closePanel);

  sendBtn.addEventListener("click", sendMessage);

  // Enter zum Senden (Shift+Enter für neue Zeile)
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Textarea auto-resize
  input.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 120) + "px";
  });

  // Escape zum Schließen
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && isOpen) {
      closePanel();
    }
  });

  // Click außerhalb schließt (nur auf Mobilgeräten sinnvoll)
  document.addEventListener("click", function (e) {
    if (
      isOpen &&
      !panel.contains(e.target) &&
      !trigger.contains(e.target)
    ) {
      closePanel();
    }
  });

  // Suggestion-Buttons
  messages.addEventListener("click", function (e) {
    const btn = e.target.closest(".ff-ki-suggestion");
    if (btn) {
      input.value = btn.textContent;
      sendMessage();
    }
  });

  // ---- Initialer Zustand ----
  panel.setAttribute("aria-hidden", "true");
  trigger.setAttribute("aria-expanded", "false");
  sendBtn.disabled = false;
})();