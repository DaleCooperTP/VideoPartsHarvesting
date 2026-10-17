from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import streamlit as st


APP_TITLE = "Referee Link Harvester"
DATA_DIR = Path("data")
SAVED_LINKS_PATH = DATA_DIR / "saved_links.json"
REJECTED_NOTES_PATH = DATA_DIR / "rejected_notes.json"


TEAM_ALIASES = {
    "paok": "PAOK",
    "παοκ": "PAOK",
    "π.α.ο.κ": "PAOK",
    "aek": "AEK",
    "αεκ": "AEK",
    "α.ε.κ": "AEK",
    "olympiacos": "Olympiacos",
    "ολυμπιακος": "Olympiacos",
    "ολυμπιακός": "Olympiacos",
    "osfp": "Olympiacos",
    "οσφπ": "Olympiacos",
    "panathinaikos": "Panathinaikos",
    "παναθηναικος": "Panathinaikos",
    "παναθηναϊκος": "Panathinaikos",
    "παναθηναϊκός": "Panathinaikos",
    "pao": "Panathinaikos",
    "aris": "Aris",
    "αρης": "Aris",
    "άρης": "Aris",
    "ofh": "OFI",
    "ofi": "OFI",
    "οφη": "OFI",
    "asteras": "Asteras Tripolis",
    "αστερας": "Asteras Tripolis",
    "αστέρας": "Asteras Tripolis",
}


GREEK_NAMES = {
    "PAOK": "ΠΑΟΚ",
    "AEK": "ΑΕΚ",
    "Olympiacos": "Ολυμπιακός",
    "Panathinaikos": "Παναθηναϊκός",
    "Aris": "Άρης",
    "OFI": "ΟΦΗ",
    "Asteras Tripolis": "Αστέρας Τρίπολης",
}


@dataclass
class ParsedQuery:
    raw: str
    teams: list[str]
    date_hint: str | None


@dataclass
class SavedLink:
    id: str
    created_at: str
    query: str
    match_label: str
    title: str
    url: str
    source: str
    notes: str
    status: str


def normalize_text(value: str) -> str:
    return value.casefold().replace("ς", "σ")


def load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_json(path: Path, rows: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_query(raw_query: str) -> ParsedQuery:
    normalized = normalize_text(raw_query)
    found_teams: list[str] = []

    for alias, team in TEAM_ALIASES.items():
        alias_pattern = re.escape(normalize_text(alias))
        if re.search(rf"(?<!\w){alias_pattern}(?!\w)", normalized) and team not in found_teams:
            found_teams.append(team)

    date_match = re.search(
        r"(?P<day>\d{1,2})[/-](?P<month>\d{1,2})(?:[/-](?P<year>\d{2,4}))?",
        raw_query,
    )
    date_hint = None
    if date_match:
        day = int(date_match.group("day"))
        month = int(date_match.group("month"))
        year = date_match.group("year")
        date_hint = f"{day:02d}/{month:02d}" + (f"/{year}" if year else "")

    return ParsedQuery(raw=raw_query, teams=found_teams[:2], date_hint=date_hint)


def team_terms(team: str) -> list[str]:
    terms = [team]
    greek = GREEK_NAMES.get(team)
    if greek:
        terms.append(greek)
    return terms


def match_label(parsed: ParsedQuery) -> str:
    if len(parsed.teams) >= 2:
        return f"{parsed.teams[0]} - {parsed.teams[1]}"
    if parsed.teams:
        return parsed.teams[0]
    return parsed.raw.strip()


def build_query_variants(parsed: ParsedQuery) -> list[tuple[str, str, str]]:
    if len(parsed.teams) >= 2:
        left_terms = team_terms(parsed.teams[0])
        right_terms = team_terms(parsed.teams[1])
        base_el = f"{left_terms[-1]} {right_terms[-1]}"
        base_en = f"{left_terms[0]} {right_terms[0]}"
    else:
        base_el = parsed.raw.strip()
        base_en = parsed.raw.strip()

    date = f" {parsed.date_hint}" if parsed.date_hint else ""

    variants = [
        ("Referee decisions", f"{base_el}{date} διαιτησία επίμαχες φάσεις", "google"),
        ("VAR / penalties / cards", f"{base_el}{date} πέναλτι κόκκινη κάρτα VAR διαιτητής", "google"),
        ("Athlitiki Kyriaki / Varouchas", f"{base_el}{date} Βαρούχας Αθλητική Κυριακή διαιτησία", "google"),
        ("KED / Lannoy analysis", f"{base_el}{date} Λανουά ΚΕΔ ανάλυση φάσεων", "google"),
        ("News articles", f"{base_el}{date} διαιτησία site:sport24.gr OR site:sdna.gr OR site:gazzetta.gr", "google"),
        ("YouTube referee clips", f"{base_el}{date} διαιτησία επίμαχες φάσεις", "youtube"),
        ("YouTube Varouchas", f"{base_el}{date} Βαρούχας διαιτησία", "youtube"),
        ("English fallback", f"{base_en}{date} referee decisions penalty red card VAR", "google"),
    ]

    return variants


def search_url(query: str, provider: str) -> str:
    encoded = quote_plus(query)
    if provider == "youtube":
        return f"https://www.youtube.com/results?search_query={encoded}"
    return f"https://www.google.com/search?q={encoded}"


def render_search_variants(parsed: ParsedQuery) -> None:
    st.subheader("Search paths")
    st.caption("Open a search, inspect results, then paste useful links into the review queue below.")

    for label, query, provider in build_query_variants(parsed):
        url = search_url(query, provider)
        provider_label = "YouTube" if provider == "youtube" else "Google"
        with st.container(border=True):
            st.markdown(f"**{label}** · {provider_label}")
            st.code(query, language=None)
            st.link_button("Open search", url, use_container_width=True)


def render_save_form(parsed: ParsedQuery) -> None:
    st.subheader("Save a useful link")
    with st.form("save_link", clear_on_submit=True):
        title = st.text_input("Title")
        url = st.text_input("URL")
        source = st.text_input("Source", placeholder="YouTube, Sport24, SDNA, ERT...")
        notes = st.text_area("Notes", placeholder="Penalty appeal at 72', useful Varouchas discussion...")
        submitted = st.form_submit_button("Save link")

    if submitted:
        if not url.strip():
            st.error("Paste a URL before saving.")
            return

        rows = load_json(SAVED_LINKS_PATH)
        rows.append(
            asdict(
                SavedLink(
                    id=str(uuid.uuid4()),
                    created_at=datetime.now(timezone.utc).isoformat(),
                    query=parsed.raw,
                    match_label=match_label(parsed),
                    title=title.strip() or url.strip(),
                    url=url.strip(),
                    source=source.strip(),
                    notes=notes.strip(),
                    status="useful",
                )
            )
        )
        save_json(SAVED_LINKS_PATH, rows)
        st.success("Saved.")


def render_reject_note(parsed: ParsedQuery) -> None:
    with st.expander("Record a bad/noisy result"):
        with st.form("reject_note", clear_on_submit=True):
            url = st.text_input("Bad URL or search result")
            reason = st.text_input("Reason", placeholder="Wrong match, fan rant, unrelated, duplicate...")
            submitted = st.form_submit_button("Save rejected note")

        if submitted:
            rows = load_json(REJECTED_NOTES_PATH)
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "query": parsed.raw,
                    "match_label": match_label(parsed),
                    "url": url.strip(),
                    "reason": reason.strip(),
                }
            )
            save_json(REJECTED_NOTES_PATH, rows)
            st.success("Rejected note saved.")


