# Referee Link Harvester Prototype

Tiny Streamlit prototype for researching referee-decision links for a specific match.

## Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Deploy On Streamlit Community Cloud

1. Put these files in a GitHub repository.
2. Create a new app on Streamlit Community Cloud.
3. Select `app.py` as the entry point.
4. Make the app private and invite the admin viewer.

## What v0 Does

- Parses rough match text such as `PAOK-AEK 21/5`.
- Recognizes common Greek club aliases.
- Generates targeted Google and YouTube searches.
- Lets the admin paste useful links.
- Saves useful links and rejected notes to local JSON files.

This version deliberately does not scrape Google/YouTube results. It is a proof-of-concept research console.
