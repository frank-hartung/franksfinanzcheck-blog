#!/usr/bin/env python3
"""Ergänzt affiliate_url (Deep-Links) in data/topics.yaml – pro Topic.
Damit bekommen künftige Bot-Artikel automatisch den passenden Deep-CTA-Link."""
import re
import sys

CHECK24 = "https://a.check24.net/misc/click.php?pid=80968&aid=18"
TARIFCHECK = "https://a.partner-versicherung.de/click.php?partner_id=47086&ad_id=15"


def deep_url(deep):
    return f"{CHECK24}&deep={deep}"


def tarif_url(deep=None):
    return f"{TARIFCHECK}&deep={deep}" if deep else TARIFCHECK


RULES = [
    (r"strom|photovoltaik|balkonkraftwerk|e-auto|waermepumpe|stromtarif|stromfresser",
     deep_url("stromanbieter-wechseln&cat=1")),
    (r"gas|heizoel|heizperiode|heizkosten", deep_url("gasanbieter-wechseln&cat=3")),
    (r"dsl|wlan|dns|kabel-internet|glasfaser|internet-flat|internet",
     deep_url("dsl-anbieterwechsel&cat=4")),
    (r"handy|mobilfunk", deep_url("handytarife")),
    (r"mietwagen", deep_url("mietwagen-preisvergleich&cat=10")),
    (r"flug", deep_url("flugvergleich")),
    (r"last-minute|urlaub|pauschal|camping", deep_url("pauschalreisen-vergleich&cat=9")),
    (r"girokonto", deep_url("c24bank&cat=14")),
    (r"kreditkarte", deep_url("kreditkarte")),
    (r"kredit|darlehen|hauskauf|baufinanzierung", deep_url("kreditvergleich")),
    (r"tagesgeld|festgeld", deep_url("tagesgeldvergleich")),
    (r"kfz|fahranfaenger|auto-versicherung", deep_url("kfz-versicherung")),
    (r"haftpflicht", tarif_url("haftpflichtversicherung")),
    (r"hausrat", tarif_url("hausratversicherung")),
    (r"reisekranken", tarif_url("reisekrankenversicherung")),
    (r"zahnzusatz|krankenzusatz", tarif_url("zahnzusatzversicherung")),
    (r"unfallversicherung", tarif_url("unfallversicherung")),
    (r"tier|hund|katze", tarif_url("hundeversicherung")),
    (r"umzug", tarif_url()),
]


def url_for(title):
    t = title.lower()
    for rx, url in RULES:
        if re.search(rx, t):
            return url
    return None  # generisch (CHECK24-Basis)


def main():
    path = "data/topics.yaml"
    lines = open(path, encoding="utf-8").read().split("\n")
    out = []
    current = None
    n_added = 0
    n_existing = 0
    for line in lines:
        m = re.match(r'^  - title: "(.*)"$', line)
        if m:
            current = m.group(1)
            out.append(line)
            continue
        if line.strip().startswith("affiliate_url:"):
            n_existing += 1
            out.append(line)
            current = None
            continue
        if current is not None and line.strip().startswith("keywords:"):
            url = url_for(current)
            if url:
                out.append(f'    affiliate_url: "{url}"')
                n_added += 1
            current = None
        out.append(line)

    open(path, "w", encoding="utf-8").write("\n".join(out))
    print(f"affiliate_url ergänzt: {n_added} Topics | bereits vorhanden: {n_existing}")

    # Verifikation
    sys.path.insert(0, "scripts")
    import generate_drafts as g
    topics = g.load_topics()
    ohne = [t["title"][:50] for t in topics if not t.get("affiliate_url")]
    print(f"Topics gesamt: {len(topics)} | ohne affiliate_url: {len(ohne)}")
    for t in ohne:
        print(f"  - {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
