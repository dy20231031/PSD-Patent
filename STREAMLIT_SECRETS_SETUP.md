# Streamlit Secrets Setup

The v0.2 Module 1 analysis requires an OpenAI API key.

1. Open the deployed Streamlit app workspace.
2. Open **App settings → Secrets**.
3. Paste:

```toml
OPENAI_API_KEY = "YOUR_API_KEY"
OPENAI_MODEL = "gpt-5.6-luna"
OPENAI_REPORT_MODEL = "gpt-5.6-luna"
```

4. Save. The app restarts automatically.

Do not create or commit `.streamlit/secrets.toml` with a real key. The repository `.gitignore` blocks that file.
