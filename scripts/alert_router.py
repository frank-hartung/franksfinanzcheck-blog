#!/usr/bin/env python3
"""
ALARM-ROUTER – Besitz, Kadenz und Schließpfad für jede Meldung (SSOT)
====================================================================

WARUM ES DIESE DATEI GIBT (Issue #272, 12.09.2026)
--------------------------------------------------
Der Bot-Watchdog kannte genau EINEN Meldeweg für ALLE Befunde:

    Befund → PROBLEMS != '' → Issue „⚠️ Bot-Watchdog: Probleme mit der
    Content-Automatisierung" → (nie wieder zu, solange irgendetwas offen ist)

Das hat drei teure Folgen, die im Agentur-Betrieb teurer sind als der
Ausfall selbst:

  1. **Falscher Alarm.** Ein Befund, den nur ein MENSCH heilen kann
     (totes Pinterest-Token → OAuth-Handschlag im Browser), stand als
     „Problem mit der Content-Automatisierung" im Briefkasten – obwohl
     Kadenz, Live-Site und Reserve kerngesund waren. Wer dreimal wegen
     nichts aufschreckt, überliest den vierten, echten Alarm
     (Alarm-Müdigkeit – genau der Schaden, den Governance-Vertrag C4
     eigentlich verhindern soll).

  2. **Sackgasse statt Schließpfad.** „Das Issue wird automatisch
     geschlossen, sobald der nächste Lauf alles grün meldet" – dieser
     Satz im alten Body war falsch: Grün kommt erst durch den Menschen,
     der Lauf darf aber nie grün melden, solange das menschliche Ticket
     in derselben Liste steht. Das Issue konnte NIE automatisch zugehen.
     Ergebnis: #251 → #272 → … täglich ein neues Gesicht, dieselbe
     Meldung. Ein Melder ohne Schließpfad ist ein Dauerläufer, kein
     Melder.

  3. **Doppelte Buchführung.** Für denselben Sachverhalt liefen zwei
     Tickets: das Fach-Ticket der Pinterest-Token-Wache (Label
     `pinterest-token`, mit Runbook) und der generische Watchdog-Alarm.
     Zwei Besitzer, zwei Wahrheiten, keine Ruhe.

WAS DER ROUTER ANDERS MACHT
---------------------------
  * **Besitz (owner):** `auto` = eine Maschine kann es heilen (Wache,
    Wiederholungslauf, Auto-Fix). `human` = nur ein Mensch mit Zugang
    kann es heilen (OAuth, Domain-Freigabe, API-Key).
  * **Zwei Kanäle, nie vermischt:** maschinelle Befunde steuern das
    generische Automations-Ticket (Label `bot-watchdog`) – und NUR sie.
    Menschliche Befunde steuern ihr Fach-Ticket (eigener Label-Kanal,
    ein Besitzer, ein Runbook).
  * **Kadenz statt Taktfeuer:** Ein offenes Fach-Ticket wird nicht
    täglich kommentiert. Die Eskalationsleiter (0/3/7/14 Tage) feuert
    genau einen Kommentar pro Stufe, frühestens alle 72 Stunden.
  * **Schließpfad ist Pflicht:** Ein Kanal ohne maschinell behebbaren
    Befund wird geschlossen – auch dann, wenn irgendwo ein menschliches
    Ticket offen ist. Die Sackgasse ist damit konstruktiv unmöglich.
  * **Ein Melder, der am Melden scheitert, ist der teuerste Fehler**
    (Lehre aus #209/#227): jede `gh`-Interaktion ist abgesichert, der
    Router wirft nie, er berichtet.

NUTZUNG
-------
    python3 scripts/alert_router.py --selftest     # Regeln prüfen (C6)
    python3 scripts/alert_router.py --plan FILE    # Plan aus Findings-JSON (kein Schreibzugriff)
    python3 scripts/alert_router.py --status       # offene Tickets + Eskalationsstufe

Die Findings kommen als JSON (eine Liste von Finding-Dicts) aus der
jeweiligen Wache – beim Bot-Watchdog: `scripts/bot_watchdog.py --route`.

Exit-Codes: 0 = ok · 1 = Routing teilweise fehlgeschlagen (Fehler im
Bericht, Lauf bleibt grün – der Melder darf nicht selbst zum Vorfall
werden) · 2 = Selbsttest defekt
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BLOG_DIR, "data", "alert_router_state.json")

SEVERITIES = ("P1", "P2", "P3")          # P1 = blockierend, P2 = beeinträchtigt, P3 = Hinweis/geparkt
OWNERS = ("auto", "human")               # auto = Maschine heilt, human = nur ein Mensch
GENERIC_CHANNEL = "bot-watchdog"         # Kanal der maschinell behebbaren Befunde

# Eskalationsleiter: (Schwelle in Tagen, Stufenname)
ESCALATION_LADDER: tuple[tuple[int, str], ...] = (
    (0, "Meldung"),
    (3, "Erinnerung"),
    (7, "Eskalation"),
    (14, "Kanal-Review"),
)

# Mindestabstand zwischen zwei Kommentaren im selben Kanal (Stunden).
# Cadence schlägt Taktfeuer: ein offenes Ticket ist KEIN täglicher Auftrag.
MIN_COMMENT_INTERVAL_HOURS = 72

# Findings jünger als dieses Alter gelten als frisch (Schutz gegen veraltete Lagebilder).
DEFAULT_MAX_STATE_AGE_HOURS = 48

MARKER = "<!-- alarm-router: {channel} -->"
TIER_MARKER = "<!-- alarm-router: {channel} stufe:{tier} -->"
SIG_MARKER = "<!-- alarm-router: {channel} sig:{sig} -->"


# --------------------------------------------------------------------------- #
#  Finding – der kleinste Baustein eines Alarms
# --------------------------------------------------------------------------- #
@dataclass
class Finding:
    """Ein Befund mit Besitzer, Schwere und Zielkanal.

    `owner="human"` ist die wichtigste Entscheidung im ganzen Router: sie
    entscheidet, ob ein Befund in den Automations-Alarm darf (darf er
    nicht) oder in sein Fach-Ticket (dorthin, mit Kadenz).
    """

    id: str                       # stabiler Schlüssel (z. B. "pinterest-token")
    title: str                    # kurze, menschenlesbare Überschrift
    detail: str = ""              # Befund mit Zahlen/Quellen
    severity: str = "P2"          # P1 | P2 | P3
    owner: str = "auto"           # auto | human
    channel: str = ""             # Label, das das Ticket BESITZT
    next_step: str = ""           # konkreter nächster Schritt (Runbook/Command)
    evidence: tuple[str, ...] = ()
    ladder: tuple[tuple[int, str], ...] = ESCALATION_LADDER
    once: bool = False            # Hinweis-Klasse: nur einmal melden (Zustand in data/alert_router_state.json)

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"severity muss {SEVERITIES} sein, nicht {self.severity!r}")
        if self.owner not in OWNERS:
            raise ValueError(f"owner muss {OWNERS} sein, nicht {self.owner!r}")
        if not self.channel:
            # Ohne Kanal gibt es keinen Besitzer – und ohne Besitzer keinen
            # Schließpfad. Lieber hart ablehnen als einen Waisen-Alarm bauen.
            self.channel = GENERIC_CHANNEL if self.owner == "auto" else "human-action"
        self.evidence = tuple(self.evidence)

    def as_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["evidence"] = list(self.evidence)
        d["ladder"] = [list(x) for x in self.ladder]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Finding":
        data = dict(d)
        data["evidence"] = tuple(data.get("evidence") or ())
        ladder = data.get("ladder") or ESCALATION_LADDER
        data["ladder"] = tuple((int(a), str(b)) for a, b in ladder)
        return cls(**data)

    def line(self) -> str:
        """Eine Zeile für Report/Issue-Body."""
        who = "Maschine" if self.owner == "auto" else "Mensch"
        step = f" → {self.next_step}" if self.next_step else ""
        return f"- **{self.severity} · {self.title}** ({who}) – {self.detail}{step}"


def machine_findings(findings: Iterable[Finding]) -> list[Finding]:
    return [f for f in findings if f.owner == "auto"]


def human_findings(findings: Iterable[Finding]) -> list[Finding]:
    return [f for f in findings if f.owner == "human"]


def blocking_findings(findings: Iterable[Finding]) -> list[Finding]:
    """Befunde, die den Betrieb wirklich stoppen (P1 + maschinell heilbar)."""
    return [f for f in findings if f.owner == "auto" and f.severity == "P1"]


def signature(findings: Sequence[Finding]) -> str:
    """Kurzer Fingerabdruck der Befundmenge (Änderung → Body-Update statt Kommentar)."""
    raw = "|".join(sorted(f"{f.id}:{f.severity}:{f.detail[:80]}" for f in findings))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]


# --------------------------------------------------------------------------- #
#  Tickets + Entscheidungen
# --------------------------------------------------------------------------- #
@dataclass
class IssueRef:
    number: int
    title: str = ""
    body: str = ""
    labels: tuple[str, ...] = ()
    created_at: datetime.datetime | None = None
    last_bot_comment_at: datetime.datetime | None = None
    last_tier: int = -1


@dataclass
class RouteDecision:
    action: str            # create | update | comment | close | none
    channel: str
    reason: str = ""
    issue: int | None = None
    title: str = ""
    body: str = ""
    tier: int = 0
    tier_label: str = ""
    severity: str = ""
    owner: str = ""


def tier_for_age(age_days: float, ladder: Sequence[tuple[int, str]] = ESCALATION_LADDER) -> int:
    """Eskalationsstufe aus dem Alter eines Tickets (0-basiert)."""
    tier = 0
    for i, (days, _label) in enumerate(ladder):
        if age_days >= days:
            tier = i
    return tier


def tier_label(tier: int, ladder: Sequence[tuple[int, str]] = ESCALATION_LADDER) -> str:
    return ladder[min(tier, len(ladder) - 1)][1]


def next_escalation_in_days(tier: int, ladder: Sequence[tuple[int, str]] = ESCALATION_LADDER) -> int | None:
    return ladder[tier + 1][0] if tier + 1 < len(ladder) else None


def _age_days(issue: IssueRef, now: datetime.datetime) -> float:
    if not issue.created_at:
        return 0.0
    return max(0.0, (now - issue.created_at).total_seconds() / 86400.0)


def _hours_since(ts: datetime.datetime | None, now: datetime.datetime) -> float:
    if not ts:
        return float("inf")
    return (now - ts).total_seconds() / 3600.0


# --------------------------------------------------------------------------- #
#  Planung (rein, ohne IO – deterministisch testbar)
# --------------------------------------------------------------------------- #
def plan_generic(findings: Sequence[Finding],
                 open_issue: IssueRef | None,
                 now: datetime.datetime) -> RouteDecision:
    """Der Automations-Kanal gehört AUSSCHLIESSLICH maschinell heilbaren Befunden.

    Genau hier liegt der Fix für #272: menschliche Befunde dürfen dieses
    Ticket weder öffnen noch offen halten – sonst gibt es keinen
    Schließpfad mehr (Sackgasse).
    """
    machine = machine_findings(findings)
    if machine:
        body = render_generic_body(machine, human_findings(findings), now)
        sig = signature(machine)
        if open_issue is None:
            return RouteDecision(
                action="create", channel=GENERIC_CHANNEL, title=(
                    "⚠️ Bot-Watchdog: Automatisierung braucht Eingriff"),
                body=body, severity=worst(machine).severity, owner="auto",
                reason=f"{len(machine)} maschinell behebbare Befunde – kein Ticket offen.")
        if sig not in (open_issue.body or ""):
            return RouteDecision(
                action="update", channel=GENERIC_CHANNEL, issue=open_issue.number,
                title=open_issue.title, body=body, severity=worst(machine).severity,
                owner="auto", reason="Befundmenge hat sich geändert – Ticket aktualisiert.")
        if _hours_since(open_issue.last_bot_comment_at, now) >= MIN_COMMENT_INTERVAL_HOURS:
            return RouteDecision(
                action="comment", channel=GENERIC_CHANNEL, issue=open_issue.number,
                body=render_status_comment(machine, now), severity=worst(machine).severity,
                owner="auto", reason=f"Befund unverändert, Kadenz {MIN_COMMENT_INTERVAL_HOURS} h erreicht.")
        return RouteDecision(
            action="none", channel=GENERIC_CHANNEL, issue=open_issue.number,
            severity=worst(machine).severity, owner="auto",
            reason=f"Befund unverändert, Ticket #{open_issue.number} offen "
                   f"(Kadenz {MIN_COMMENT_INTERVAL_HOURS} h noch nicht erreicht).")
    if open_issue is not None:
        return RouteDecision(
            action="close", channel=GENERIC_CHANNEL, issue=open_issue.number,
            reason="Keine maschinell behebbaren Befunde – Schließpfad greift "
                   "(menschliche Tickets bleiben in ihrem eigenen Kanal offen).")
    return RouteDecision(action="none", channel=GENERIC_CHANNEL,
                         reason="Keine Befunde – keine Meldung.")


def plan_channels(findings: Sequence[Finding],
                  open_by_channel: dict[str, IssueRef],
                  now: datetime.datetime,
                  state: dict[str, Any] | None = None) -> list[RouteDecision]:
    """Fach-Kanäle für menschliche Befunde: ein Besitzer, eine Kadenz.

    Der Router eröffnet ein Fach-Ticket nur, wenn der eigentliche Besitzer
    (der Fach-Workflow) keines offen hat – sonst bleibt er stumm und
    vermerkt die Abdeckung im Bericht. Kommentiert wird ausschließlich
    beim Überschreiten einer Eskalationsstufe (und frühestens alle 72 h).
    """
    state = state or {}
    out: list[RouteDecision] = []
    grouped: dict[str, list[Finding]] = {}
    for f in human_findings(findings):
        grouped.setdefault(f.channel, []).append(f)

    for channel, group in sorted(grouped.items()):
        worst_f = worst(group)
        issue = open_by_channel.get(channel)
        if issue is None:
            if worst_f.once and _channel_done(state, channel):
                out.append(RouteDecision(action="none", channel=channel, severity=worst_f.severity,
                                         owner="human",
                                         reason="Hinweis-Klasse: bereits gemeldet (Zustand)."))
                continue
            out.append(RouteDecision(
                action="create", channel=channel,
                title=render_channel_title(channel, group),
                body=render_channel_body(channel, group, now),
                severity=worst_f.severity, owner="human",
                reason="Kein Ticket im Fach-Kanal offen – Router übernimmt den Fallback-Besitz."))
            continue

        age = _age_days(issue, now)
        tier = tier_for_age(age, worst_f.ladder)
        label = tier_label(tier, worst_f.ladder)
        if tier > issue.last_tier and _hours_since(issue.last_bot_comment_at, now) >= MIN_COMMENT_INTERVAL_HOURS:
            out.append(RouteDecision(
                action="comment", channel=channel, issue=issue.number, tier=tier, tier_label=label,
                body=render_escalation_comment(channel, group, tier, age, now),
                severity=worst_f.severity, owner="human",
                reason=f"Stufe {tier} ({label}) erreicht, Ticket {age:.0f} Tage offen."))
            continue
        nxt = next_escalation_in_days(tier, worst_f.ladder)
        rest = f"nächste Stufe in {nxt} Tagen" if nxt is not None else "Endstufe erreicht"
        out.append(RouteDecision(
            action="none", channel=channel, issue=issue.number, tier=tier, tier_label=label,
            severity=worst_f.severity, owner="human",
            reason=f"Abgedeckt durch Ticket #{issue.number} (Stufe {tier} · {label}, {rest})."))
    return out


def worst(findings: Sequence[Finding]) -> Finding:
    """Schwerster Befund (P1 > P2 > P3), bei Gleichstand der erste."""
    order = {s: i for i, s in enumerate(SEVERITIES)}
    return sorted(findings, key=lambda f: order[f.severity])[0]


def _channel_done(state: dict[str, Any], channel: str) -> bool:
    return bool((state.get("channels") or {}).get(channel, {}).get("done"))


# --------------------------------------------------------------------------- #
#  Texte (Deutsch, Redaktionston – ein Ticket ist ein Arbeitsauftrag)
# --------------------------------------------------------------------------- #
def render_generic_body(machine: Sequence[Finding], human: Sequence[Finding],
                        now: datetime.datetime) -> str:
    lines = [
        "## 🤖 Bot-Watchdog: Automatisierung braucht Eingriff",
        "",
        f"**Stand:** {now:%Y-%m-%d %H:%M} UTC · **Besitzer:** Content-Automatisierung (Maschine)",
        "",
        "Diese Befunde kann eine Maschine heilen – sie blockieren den Betrieb,",
        "bis sie erledigt sind:",
        "",
    ]
    lines += [f.line() for f in machine]
    for f in machine:
        if f.evidence:
            lines += ["", f"**Nachweis `{f.id}`:**"] + [f"- {e}" for e in f.evidence]
    lines += ["", "### Nächste Schritte", ""]
    for i, f in enumerate(machine, 1):
        step = f.next_step or "siehe Befund"
        lines.append(f"{i}. **{f.title}** – {step}")
    if human:
        lines += ["", "### Was hier bewusst NICHT steht", "",
                  "Befunde, die nur ein Mensch heilen kann, haben einen eigenen Kanal",
                  "mit eigenem Besitzer und eigener Runbook-Seite – sie tauchen in diesem",
                  "Ticket nicht auf (Alarm-Routing, docs/ALARMROUTING-2026-09-12.md):", ""]
        lines += [f"- {f.title} → Ticket-Kanal `{f.channel}`" for f in human]
    lines += ["", "Das Ticket schließt sich von selbst, sobald kein maschinell behebbarer",
              "Befund mehr offen ist.", "",
              MARKER.format(channel=GENERIC_CHANNEL),
              SIG_MARKER.format(channel=GENERIC_CHANNEL, sig=signature(machine)), ""]
    return "\n".join(lines)


def render_status_comment(machine: Sequence[Finding], now: datetime.datetime) -> str:
    lines = [f"**Status {now:%Y-%m-%d %H:%M} UTC** – {len(machine)} Befunde weiter offen:", ""]
    lines += [f.line() for f in machine]
    lines += ["", f"_Kadenz: ein Kommentar alle {MIN_COMMENT_INTERVAL_HOURS} h – "
                  "ein offenes Ticket ist kein tägliches Rauschen._", "",
              MARKER.format(channel=GENERIC_CHANNEL)]
    return "\n".join(lines)


def render_channel_title(channel: str, group: Sequence[Finding]) -> str:
    icons = {"pinterest": "📌", "pinterest-token": "🔑", "human-action": "🙋"}
    icon = icons.get(channel, "🔔")
    return f"{icon} {worst(group).title}"


def render_channel_body(channel: str, group: Sequence[Finding], now: datetime.datetime) -> str:
    lines = [
        f"## {render_channel_title(channel, group)}",
        "",
        f"**Stand:** {now:%Y-%m-%d %H:%M} UTC · **Besitzer:** Mensch "
        f"(Kanal `{channel}`) · **Stufe:** 0 (Meldung)",
        "",
        "Diesen Befund kann keine Maschine heilen – er braucht einen Menschen mit",
        "Zugang. Genau deshalb steht er in einem eigenen Ticket: der Automations-",
        "Alarm bleibt sauber, und dieses Ticket hat sein eigenes Runbook.",
        "",
    ]
    lines += [f.line() for f in group]
    lines += ["", "### Nächster Schritt", ""]
    for f in group:
        lines.append(f"- **{f.title}** – {f.next_step or 'siehe Runbook'}")
    lines += ["", "### Kadenz", "",
              f"Erinnerung nach {ESCALATION_LADDER[1][0]} Tagen, Eskalation nach "
              f"{ESCALATION_LADDER[2][0]} Tagen, Kanal-Review nach {ESCALATION_LADDER[3][0]} Tagen.",
              "Ein Kommentar pro Stufe – kein tägliches Rauschen.", "",
              MARKER.format(channel=channel),
              SIG_MARKER.format(channel=channel, sig=signature(list(group))), ""]
    return "\n".join(lines)


def render_escalation_comment(channel: str, group: Sequence[Finding], tier: int,
                              age_days: float, now: datetime.datetime) -> str:
    label = tier_label(tier, group[0].ladder)
    lines = [
        f"### ⏫ Eskalation: {label} (Stufe {tier})",
        "",
        f"**Stand:** {now:%Y-%m-%d %H:%M} UTC · Ticket seit {age_days:.0f} Tagen offen.",
        "",
    ]
    lines += [f.line() for f in group]
    nxt = next_escalation_in_days(tier, group[0].ladder)
    if nxt is not None:
        lines += ["", f"_Nächste Stufe nach {nxt} Tagen, wenn sich der Befund nicht ändert._"]
    else:
        lines += ["", "_Endstufe erreicht: bitte entscheiden – heilen, parken oder Kanal "
                       "abschalten (stilllegen ist besser als ein Dauer-Alarm ohne Wirkung)._"]
    lines += ["", TIER_MARKER.format(channel=channel, tier=tier)]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
#  GitHub-Client (alle Aufrufe abgesichert – der Melder darf nie selbst
#  zum Vorfall werden, Lehre aus #209/#227)
# --------------------------------------------------------------------------- #
def _default_runner(args: Sequence[str], timeout: int = 60) -> tuple[int, str, str]:
    try:
        r = subprocess.run(list(args), cwd=BLOG_DIR, capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, (r.stdout or ""), (r.stderr or "")
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", f"{exc.__class__.__name__}: {exc}"


def _parse_ts(raw: str | None) -> datetime.datetime | None:
    if not raw:
        return None
    try:
        raw = raw.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


class GhClient:
    """Minimaler, abgesicherter GitHub-Client (nur Issues/Labels)."""

    def __init__(self, repo: str | None = None,
                 runner: Callable[..., tuple[int, str, str]] | None = None,
                 state_path: str = STATE_FILE):
        self.repo = repo or os.environ.get("GITHUB_REPOSITORY") or ""
        self._run = runner or _default_runner
        self.state_path = state_path
        self.errors: list[str] = []

    # -- Basis ------------------------------------------------------------ #
    def _gh(self, args: Sequence[str], timeout: int = 60) -> tuple[int, str, str]:
        args = list(args)
        # `gh api` kennt kein `--repo` – dort steckt das Repo im Pfad.
        if self.repo and "--repo" not in args and (not args or args[0] != "api"):
            args = ["--repo", self.repo, *args]
        return self._run(["gh", *args], timeout)

    def _api_lines(self, path: str, jq: str, timeout: int = 60) -> list[str]:
        """`gh api` zeilenweise (robust auch über mehrere Seiten hinweg)."""
        rc, out, err = self._gh(["api", path, "--paginate", "--jq", jq], timeout=timeout)
        if rc != 0:
            self.errors.append(f"api {path}: rc={rc} {err.strip()[:120]}")
            return []
        return (out or "").splitlines()

    # -- Lesen ------------------------------------------------------------ #
    def open_issues(self, label: str | None = None) -> list[IssueRef]:
        """Offene Tickets eines Kanals (leere Liste bei gh-Fehler – nie Exception)."""
        args = ["issue", "list", "--state", "open", "--limit", "100"]
        if label:
            args += ["--label", label]
        args += ["--json", "number,title,body,labels,createdAt,updatedAt"]
        rc, out, err = self._gh(args)
        if rc != 0:
            self.errors.append(f"issue list ({label or 'alle'}): rc={rc} {err.strip()[:160]}")
            return []
        try:
            data = json.loads(out or "[]")
        except json.JSONDecodeError as exc:
            self.errors.append(f"issue list ({label or 'alle'}): unparsbar ({exc})")
            return []
        return [self._issue_ref(item) for item in (data or [])]

    def _issue_ref(self, item: dict[str, Any]) -> IssueRef:
        labels = tuple((l.get("name") if isinstance(l, dict) else str(l))
                       for l in (item.get("labels") or []))
        return IssueRef(
            number=int(item.get("number")),
            title=item.get("title") or "",
            body=item.get("body") or "",
            labels=labels,
            created_at=_parse_ts(item.get("createdAt")),
        )

    def load_channel_comments(self, issue: IssueRef, channel: str) -> IssueRef:
        """Höchste bereits gemeldete Eskalationsstufe je Kanal (aus Kommentaren).

        Nur Kommentare mit Router-Marker zählen – fremde Kommentare (Mensch,
        andere Bots) verschieben die Leiter nicht.
        """
        bodies = self._api_lines(f"repos/{self.repo}/issues/{issue.number}/comments", ".[] | .body")
        for body in bodies:
            if MARKER.format(channel=channel) not in body:
                continue
            for t in range(len(ESCALATION_LADDER) - 1, -1, -1):
                if TIER_MARKER.format(channel=channel, tier=t) in body:
                    issue.last_tier = max(issue.last_tier, t)
                    break
        return issue

    def load_comments(self, number: int) -> list[dict[str, Any]]:
        stamps = self._api_lines(f"repos/{self.repo}/issues/{number}/comments", ".[] | .created_at")
        return [{"created_at": s.strip()} for s in stamps if s.strip()]

    def last_comment_at(self, number: int) -> datetime.datetime | None:
        stamps = [_parse_ts(c.get("created_at")) for c in self.load_comments(number)]
        stamps = [s for s in stamps if s]
        return max(stamps) if stamps else None

    # -- Schreiben --------------------------------------------------------- #
    def ensure_label(self, name: str, color: str = "0e8a16", description: str = "") -> bool:
        rc, _out, err = self._gh(["label", "create", name, "--color", color,
                                  "--description", description or f"Alarm-Kanal: {name}",
                                  "--force"], timeout=60)
        if rc != 0:
            self.errors.append(f"label create {name}: rc={rc} {err.strip()[:120]}")
            return False
        return True

    def create(self, title: str, body: str, labels: Sequence[str]) -> IssueRef | None:
        args = ["issue", "create", "--title", title, "--body", body]
        for label in labels:
            args += ["--label", label]
        rc, out, err = self._gh(args, timeout=90)
        if rc != 0:
            self.errors.append(f"issue create: rc={rc} {err.strip()[:160]}")
            return None
        m = re.search(r"/issues/(\d+)", out or "")
        number = int(m.group(1)) if m else 0
        if not number:
            self.errors.append(f"issue create: Nummer nicht erkannt ({out.strip()[:80]})")
            return None
        return IssueRef(number=number, title=title, body=body, labels=tuple(labels),
                        created_at=datetime.datetime.now(datetime.timezone.utc))

    def edit_body(self, number: int, body: str) -> bool:
        rc, _out, err = self._gh(["issue", "edit", str(number), "--body", body], timeout=60)
        if rc != 0:
            self.errors.append(f"issue edit #{number}: rc={rc} {err.strip()[:120]}")
            return False
        return True

    def comment(self, number: int, body: str) -> bool:
        rc, _out, err = self._gh(["issue", "comment", str(number), "--body", body], timeout=60)
        if rc != 0:
            self.errors.append(f"issue comment #{number}: rc={rc} {err.strip()[:120]}")
            return False
        return True

    def close(self, number: int, comment: str | None = None) -> bool:
        if comment:
            self.comment(number, comment)
        rc, _out, err = self._gh(["issue", "close", str(number)], timeout=60)
        if rc != 0:
            self.errors.append(f"issue close #{number}: rc={rc} {err.strip()[:120]}")
            return False
        return True

    # -- Zustand ----------------------------------------------------------- #
    def load_state(self) -> dict[str, Any]:
        try:
            with open(self.state_path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def save_state(self, state: dict[str, Any]) -> None:
        state["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
                f.write("\n")
        except OSError as exc:
            self.errors.append(f"Zustand nicht schreibbar: {exc}")


# --------------------------------------------------------------------------- #
#  Ausführung
# --------------------------------------------------------------------------- #
def route(findings: Sequence[Finding],
          client: GhClient,
          now: datetime.datetime | None = None,
          dry_run: bool = False,
          label_colors: dict[str, str] | None = None) -> dict[str, Any]:
    """Plant und führt das Routing aus. Wirft nie – sie berichtet."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    label_colors = label_colors or {"pinterest": "e60023", "pinterest-token": "d93f0b",
                                    "human-action": "fbca04", GENERIC_CHANNEL: "0e8a16"}
    report: dict[str, Any] = {"actions": [], "errors": [], "channels": {}}

    try:
        state = client.load_state()
        open_generic = None
        generic_issues = (client.open_issues(GENERIC_CHANNEL) or []) if not dry_run else []
        if generic_issues:
            open_generic = sorted(generic_issues, key=lambda i: i.number)[-1]
            open_generic.last_bot_comment_at = client.last_comment_at(open_generic.number)

        decisions = [plan_generic(findings, open_generic, now)]
        channels = {f.channel for f in human_findings(findings)}
        open_by_channel: dict[str, IssueRef] = {}
        for channel in sorted(channels):
            issues = (client.open_issues(channel) or []) if not dry_run else []
            if issues:
                issue = sorted(issues, key=lambda i: i.number)[-1]
                issue = client.load_channel_comments(issue, channel)
                issue.last_bot_comment_at = client.last_comment_at(issue.number)
                open_by_channel[channel] = issue
        decisions += plan_channels(findings, open_by_channel, now, state)

        for d in decisions:
            entry = {"channel": d.channel, "action": d.action, "reason": d.reason,
                     "issue": d.issue, "severity": d.severity, "owner": d.owner,
                     "tier": d.tier, "tier_label": d.tier_label}
            if dry_run or d.action == "none":
                report["actions"].append(entry)
                continue
            client.ensure_label(d.channel, label_colors.get(d.channel, "0e8a16"))
            if d.action == "create":
                created = client.create(d.title, d.body, [d.channel])
                entry["issue"] = created.number if created else None
                if created:
                    ch_state = (state.setdefault("channels", {}).setdefault(d.channel, {}))
                    ch_state.update({"first_seen": now.isoformat(), "ticket": created.number,
                                     "last_tier": d.tier, "open": True})
                    if d.owner == "human" and worst([f for f in findings
                                                     if f.channel == d.channel]).once:
                        ch_state["done"] = True
            elif d.action == "update" and d.issue:
                client.edit_body(d.issue, d.body)
                client.comment(d.issue, "🔄 Befundmenge aktualisiert – Stand siehe Ticket-Body.")
            elif d.action == "comment" and d.issue:
                client.comment(d.issue, d.body)
                ch_state = (state.setdefault("channels", {}).setdefault(d.channel, {}))
                ch_state.update({"last_tier": d.tier, "last_action": now.isoformat()})
            elif d.action == "close" and d.issue:
                client.close(d.issue, render_close_comment(findings, now))
                ch_state = (state.setdefault("channels", {}).setdefault(d.channel, {}))
                ch_state.update({"open": False, "closed_at": now.isoformat(),
                                 "last_tier": -1})
            report["actions"].append(entry)
            report["channels"][d.channel] = d.action

        client.save_state(state)
    except Exception as exc:  # Melder darf nie selbst zum Vorfall werden
        report["errors"].append(f"Routing abgebrochen: {exc.__class__.__name__}: {exc}")

    report["errors"] += client.errors
    report["ok"] = not report["errors"]
    return report


