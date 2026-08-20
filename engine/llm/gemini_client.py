from __future__ import annotations

import json
from typing import Any


class LLMConfigurationError(RuntimeError):
    """Raised when the LLM provider is not configured."""


class LLMResponseError(RuntimeError):
    """Raised when a model response cannot be parsed/validated."""


class GeminiJsonClient:
    """Google Gemini API wrapper for JSON-schema constrained output.

    Uses the official ``google-genai`` SDK and the Gemini Developer API.
    The dependency is imported lazily so PDF parsing/tests still work even
    when the API package/key is not configured.
    """

    provider = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-3.7-flash") -> None:
        if not api_key or not api_key.strip():
            raise LLMConfigurationError("GEMINI_API_KEY가 설정되지 않았습니다.")
        self.api_key = api_key.strip()
        self.model = (model or "gemini-3.7-flash").strip()

    def _sdk(self):
        try:
            from google import genai
        except ImportError as exc:
            raise LLMConfigurationError(
                "google-genai 패키지가 설치되지 않았습니다. requirements.txt를 다시 설치해 주세요."
            ) from exc
        return genai

    def _client(self):
        genai = self._sdk()
        return genai.Client(api_key=self.api_key)

    def generate_json(
        self,
        *,
        instructions: str,
        input_text: str,
        schema_name: str,
        json_schema: dict[str, Any],
        model: str | None = None,
    ) -> dict[str, Any]:
        """Generate a JSON object that follows ``json_schema``.

        Gemini's ``response_json_schema`` accepts standard JSON Schema. We keep
        the schema name in the system instruction for traceability, while the
        schema itself is supplied only through the API config (not duplicated in
        the prompt), following Google Gen AI SDK guidance.
        """
        client = self._client()
        target_model = (model or self.model).strip()
        system_instruction = (
            instructions
            + f"\n\nInternal output contract name: {schema_name}. "
              "Return only data conforming to the configured JSON schema."
        )
        try:
            response = client.models.generate_content(
                model=target_model,
                contents=input_text,
                config={
                    "system_instruction": system_instruction,
                    "response_mime_type": "application/json",
                    "response_json_schema": json_schema,
                },
            )
        except Exception as exc:  # SDK/provider exceptions vary by version/status
            raise LLMResponseError(f"Gemini API 호출에 실패했습니다: {exc}") from exc

        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, dict):
            return parsed
        if parsed is not None:
            try:
                if hasattr(parsed, "model_dump"):
                    value = parsed.model_dump()
                    if isinstance(value, dict):
                        return value
                if isinstance(parsed, str):
                    return json.loads(parsed)
            except Exception:
                pass

        output_text = getattr(response, "text", None)
        if not output_text:
            raise LLMResponseError("Gemini 응답에 JSON text가 없습니다.")
        try:
            data = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise LLMResponseError("Gemini Structured Output을 JSON으로 해석하지 못했습니다.") from exc
        if not isinstance(data, dict):
            raise LLMResponseError("Gemini Structured Output의 최상위 값이 JSON object가 아닙니다.")
        return data
