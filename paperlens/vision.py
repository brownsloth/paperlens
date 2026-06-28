from __future__ import annotations

import base64
from pathlib import Path

from openai import OpenAI

from speechlens.config import settings


class VisionClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or settings.openai_api_key
        if not key:
            raise ValueError("OPENAI_API_KEY required for figure/equation vision calls")
        kwargs: dict = {"api_key": key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        self.client = OpenAI(**kwargs)
        self.model = model or settings.openai_model

    def describe_crop(
        self,
        image_path: str,
        *,
        prompt: str,
        context: str = "",
    ) -> str:
        path = Path(image_path)
        if not path.exists():
            return ""
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        user_parts: list[dict] = [
            {"type": "text", "text": f"{prompt}\n\nSurrounding context:\n{context[:1200]}"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            },
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You explain figures and equations from research papers clearly and concisely. "
                        "Do not invent details not visible in the image."
                    ),
                },
                {"role": "user", "content": user_parts},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        return (response.choices[0].message.content or "").strip()
