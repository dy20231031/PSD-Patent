from __future__ import annotations

import json
import random
import time
from typing import Any


class LLMConfigurationError(RuntimeError):
    """Raised when the LLM provider is not configured."""


class LLMResponseError(RuntimeError):
    """Raised when a model response cannot be parsed/validated."""


_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
_TRANSIENT_MARKERS = (
    "RESOURCE_EXHAUSTED",
    "UNAVAILABLE",
    "INTERNAL",
    "DEADLINE_EXCEEDED",
    "TOO MANY REQUESTS",
    "HIGH DEMAND",
)


def _status_code(exc: Exception) -> int | None:
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        try:
            if callable(value):
                value = value()
            if value is not None:
                code = int(value)
                if 100 <= code <= 599:
                    return code
        except Exception:
            pass
    text = str(exc).upper()
    for code in _TRANSIENT_STATUS_CODES:
        if str(code) in text:
            return code
    return None


def _is_transient(exc: Exception) -> bool:
    code = _status_code(exc)
    if code in _TRANSIENT_STATUS_CODES:
        return True
    upper = str(exc).upper()
    return any(marker in upper for marker in _TRANSIENT_MARKERS)


class GeminiJsonClient:
    """Google Gemini API wrapper with structured output, retry and fallback.

    Temporary provider errors (429/5xx/high demand) are retried with short
    exponential backoff. If the primary model remains unavailable, an optional
    fallback model is tried automatically. This prevents a single transient 503
    from collapsing the whole patent report.
    """

    provider = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.7-flash",
        *,
        fallback_model: str | None = None,
        max_retries: int = 2,
        base_delay: float = 1.25,
    ) -> None:
        if not api_key or not api_key.strip():
            raise LLMConfigurationError("GEMINI_API_KEY가 설정되지 않았습니다.")
        self.api_key = api_key.strip()
        self.model = (model or "gemini-3.7-flash").strip()
        fallback = (fallback_model or "").strip()
        self.fallback_model = fallback if fallback and fallback != self.model else None
        self.max_retries = max(0, min(int(max_retries), 4))
        self.base_delay = max(0.0, float(base_delay))
        self.last_model_used: str | None = None
        self.last_attempt_count: int = 0

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

    def _call(self, *, client, model: str, contents: str, config: dict[str, Any]):
        return client.models.generate_content(model=model, contents=contents, config=config)

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
        target_model = (model or self.model).strip()
        system_instruction = (
            instructions
            + f"\n\nInternal output contract name: {schema_name}. "
              "Return only data conforming to the configured JSON schema."
        )
        config = {
            "system_instruction": system_instruction,
            "response_mime_type": "application/json",
            "response_json_schema": json_schema,
        }

        models = [target_model]
        if self.fallback_model and self.fallback_model not in models:
            models.append(self.fallback_model)

        last_exc: Exception | None = None
        total_attempts = 0
        for model_name in models:
            for attempt in range(self.max_retries + 1):
                total_attempts += 1
                try:
                    response = self._call(
                        client=client,
                        model=model_name,
                        contents=input_text,
                        config=config,
                    )
                    self.last_model_used = model_name
                    self.last_attempt_count = total_attempts
                    return self._parse_response(response)
                except Exception as exc:  # provider exception types vary by SDK version
                    last_exc = exc
                    transient = _is_transient(exc)
                    if not transient:
                        self.last_attempt_count = total_attempts
                        raise LLMResponseError(f"Gemini API 호출에 실패했습니다: {exc}") from exc
                    if attempt < self.max_retries:
                        delay = self.base_delay * (2 ** attempt)
                        if delay > 0:
                            delay += random.uniform(0, min(0.35, delay * 0.1))
                            time.sleep(delay)
                        continue
                    break

        self.last_attempt_count = total_attempts
        fallback_note = f" / fallback={self.fallback_model}" if self.fallback_model else ""
        raise LLMResponseError(
            f"Gemini API 호출이 재시도 후에도 실패했습니다 (primary={target_model}{fallback_note}): {last_exc}"
        ) from last_exc

    @staticmethod
    def _parse_response(response) -> dict[str, Any]:
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
