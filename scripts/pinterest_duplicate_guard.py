#!/usr/bin/env python3
"""
PINTEREST-DUPLICATE-GUARD – Premium-Wächter gegen Duplicate Pin-Texte (P4)

Zweck: Verhindert dauerhaft, dass zwei Artikel denselben pin_title oder
pin_description tragen – das häufigste Pinterest-Spam-Signal, das zum
Shadowban oder zur Meldung "Link leitet an Spam-Webseite weiter" führt.

- Prüft alle Artikel (inkl. Drafts) auf Duplikate
- Exit 1 bei Duplikaten (für CI-Gates)
- --fix heilt automatisch mit einzigartigen Premium-Texten
- Deterministisch + idempotent + Sabotage-geschützt

Einbindung:
  - Lokal: python3 scripts/pinterest_duplicate_guard.py --fix
  - CI:    python3 scripts/pinterest_duplicate_guard.py
  - Workflows: pinterest-watchdog, redaktions-standard, premium-governance

Agentur-Standard 2026: Jeder Pin-Text muss einzigartig sein – Titel ≤100,
Description ≤500, *Werbung-Prefix, Hashtags nach scripts/pinterest_hashtags.py
(max. 3, [a-z0-9], Block am Ende – eine Regel für alle Schreiber, #729).
"""
import glob
import os
import re
import sys
from collections import defaultdict

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
import pinterest_hashtags as ph  # noqa: E402  – Hashtag-SSOT (#729)
import reserve_schreibschutz as schutz  # noqa: E402  – #900
from post_utils import join_article  # noqa: E402  – Naht-SSOT (FM-Grenze)
DO_FIX = "--fix" in sys.argv

DESC_MAX = 500
TITLE_MAX = 100

def _read_posts():
    posts = []
    # Sortiert lesen. `glob` liefert die Reihenfolge des Dateisystems, und die
    # ist auf ext4 (Lokalrechner) eine andere als auf dem CI-Runner. Weil die
    # Heilung unten `group[1:]` anfasst, entschied die Reihenfolge darüber,
    # WELCHER Artikel eines Duplikat-Paars umgeschrieben wird: Stand der
    # bytegebundene Reserve-Entwurf auf Platz 0, blieb der normale Entwurf
    # ungeheilt (und umgekehrt). Ein Mess-/Heilwerkzeug, dessen Ergebnis von
    # der Verzeichnis-Reihenfolge abhängt, ist keine Messung. Ein Test
    # (`test_reserve_schreibschutz`) war deshalb lokal grün und in der CI rot.
    for path in sorted(glob.glob(os.path.join(BLOG_DIR, "content", "posts", "*", "index.md"))):
        content = open(path, encoding="utf-8").read()
        slug = os.path.basename(os.path.dirname(path))
        # Frontmatter extrahieren
        def fm_get(key, _c=content):
            m = re.search(rf'^{re.escape(key)}:\s*"(.*)"\s*$', _c, re.M)
            if m:
                return m.group(1)
            m = re.search(rf"^{re.escape(key)}:\s*'(.*)'\s*$", _c, re.M)
            if m:
                return m.group(1)
            m = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", _c, re.M)
            return m.group(1).strip() if m else ""
        def fm_list(key, _c=content):
            m = re.search(rf"^{re.escape(key)}:\s*\[(.*?)\]", _c, re.M)
            if m:
                return [k.strip().strip("\"'") for k in m.group(1).split(",") if k.strip()]
            raw = fm_get(key)
            return [k.strip() for k in raw.split(",")] if raw else []
        posts.append({
            "slug": slug,
            "path": path,
            "content": content,
            "title": fm_get("title") or slug,
            "description": fm_get("description") or "",
            "pin_title": fm_get("pin_title"),
            "pin_description": fm_get("pin_description"),
            "keywords": fm_list("keywords") or fm_list("tags"),
        })
    return posts

def _build_hashtags(keywords, slug):
    """Hashtags für einen neu erzeugten Pin-Text – Regel in der SSOT (#729)."""
    return ph.tags_bauen(keywords, slug)

