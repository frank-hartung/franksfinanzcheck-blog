# 📌 PIN-STATUS (Pinterest-Automatisierung)

**Stand:** 2026-08-26 23:43 UTC

**Modus:** Queue (kein PINTEREST_ACCESS_TOKEN)

- 10 Pins vorbereitet in `data/pin_queue.yaml`
- 18 Artikel warten aufs Posting
- 0 Refresh-Kandidaten (älter als 60 Tage)

**So aktivierst du das Posting:** Pinterest Developer App → Token als Secret `PINTEREST_ACCESS_TOKEN` (Board-Routing läuft automatisch, siehe `data/pinterest_boards.yaml`; Fallback-Board optional: `PINTEREST_BOARD_ID`).