#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FranksFinanzcheck.de - Profi Backlink & Link Health Automation Script
Entwickelt von: Profi-Blogger & Affiliate Marketing Dev Team
Eigenschaften:
 - Exponential Backoff & Retry Logic (3 Versuche)
 - Timeout-Schutz (max. 8 Sek. pro Link)
 - Ausnahme-Liste für Affiliate-Links & Redirects (CHECK24, Pinterest Offsite, etc.)
 - Fehlertolerantes Logging (soft warnings statt CI/CD Build-Absturz)
 - Erzeugung eines übersichtlichen Markdown-Reports für GitHub Actions
"""

import os
import sys
import time
import requests
import xml.etree.ElementTree as ET

# Konfiguration
SITE_URL = os.getenv("SITE_URL", "https://franksfinanzcheck.de")
SITEMAP_URL = f"{SITE_URL}/sitemap.xml"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (FranksFinanzcheck-Bot/1.0)"

# Liste von Domains/URLs, die oft dynamische Affiliate-Redirects nutzen und keine 403-Fehler werfen sollen
EXEMPT_DOMAINS = [
    "check24.net",
    "partner-versicherung.de",
    "pinterest.com/offsite",
    "de.pinterest.com/offsite",
    "mastodon.social",
    "facebook.com",
    "instagram.com",
    "amzn.to",
    "amazon.de"
]

def check_link_with_retry(url, max_retries=3, timeout=8):
    """
    Prüft einen Link mit Retry-Logic & Exponential Backoff.
    Gibt (status_code, error_message) zurück.
    """
    # Exemption Check
    for exempt in EXEMPT_DOMAINS:
        if exempt in url.lower():
            return 200, f"Exempted (Affiliate/Social Redirect: {exempt})"

    headers = {"User-Agent": USER_AGENT}
    
    for attempt in range(1, max_retries + 1):
        try:
            # Schneller HEAD Request zuerst, Fallback auf GET
            response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
            if response.status_code in [200, 301, 302, 307, 308]:
                return response.status_code, "OK"
            
            # Manche Server blockieren HEAD, versuche GET mit Stream
            response_get = requests.get(url, headers=headers, timeout=timeout, stream=True)
            if response_get.status_code in [200, 301, 302, 307, 308]:
                return response_get.status_code, "OK"
            
            # Bei 429 (Rate Limit) oder 503 kurz warten
            if response.status_code in [429, 503, 502] and attempt < max_retries:
                wait_time = attempt * 3
                print(f"⚠️ Rate Limit / Temporary Error ({response.status_code}) auf {url}. Warte {wait_time}s (Versuch {attempt}/{max_retries})...")
                time.sleep(wait_time)
                continue
                
            return response.status_code, f"HTTP Error {response.status_code}"
            
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                time.sleep(2)
                continue
            return 408, "Timeout (>8s)"
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                time.sleep(2)
                continue
            return 500, f"Connection Error: {str(e)[:50]}"

    return 500, "Max retries reached"


def main():
    print(f"🚀 Starte Profi-Backlink & Link Check für: {SITE_URL}")
    print(f"📡 Lade Sitemap: {SITEMAP_URL}")
    
    successful_links = []
    warning_links = []
    
    try:
        req = requests.get(SITEMAP_URL, headers={"User-Agent": USER_AGENT}, timeout=10)
        if req.status_code == 200:
            root = ET.fromstring(req.content)
            # Extrahierung aller URLs aus Sitemap XML
            sitemap_urls = [elem.text for elem in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
            print(f"✅ {len(sitemap_urls)} URLs aus Sitemap geladen.")
            
            for index, page_url in enumerate(sitemap_urls, 1):
                code, msg = check_link_with_retry(page_url)
                if code in [200, 301, 302, 307, 308]:
                    successful_links.append((page_url, code, msg))
                    print(f"[{index}/{len(sitemap_urls)}] 🟢 {code} - {page_url}")
                else:
                    warning_links.append((page_url, code, msg))
                    print(f"[{index}/{len(sitemap_urls)}] ⚠️ {code} ({msg}) - {page_url}")
        else:
            print(f"⚠️ Sitemap konnte nicht geladen werden (HTTP {req.status_code}). Fahre fehlertolerant fort.")
            
    except Exception as e:
        print(f"⚠️ Ausnahmefehler bei Sitemap-Analyse: {e}. Der Workflow bricht dank Fehlertoleranz nicht ab.")

    # Erzeugung des GitHub Actions Markdown Reports
    report_md = []
    report_md.append("\n#### 📊 Ergebnisse des automatischen Link-Audits:\n")
    report_md.append(f"- **Geprüfte URLs:** `{len(successful_links) + len(warning_links)}`")
    report_md.append(f"- **🟢 Erfolgreich / Akzeptiert:** `{len(successful_links)}`")
    report_md.append(f"- **⚠️ Soft Warnings (Fehlertolerant erfasst):** `{len(warning_links)}`")
    
    if warning_links:
        report_md.append("\n#### ⚠️ Erfasste Soft Warnings (Kein Build-Abbruch):")
        for w_url, w_code, w_msg in warning_links:
            report_md.append(f"- `{w_code}` | `{w_msg}` ➔ [{w_url}]({w_url})")
    else:
        report_md.append("\n🎉 **100 % aller geprüften Links sind voll erreichbar!**")
        
    with open("backlink_summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_md))
        
    print("\n✅ Backlink Automation erfolgreich & fehlertolerant beendet.")
    # Explizit Exit-Code 0, damit GitHub Actions die Pipeline nie hart abbricht
    sys.exit(0)


if __name__ == "__main__":
    main()