def render_saved_links() -> None:
    rows = load_json(SAVED_LINKS_PATH)
    st.subheader(f"Saved links ({len(rows)})")
    if not rows:
        st.caption("No saved links yet.")
        return

    for row in reversed(rows[-25:]):
        with st.container(border=True):
            st.markdown(f"**{row.get('title', 'Untitled')}**")
            st.caption(f"{row.get('match_label', '')} · {row.get('source', 'Unknown source')}")
            st.write(row.get("notes", ""))
            st.link_button("Open", row.get("url", "#"))

            x_draft = (
                f"{row.get('match_label', 'Match')}: γνώμη για τη φάση;\n\n"
                f"{row.get('title', '')}\n"
                f"{row.get('url', '')}\n\n"
                "#SuperLeagueGR"
            )
            st.text_area("X draft", value=x_draft, height=120, key=f"x_{row['id']}")


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="⚽", layout="wide")

    st.title(APP_TITLE)
    st.caption("Private prototype for finding referee-decision discussion links.")

    with st.sidebar:
        st.header("How to use")
        st.markdown(
            """
1. Type a match query.
2. Open the generated searches.
3. Paste useful links back into the app.
4. Use the saved queue to draft X posts.
            """.strip()
        )
        st.divider()
        st.caption("Examples")
        st.code("PAOK-AEK 21/5\nΠΑΟΚ ΑΕΚ 21/05\nOlympiacos Panathinaikos penalty", language=None)

    query = st.text_input(
        "Match or topic",
        value="PAOK-AEK 21/5",
        placeholder="PAOK-AEK 21/5",
    )

    parsed = parse_query(query)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Detected teams", ", ".join(parsed.teams) if parsed.teams else "Unknown")
    col_b.metric("Date hint", parsed.date_hint or "Unknown")
    col_c.metric("Match label", match_label(parsed))

    if len(parsed.teams) < 2:
        st.warning("I could not confidently detect two teams. The searches still work, but add team aliases over time.")

    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        render_search_variants(parsed)
    with right:
        render_save_form(parsed)
        render_reject_note(parsed)
        render_saved_links()


if __name__ == "__main__":
    main()
