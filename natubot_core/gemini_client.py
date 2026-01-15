from __future__ import annotations

from typing import List
from google import genai
from google.genai import types

class GeminiClient:
    def __init__(self, api_key: str, chat_model: str, embed_model: str, embed_dim: int):
        self.client = genai.Client(api_key=api_key)
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.embed_dim = embed_dim

    def embed_query(self, text: str) -> List[float]:
        res = self.client.models.embed_content(
            model=self.embed_model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=self.embed_dim,
            ),
        )
        return res.embeddings[0].values

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        res = self.client.models.embed_content(
            model=self.embed_model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=self.embed_dim,
            ),
        )
        return [e.values for e in res.embeddings]

    def generate(self, prompt: str, temperature: float = 0.2, max_output_tokens: int = 800) -> str:
        resp = self.client.models.generate_content(
            model=self.chat_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        return (resp.text or "").strip()
