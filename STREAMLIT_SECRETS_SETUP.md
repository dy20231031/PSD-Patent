# Streamlit Secrets Setup — Gemini API

The v0.3 Module 1 analysis uses the Google Gemini API through the official `google-genai` Python SDK.

1. Open the deployed Streamlit app workspace.
2. Open **App settings → Secrets**.
3. Paste:

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_MODEL = "gemini-3.7-flash"
GEMINI_REPORT_MODEL = "gemini-3.7-flash"
```

4. Save. The app restarts automatically.

Do not create or commit `.streamlit/secrets.toml` with a real key. The repository `.gitignore` blocks that file.
