import json
import sys
import types

import pytest

from engine.llm.gemini_client import GeminiJsonClient, LLMConfigurationError, LLMResponseError


def test_gemini_client_rejects_empty_key():
    with pytest.raises(LLMConfigurationError):
        GeminiJsonClient("")


def test_gemini_generate_json_uses_schema(monkeypatch):
    captured = {}

    class FakeResponse:
        parsed = {"ok": True}
        text = '{"ok": true}'

    class FakeModels:
        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    class FakeClient:
        def __init__(self, api_key=None):
            captured["api_key"] = api_key
            self.models = FakeModels()

    fake_genai = types.ModuleType("genai")
    fake_genai.Client = FakeClient
    fake_google = types.ModuleType("google")
    fake_google.genai = fake_genai
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)

    client = GeminiJsonClient("secret", model="gemini-3.7-flash")
    out = client.generate_json(
        instructions="Follow facts only.",
        input_text="hello",
        schema_name="test_contract",
        json_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
    )
    assert out == {"ok": True}
    assert captured["model"] == "gemini-3.7-flash"
    assert captured["config"]["response_mime_type"] == "application/json"
    assert captured["config"]["response_json_schema"]["type"] == "object"
    assert "test_contract" in captured["config"]["system_instruction"]
    assert captured["api_key"] == "secret"


def test_gemini_generate_json_wraps_provider_error(monkeypatch):
    class FakeModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("boom")

    class FakeClient:
        def __init__(self, api_key=None):
            self.models = FakeModels()

    fake_genai = types.ModuleType("genai")
    fake_genai.Client = FakeClient
    fake_google = types.ModuleType("google")
    fake_google.genai = fake_genai
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)

    client = GeminiJsonClient("secret")
    with pytest.raises(LLMResponseError, match="Gemini API"):
        client.generate_json(
            instructions="x",
            input_text="y",
            schema_name="z",
            json_schema={"type": "object"},
        )
