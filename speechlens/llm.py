from __future__ import annotations

import json
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from speechlens.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        key = api_key or settings.openai_api_key
        if not key:
            raise ValueError(
                "OPENAI_API_KEY is required. Set it in .env or pass api_key to SpeechAnnotator."
            )
        kwargs: dict[str, Any] = {"api_key": key}
        resolved_base = base_url if base_url is not None else settings.openai_base_url
        if resolved_base:
            kwargs["base_url"] = resolved_base
        self.client = OpenAI(**kwargs)
        self.model = model or settings.openai_model

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
