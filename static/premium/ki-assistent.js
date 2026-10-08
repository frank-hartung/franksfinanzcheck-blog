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
  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // Einfache Markdown-ähnliche Formatierung (kein HTML-Injection)
  function formatAnswer(text) {
    let html = escapeHtml(text);
    // Bold: **text**
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    // Italic: *text*
    html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");
    // Inline code: `text`
    html = html.replace(/`(.+?)`/g, "<code>$1</code>");
    // Listen: Zeilen mit - oder * am Anfang
    html = html.replace(/(^|\n)[*-]\s+(.+)/g, function (m, pre, item) {
      return pre + "• " + item;
    });
    // Absätze
    html = html.replace(/\n\n+/g, "</p><p>");
    html = html.replace(/\n/g, "<br>");
    return "<p>" + html + "</p>";
  }

  function scrollToBottom() {
    requestAnimationFrame(function () {
      messages.scrollTop = messages.scrollHeight;
    });
  }

  function addMessage(text, type, isHtml) {
    const el = document.createElement("div");
    el.className = "ff-ki-msg ff-ki-msg--" + type;
    if (isHtml) {
      el.innerHTML = text;
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
    el.innerHTML =
      '<span class="ff-ki-typing__dot"></span>' +
      '<span class="ff-ki-typing__dot"></span>' +
      '<span class="ff-ki-typing__dot"></span>';
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

    try {
      const resp = await fetch(ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question,
          history: history.slice(-MAX_HISTORY),
        }),
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
        addMessage(formatAnswer(data.answer), "bot", true);
        history.push({ role: "assistant", content: data.answer });
      } else {
        addMessage(
          "Der Assistent konnte keine Antwort finden. Bitte formuliere die Frage anders.",
          "error"
        );
      }
    } catch {
      hideTyping();
      addMessage(
        "Verbindungsfehler. Bitte prüfe deine Internetverbindung und versuch es erneut.",
        "error"
      );
    } finally {
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