-- KLICK-ZÄHLER – D1-Schema (nur aggregierte Tageszähler, keine Personenbezüge)
-- Anlegen: npx wrangler d1 execute ff-klicks --remote --file=schema.sql
CREATE TABLE IF NOT EXISTS klicks (
  tag      TEXT    NOT NULL,            -- YYYY-MM-DD, Europe/Berlin
  go_key   TEXT    NOT NULL,            -- /go/<key>/ (z. B. "strom")
  artikel  TEXT    NOT NULL,            -- Artikel-Slug aus ?subid= oder "unbekannt"
  anzahl   INTEGER NOT NULL DEFAULT 0,  -- Klicks an diesem Tag
  PRIMARY KEY (tag, go_key, artikel)
);
CREATE INDEX IF NOT EXISTS idx_klicks_tag ON klicks (tag);