def _unique_desc(slug, title, description, keywords, existing, attempt=0):
    base = (description or title or slug).strip()
    base = re.sub(r"\s+", " ", base).replace("&", "und")
    ctas = [
        "Jetzt Anleitung sichern!",
        "Jetzt checken und sparen!",
        "Jetzt Tipps entdecken!",
        "Jetzt lesen und bis zu 300 € sparen!",
        "Jetzt Guide sichern!",
    ]
    cta = ctas[(sum(ord(c) for c in slug) + attempt) % len(ctas)]
    hashtags = _build_hashtags(keywords, slug)
    ht = ph.als_text(hashtags)
    if attempt>0:
        base = base.rstrip(".") + f" – Variante {attempt+1} mit Checkliste."
    text = f"*Werbung | {base} {cta}"
    if ht:
        text += f" {ht}"
    if len(text) > DESC_MAX:
        budget = DESC_MAX - len(f"*Werbung |  {cta} {ht}") - 4
        budget = max(60, budget)
        trunc = base[:budget]
        sp = trunc.rfind(" ")
        if sp>30:
            trunc=trunc[:sp]
        text = f"*Werbung | {trunc}… {cta}"
        if ht:
            text+=f" {ht}"
    # Schlusskontrolle über die SSOT: ein Block, höchstens drei Tags, ≤500 –
    # auch ein erzeugter Text darf die Regel nicht erst nach dem Schreiben
    # verletzen (#729).
    text, _ = ph.heile(text)
    text=text[:DESC_MAX]
    if text in existing and attempt<10:
        return _unique_desc(slug, title, description, keywords, existing, attempt+1)
    return text

def _unique_title(slug, title, existing, attempt=0):
    base = (title or slug).strip()
    base = re.sub(r"\s+", " ", base)
    if attempt>0:
        suffixes = [" – Praxis-Guide", " – So sparst du", " – Schritt für Schritt", " – Jetzt vergleichen", f" – Teil {attempt+1}"]
        suf = suffixes[attempt % len(suffixes)]
        if len(base)+len(suf) <= TITLE_MAX:
            base+=suf
        else:
            base=base[:TITLE_MAX-len(suf)-1].rstrip()+"…"+suf
    base=base[:TITLE_MAX]
    if base in existing and attempt<10:
        return _unique_title(slug, title, existing, attempt+1)
    return base

def _fm_set(content, key, value):
    v = str(value).replace('"', '\\"')
    line = f'{key}: "{v}"'
    if re.search(rf"^{re.escape(key)}:\s*", content, re.M):
        return re.sub(rf"^{re.escape(key)}:\s*.*$", line, content, count=1, flags=re.M)
    else:
        parts = content.split("---",2)
        if len(parts)>=3:
            fm=parts[1]
            body=parts[2]
            fm2=fm.rstrip("\n")+"\n"+line+"\n"
            return join_article(fm2, body)
        return content

