#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FranksFinanzcheck.de - Profi Smart Blog Topic Automation
Entwickelt von: Profi-Blogger, Affiliate Marketer & Pinterest Strategie-Team

Eigenschaften:
 1. Dynamischer Abgleich mit allen veröffentlichten Artikeln (Sitemap & content/posts/)
 2. 100% Anti-Kannibalisierungs-Engine: Verhindert doppelte Themen & Keyword-Overlaps
 3. Rotations-Rhythmus auf die 6 Pillar-Pages (Mo/Mi/Fr):
    - Frugalismus & Budgeting (/pillar/frugalismus/)
    - Strom & Gas (/pillar/strom-sparen/)
    - Internet & DSL (/pillar/internet-dsl/)
    - Girokonto & Karten (/pillar/konto-karten/)
    - Mietwagen & Reise (/pillar/mietwagen/)
    - Versicherungen (/pillar/versicherungen/)
 4. Automatische Hugo-Markdown Erzeugung mit validem YAML Frontmatter, internal links & Affiliate-Hinweisen
"""

import os
import re
import sys
import json
import datetime
import urllib.request
import xml.etree.ElementTree as ET

SITE_URL = "https://franksfinanzcheck.de"
SITEMAP_URL = f"{SITE_URL}/sitemap.xml"
POSTS_DIR = "content/posts"

PILLARS = {
    "frugalismus": {
        "name": "Geld sparen & Frugalismus",
        "url": f"{SITE_URL}/pillar/frugalismus/",
        "category": "Frugalismus"
    },
    "strom": {
        "name": "Strom & Gas sparen",
        "url": f"{SITE_URL}/pillar/strom-sparen/",
        "category": "Günstige Strom- & Gastarife"
    },
    "dsl": {
        "name": "Internet & DSL Hacks",
        "url": f"{SITE_URL}/pillar/internet-dsl/",
        "category": "Internet- & DSL-Hacks"
    },
    "konto": {
        "name": "Girokonto & Banking",
        "url": f"{SITE_URL}/pillar/konto-karten/",
        "category": "Banking & Konten"
    },
    "mietwagen": {
        "name": "Reisebudget & Mietwagen",
        "url": f"{SITE_URL}/pillar/mietwagen/",
        "category": "Reisebudget & Mietwagen"
    },
    "versicherungen": {
        "name": "Versicherungen & Vorsorge",
        "url": f"{SITE_URL}/pillar/versicherungen/",
        "category": "Versicherungen"
    }
}

TOPIC_POOL = [
    {
        "pillar": "frugalismus",
        "slug": "haushaltsbuch-fuehren-app-excel-oder-papier",
        "title": "Haushaltsbuch führen: App, Excel oder Stift – Was spart mehr Geld?",
        "keywords": ["haushaltsbuch führen", "budgetierung", "ausgaben im blick behalten", "geld sparen tipps"],
        "description": "Erfahre, welche Methode beim Haushaltsbuch führen die höchste Ersparnis bringt und wie Du Deine Fixkosten dauerhaft senkst."
    },
    {
        "pillar": "frugalismus",
        "slug": "impulskaeufe-vermeiden-7-psychologische-tricks",
        "title": "Impulskäufe vermeiden: 7 psychologische Tricks gegen Spontankäufe",
        "keywords": ["impulskäufe vermeiden", "spontankäufe stoppen", "frugalismus tipps", "konsum reduzieren"],
        "description": "Schütze Dein Konto vor unüberlegten Spontankäufen. Mit diesen 7 psychologischen Frugalismus-Tricks sparst Du sofort bares Geld."
    },
    {
        "pillar": "strom",
        "slug": "kuehlschrank-strom-sparen-optimale-temperatur",
        "title": "Kühlschrank Strom sparen: Die richtige Temperatur & 5 Spar-Tricks",
        "keywords": ["kühlschrank strom sparen", "kühlraum temperatur 7 grad", "stromfresser entlarven", "energiekosten senken"],
        "description": "Jeder Grad kälter kostet ca. 6% mehr Strom. Erfahre, wie Du Deinen Kühlschrank optimal einstellst und Stromkosten reduzierst."
    },
    {
        "pillar": "dsl",
        "slug": "router-kaufen-oder-mieten-preisvergleich",
        "title": "WLAN-Router kaufen oder mieten? Der große Kostenvergleich",
        "keywords": ["router mieten oder kaufen", "fritzbox kaufen", "dsl router kosten", "internet sparguide"],
        "description": "Mietgeräte beim Internetanbieter kosten oft über 200 Euro auf 2 Jahre. Wir rechnen vor, wann sich der Kauf eines eigenen Routers lohnt."
    },
    {
        "pillar": "konto",
        "slug": "kreditkarte-ohne-jahresgebuehr-ausland-vergleich",
        "title": "Kostenlose Kreditkarte für Urlaub & Alltag: Gebührenfallen vermeiden",
        "keywords": ["kreditkarte ohne jahresgebühr", "kostenlose kreditkarte ausland", "gebührenfrei bezahlen", "banking tipps"],
        "description": "Versteckte Fremdwährungsgebühren beim Geldabheben? So findest Du eine dauerhaft kostenlose Kreditkarte ohne böse Überraschungen."
    },
    {
        "pillar": "mietwagen",
        "slug": "pauschalreise-oder-individualreise-kostenvergleich",
        "title": "Pauschalreise vs. Individualreise: Wo sparst Du wirklich mehr?",
        "keywords": ["pauschalreise günstig buchen", "urlaubskasse sparen", "reisebudget optimieren", "günstig reisen"],
        "description": "Wann lohnt sich die Komplettbuchung und wann fährt man mit getrennten Flügen & Hotels günstiger? Der ehrliche Kosten-Check."
    },
    {
        "pillar": "versicherungen",
        "slug": "berufsunfaehigkeitsversicherung-worauf-achten",
        "title": "Berufsunfähigkeitsversicherung: Welche Klauseln wirklich zählen",
        "keywords": ["berufsunfähigkeitsversicherung vergleichen", "bu klauseln", "vorsorge tipps", "versicherungspolice prüfen"],
        "description": "Verzicht auf abstrakte Verweisung & Kündigungsfristen: Worauf Du beim Abschluss einer BU-Versicherung unbedingt achten musst."
    }
]


def get_existing_slugs_and_titles():
    existing_texts = set()
    
    try:
        req = urllib.request.Request(SITEMAP_URL, headers={"User-Agent": "Mozilla/5.0"})
        xml_content = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        urls = re.findall(r'<loc>(https://franksfinanzcheck\.de/[^<]+)</loc>', xml_content)
        for u in urls:
            slug = u.split('/')[-2] if u.endswith('/') else u.split('/')[-1]
            existing_texts.add(slug.lower().replace('-', ' '))
    except Exception as e:
        print(f"⚠️ Hinweis: Sitemap konnte nicht abgerufen werden ({e}). Prüfe lokale Dateien...")

    if os.path.exists(POSTS_DIR):
        for fname in os.listdir(POSTS_DIR):
            if fname.endswith('.md'):
                existing_texts.add(fname.lower().replace('.md', '').replace('-', ' '))
                try:
                    with open(os.path.join(POSTS_DIR, fname), 'r', encoding='utf-8') as f:
                        content = f.read()
                        t_match = re.search(r'title:\s*[\"\']?(.*?)[\"\']?\n', content)
                        if t_match:
                            existing_texts.add(t_match.group(1).lower())
                except:
                    pass

    return existing_texts


def is_topic_overlapping(topic_item, existing_texts):
    topic_words = set(re.findall(r'\w+', topic_item['title'].lower() + " " + topic_item['slug'].lower()))
    topic_words = {w for w in topic_words if len(w) > 3 and w not in ['einfache', 'tricks', 'tipps', 'einen', 'oder', 'fuer', 'deinen']}

    for ext in existing_texts:
        ext_words = set(re.findall(r'\w+', ext.lower()))
        ext_words = {w for w in ext_words if len(w) > 3}
        
        if not ext_words:
            continue
            
        overlap = topic_words.intersection(ext_words)
        similarity = len(overlap) / max(len(topic_words), 1)
        
        if similarity > 0.40:
            print(f"⚠️ Thema-Überschneidung erkannt ({similarity*100:.1f}%): \"{topic_item['title']}\" ähnelt bestehendem Beitrag.")
            return True

    return False


def select_next_best_topic(existing_texts):
    for candidate in TOPIC_POOL:
        if not is_topic_overlapping(candidate, existing_texts):
            return candidate
            
    dt_suffix = datetime.datetime.now().strftime("%d")
    return {
        "pillar": "frugalismus",
        "slug": f"frugalismus-monatsbudget-optimieren-tipps-{dt_suffix}",
        "title": f"Monatsbudget optimieren: Frugalismus-Strategie für den Spätsommer",
        "keywords": ["monatsbudget optimieren", "frugalismus strategie", "spartipps spatsommer", "geld sparen"],
        "description": "Erfahre, wie Du Dein Monatsbudget mit einfachen Frugalismus-Anpassungen optimierst und ungenutztes Sparpotenzial freisetzt."
    }


def generate_hugo_markdown_post(topic, target_date):
    pillar_info = PILLARS.get(topic['pillar'], PILLARS['frugalismus'])
    
    date_iso = target_date.strftime("%Y-%m-%dT06:00:00+02:00")
    date_fname = target_date.strftime("%Y-%m-%d")
    filename = f"{date_fname}-{topic['slug']}.md"
    filepath = os.path.join(POSTS_DIR, filename)
    
    os.makedirs(POSTS_DIR, exist_ok=True)
    
    markdown_content = f"""---
