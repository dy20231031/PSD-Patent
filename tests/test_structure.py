from pathlib import Path


def test_required_files_exist():
    root = Path(__file__).resolve().parents[1]
    required = [
        root / "streamlit_app.py",
        root / "requirements.txt",
        root / "knowledge" / "ontology_meta.json",
        root / "engine" / "schemas.py",
        root / "engine" / "analysis_models.py",
        root / "engine" / "llm" / "gemini_client.py",
        root / "engine" / "ontology" / "extractor.py",
        root / "engine" / "ontology" / "prompt_context.py",
        root / "engine" / "modules" / "module1.py",
        root / "engine" / "modules" / "module2.py",
        root / "engine" / "modules" / "module3.py",
    ]
    assert all(path.exists() for path in required)