def main():
    posts = _read_posts()
    desc_map = defaultdict(list)
    title_map = defaultdict(list)
    for p in posts:
        if p["pin_description"]:
            desc_map[p["pin_description"]].append(p)
        if p["pin_title"]:
            title_map[p["pin_title"]].append(p)

    problems = []
    fixed = 0
    # Wie viele Duplikat-Gruppen überhaupt heilbar sind (mindestens zwei
    # nicht-bytegebundene Mitglieder). Nur daran wird der Erfolg gemessen.
    heilbare_probleme = 0

    for d, group in desc_map.items():
        if len(group)>1:
            slugs = ", ".join(g["slug"] for g in group)
            problems.append(("P4", slugs, f"DUPLIKAT pin_description: {d[:80]}…"))
            if DO_FIX:
                existing = set(desc_map.keys())
                # EINEN Eintrag der Gruppe lassen wir stehen, die übrigen
                # bekommen einen eigenen Text. Welcher stehen bleibt, darf
                # nicht die Verzeichnis-Reihenfolge entscheiden: Ist der
                # erste bytegebunden (#900), muss der NÄCHSTE heilbare
                # weichen – sonst bliebe die ganze Gruppe ungeheilt und der
                # normale Entwurf behielte stillschweigend das Duplikat.
                # Geschützte Entwürfe werden deshalb ZUERST gemeldet und für
                # die Heilung übersprungen, nicht die Gruppe abgeschnitten.
                heilbar = []
                for g in group:
                    if schutz.ist_bytegebunden(g["content"]):
                        # #900: bytegebundene Reserve-Entwürfe nicht anfassen.
                        print("  ⏸ " + schutz.schutzvermerk(g["slug"], "pinterest_duplicate_guard.py"))
                    else:
                        heilbar.append(g)
                # Bleibt überhaupt ein Duplikat übrig, das jemand ändern
                # KÖNNTE? Nur dann ist die Gruppe heilbar.
                #
                # Die Regel darf nicht „ab dem zweiten Eintrag heilen" lauten:
                # Steht der bytegebundene Reserve-Entwurf allein neben einem
                # normalen, gäbe es keinen zweiten heilbaren – der normale
                # behielte das Duplikat und der Lauf meldete trotzdem „0
                # geheilt". Genau so war `test_normaler_entwurf_wird_
                # weiterhin_eindeutig` in der CI rot und lokal grün.
                #
                # Deshalb: von den NICHT geschützten bleibt genau einer
                # stehen (der erste), alle anderen weichen. Geschützte
                # zählen dabei weder als „der eine" noch als heilbar.
                ziel = heilbar[1:] if len(heilbar) > 1 else heilbar
                if ziel:
                    heilbare_probleme += 1
                for g in ziel:
                    new_desc = _unique_desc(g["slug"], g["title"], g["description"], g["keywords"], existing)
                    new_content = _fm_set(g["content"], "pin_description", new_desc)
                    open(g["path"], "w", encoding="utf-8").write(new_content)
                    existing.add(new_desc)
                    fixed+=1
                    print(f"  ✅ Fixed P4 {g['slug']}")

    # Rebuild after fix
    if DO_FIX and fixed:
        posts = _read_posts()
        desc_map = defaultdict(list)
        title_map = defaultdict(list)
        for p in posts:
            if p["pin_description"]:
                desc_map[p["pin_description"]].append(p)
            if p["pin_title"]:
                title_map[p["pin_title"]].append(p)

    for t, group in title_map.items():
        if len(group)>1:
            slugs = ", ".join(g["slug"] for g in group)
            problems.append(("P4b", slugs, f"DUPLIKAT pin_title: {t}"))
            if DO_FIX:
                existing = set(title_map.keys())
                heilbar = []
                for g in group:
                    if schutz.ist_bytegebunden(g["content"]):
                        print("  ⏸ " + schutz.schutzvermerk(g["slug"], "pinterest_duplicate_guard.py"))
                    else:
                        heilbar.append(g)
                ziel = heilbar[1:] if len(heilbar) > 1 else heilbar
                if ziel:
                    heilbare_probleme += 1
                for g in ziel:
                    new_title = _unique_title(g["slug"], g["title"], existing)
                    new_content = _fm_set(g["content"], "pin_title", new_title)
                    open(g["path"], "w", encoding="utf-8").write(new_content)
                    existing.add(new_title)
                    fixed+=1
                    print(f"  ✅ Fixed P4b {g['slug']}")

    if problems:
        print(f"❌ {len(problems)} Pinterest-Duplikate gefunden:")
        for code, slugs, msg in problems:
            print(f"  [{code}] {slugs}: {msg}")
        if DO_FIX:
            print(f"✅ {fixed} Duplikate geheilt (dauerhaft)")
            # Eine Gruppe, in der ALLE Mitglieder bytegebunden sind, ist
            # bewusst nicht heilbar – das ist kein Fehlschlag, sondern der
            # Schreibschutz bei der Arbeit. Gezählt wird deshalb nur, was
            # überhaupt heilbar war.
            return 0 if fixed >= heilbare_probleme else 1
        return 1
    else:
        print("✅ Keine Pinterest-Duplikate – alle Pin-Texte einzigartig (Premium-Level)")
        return 0

if __name__ == "__main__":
    sys.exit(main())