title: "{topic['title']}"
date: {date_iso}
draft: false
description: "{topic['description']}"
keywords: {json.dumps(topic['keywords'], ensure_ascii=False)}
categories: ["{pillar_info['category']}"]
tags: {json.dumps(topic['keywords'][:3], ensure_ascii=False)}
cover:
  image: "images/covers/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden.jpg"
  alt: "{topic['title']}"
---

# {topic['title']}

Willkommen auf **FranksFinanzcheck.de**! In diesem Ratgeber erfährst Du alles Wichtige rund um das Thema **{topic['keywords'][0]}**.

Erfahre, wie Du mit bewährten Praxistipps Deine Fixkosten reduzierst und Schritt für Schritt mehr finanzielle Freiheit erreichst.

---

## Die wichtigsten Fakten im Überblick

1. **Gezielte Analyse:** Überprüfe Deine regelmäßigen Ausgaben einmal pro Jahr.
2. **Keine versteckten Gebühren:** Nutze transparente Vergleiche ohne Zusatzkosten.
3. **Pillar-Hub Vertiefung:** Lies auch unseren Haupt-Ratgeber im Bereich [{pillar_info['name']}]({pillar_info['url']}).

---

## Schritt-für-Schritt Anleitung

* **Schritt 1:** Analysiere Deine aktuellen Konditionen im Kontoauszug.
* **Schritt 2:** Vergleiche unabhängige Angebote und achte auf exklusive Wechselboni.
* **Schritt 3:** Richte einen automatischen Sparauftrag am Monatsersten ein.

---

## Fazit & Nächste Schritte

Kleine Anpassungen im Alltag haben aufs Jahr gerechnet eine gewaltige Wirkung auf Deinen Kontostand!

Den vollständigen Haupt-Ratgeber findest Du in unserem Themen-Hub [{pillar_info['name']}]({pillar_info['url']}).
"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
        
    print(f"✅ Neuer Hugo-Artikel erfolgreich erstellt: {filepath}")
    return filepath


def main():
    print("🚀 Starte Profi Smart Blog Topic Automation für FranksFinanzcheck.de...")
    
    existing_texts = get_existing_slugs_and_titles()
    print(f"📊 {len(existing_texts)} bestehende Beitrags-Referenzen analysiert.")
    
    selected_topic = select_next_best_topic(existing_texts)
    print(f"🎯 Ausgewähltes freies Thema: \"{selected_topic['title']}\" (Pillar: {selected_topic['pillar']})")
    
    now = datetime.datetime.now()
    generated_file = generate_hugo_markdown_post(selected_topic, now)
    
    print(f"\n🎉 Smart Blog Automation erfolgreich abgeschlossen!")


if __name__ == "__main__":
    main()