def render_close_comment(findings: Sequence[Finding], now: datetime.datetime) -> str:
    human = human_findings(findings)
    lines = [f"✅ **{now:%Y-%m-%d %H:%M} UTC** – kein maschinell behebbarer Befund mehr offen.",
             "Der Automations-Kanal ist damit wieder ruhig; der nächste Lauf prüft weiter.",
             ""]
    if human:
        lines += ["Was bleibt, ist bewusst in seinem eigenen Kanal (menschlicher Besitzer,",
                  "eigene Kadenz) – es hält dieses Ticket NICHT offen:", ""]
        lines += [f"- {f.title} → `{f.channel}`" for f in human]
    else:
        lines.append("Alle Wachen leben, Live-Site aktuell, alle Kanäle im grünen Bereich.")
    lines += ["", MARKER.format(channel=GENERIC_CHANNEL)]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
#  CLI + Selbsttest
# --------------------------------------------------------------------------- #
def _selftest() -> int:
    failures: list[str] = []
    now = datetime.datetime(2026, 9, 12, 12, 0, tzinfo=datetime.timezone.utc)
    born = now - datetime.timedelta(days=8)

    def check(name: str, cond: bool) -> None:
        if not cond:
            failures.append(name)

    # 1) Klassifikation: Mensch-Befund darf den Automations-Kanal nicht öffnen
    human = Finding(id="pinterest-token", title="Pinterest-Token tot", detail="HTTP 401",
                    severity="P2", owner="human", channel="pinterest-token",
                    next_step="Runbook")
    d = plan_generic([human], None, now)
    check("menschlicher Befund öffnet kein Automations-Ticket", d.action == "none")

    # 2) Schließpfad: Ticket offen, nur noch Mensch-Befunde → schließen
    issue = IssueRef(number=272, created_at=born, last_bot_comment_at=born)
    d = plan_generic([human], issue, now)
    check("Sackgasse geschlossen: Mensch-Befund allein hält Ticket nicht offen",
          d.action == "close" and d.issue == 272)

    # 3) Maschinen-Befund öffnet + aktualisiert
    machine = Finding(id="cadence", title="Kadenz nicht erfüllt", severity="P1",
                      owner="auto", channel=GENERIC_CHANNEL, next_step="Engine triggern")
    check("Maschinen-Befund öffnet Ticket", plan_generic([machine], None, now).action == "create")
    open_with_body = IssueRef(number=1, created_at=born,
                              body=render_generic_body([machine], [], now),
                              last_bot_comment_at=now - datetime.timedelta(hours=6))
    check("unveränderter Befund kommentiert nicht täglich",
          plan_generic([machine], open_with_body, now).action == "none")
    later = now + datetime.timedelta(hours=MIN_COMMENT_INTERVAL_HOURS + 1)
    check("Kadenz erreicht → Statuskommentar",
          plan_generic([machine], open_with_body, later).action == "comment")

    # 4) Fach-Kanal: kein Ticket → Fallback-Besitz; Ticket offen → Stille
    plans = plan_channels([human], {}, now, {})
    check("Fallback-Besitz bei fehlendem Fach-Ticket",
          plans and plans[0].action == "create" and plans[0].channel == "pinterest-token")
    covered = plan_channels([human], {"pinterest-token": IssueRef(
        number=246, created_at=born, last_tier=tier_for_age(_age_days(
            IssueRef(number=246, created_at=born), now)))}, now, {})
    check("abgedecktes Fach-Ticket bleibt still (Stufe schon eskaliert)",
          covered and covered[0].action == "none" and covered[0].issue == 246)
    fresh = IssueRef(number=246, created_at=now - datetime.timedelta(days=9),
                     last_tier=0, last_bot_comment_at=now - datetime.timedelta(days=9))
    esc = plan_channels([human], {"pinterest-token": fresh}, now, {})
    check("Eskalation feuert genau einmal pro Stufe",
          esc and esc[0].action == "comment" and esc[0].tier >= 2)
    check("Eskalation doppelt nicht (72 h)",
          plan_channels([human], {"pinterest-token": IssueRef(
              number=246, created_at=now - datetime.timedelta(days=9), last_tier=0,
              last_bot_comment_at=now - datetime.timedelta(hours=1))}, now, {})[0].action == "none")

    # 5) Leiter + Signaturen
    check("Leiter Tag 0", tier_for_age(0) == 0)
    check("Leiter Tag 7", tier_for_age(7) == 2)
    check("Signatur ändert sich mit Befund", signature([machine]) != signature([machine, human]))

    # 6) Finding-Validierung
    try:
        Finding(id="x", title="y", severity="P9")
        failures.append("ungültige Severity wird akzeptiert")
    except ValueError:
        pass
    check("Kanal-Default: Mensch → human-action",
          Finding(id="x", title="y", owner="human").channel == "human-action")

    # 7) Round-Trip JSON (Findings-Datei der Wachen)
    rt = Finding.from_dict(human.as_dict())
    check("JSON-Roundtrip", rt == human)

    if failures:
        print("🛑 ALARM-ROUTER SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print(f"  - {f}")
        return 2
    print("✅ ALARM-ROUTER SELFTEST bestanden "
          "(Klassifikation, Schließpfad, Kadenz, Eskalation, JSON).")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()

    if "--plan" in argv:
        path = argv[argv.index("--plan") + 1]
        try:
            with open(path, encoding="utf-8") as f:
                findings = [Finding.from_dict(d) for d in json.load(f)]
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            print(f"⚠️  Findings nicht lesbar: {exc}")
            return 1
        now = datetime.datetime.now(datetime.timezone.utc)
        plan = [plan_generic(findings, None, now).__dict__]
        plan += [d.__dict__ for d in plan_channels(findings, {}, now, {})]
        print(json.dumps(plan, ensure_ascii=False, indent=2, default=str))
        return 0

    if "--status" in argv:
        client = GhClient()
        if not client.repo:
            print("⚠️  GITHUB_REPOSITORY/GH_TOKEN fehlt – Status nicht abrufbar.")
            return 1
        issues = client.open_issues(GENERIC_CHANNEL) or []
        if not issues:
            print(f"Kein offenes Ticket im Kanal `{GENERIC_CHANNEL}`.")
        for issue in issues:
            age = _age_days(issue, datetime.datetime.now(datetime.timezone.utc))
            print(f"#{issue.number} · {issue.title} · {age:.0f} Tage offen · "
                  f"Stufe {tier_for_age(age)} ({tier_label(tier_for_age(age))})")
        return 0

    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
