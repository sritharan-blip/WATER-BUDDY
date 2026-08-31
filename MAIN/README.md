# Water Buddy

A Streamlit hydration tracking app.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run waterbuddy.py
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run waterbuddy.py
```

The app stores personal hydration data locally in `~/.water_buddy`.
