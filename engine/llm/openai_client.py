from __future__ import annotations

import json
from typing import Any


class LLMConfigurationError(RuntimeError):
    """Raised when the LLM provider is not configured."""


class LLMResponseError(RuntimeError):
    """Raised when a model response cannot be parsed/validated."""


class OpenAIJsonClient:
    """Small Responses API wrapper with Structured Outputs.

    The OpenAI dependency is imported lazily so PDF parsing/tests still work
    without an API key and without constructing a client at import time.
    """

    def __init__(self, api_key: str, model: str = "gpt-5.6-luna") -> None:
        if not api_key or not api_key.strip():
            raise LLMConfigurationError("OPENAI_API_KEY가 설정되지 않았습니다.")
        self.api_key = api_key.strip()
        self.model = (model or "gpt-5.6-luna").strip()

    def _client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMConfigurationError(
                "openai 패키지가 설치되지 않았습니다. requirements.txt를 다시 설치해 주세요."
            ) from exc
        return OpenAI(api_key=self.api_key)

    def generate_json(
        self,
        *,
        instructions: str,
        input_text: str,
        schema_name: str,
        json_schema: dict[str, Any],
        model: str | None = None,
    ) -> dict[str, Any]:
        client = self._client()
        try:
            response = client.responses.create(
                model=model or self.model,
                instructions=instructions,
                input=input_text,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "strict": True,
                        "schema": json_schema,
                    }
                },
                store=False,
            )
        except Exception as exc:  # provider errors vary by SDK version/status
            raise LLMResponseError(f"OpenAI API 호출에 실패했습니다: {exc}") from exc

        output_text = getattr(response, "output_text", None)
        if not output_text:
            raise LLMResponseError("OpenAI 응답에 output_text가 없습니다.")
        try:
            return json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise LLMResponseError("Structured Output을 JSON으로 해석하지 못했습니다.") from exc
