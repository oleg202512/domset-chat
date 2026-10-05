from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI

from .config import EMBEDDING_MODEL, TOP_K


@dataclass
class Chunk:
    number: int
    text: str
    embedding: list[float] | None = None


class KnowledgeBase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.chunks = self._load_chunks()
        self._embedding_cache: dict[str, list[float]] = {}

    def _load_chunks(self) -> list[Chunk]:
        text = self.path.read_text(encoding="utf-8")
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: list[Chunk] = []
        buffer: list[str] = []
        size = 0

        for paragraph in paragraphs:
            if buffer and size + len(paragraph) > 1400:
                chunks.append(Chunk(len(chunks) + 1, "\n\n".join(buffer)))
                buffer = []
                size = 0
            buffer.append(paragraph)
            size += len(paragraph)

        if buffer:
            chunks.append(Chunk(len(chunks) + 1, "\n\n".join(buffer)))
        return chunks

    async def _embed(self, client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
        missing = [text for text in texts if text not in self._embedding_cache]
        # Платформа разрешает до 8 строк, но также ограничивает общий размер
        # тела запроса. Четыре чанка оставляют запас для русского текста.
        for start in range(0, len(missing), 4):
            batch = missing[start : start + 4]
            result = await client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
                dimensions=256,
                encoding_format="float",
            )
            for text, item in zip(batch, result.data):
                self._embedding_cache[text] = item.embedding
        return [self._embedding_cache[text] for text in texts]

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if not left_norm or not right_norm:
            return 0.0
        return dot / (left_norm * right_norm)

    async def search(self, client: AsyncOpenAI, query: str) -> list[dict[str, object]]:
        query_embedding = (await self._embed(client, [query]))[0]
        chunk_embeddings = await self._embed(client, [chunk.text for chunk in self.chunks])
        scored = [
            (self._cosine(query_embedding, embedding), chunk)
            for chunk, embedding in zip(self.chunks, chunk_embeddings)
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {"number": chunk.number, "text": chunk.text, "score": round(score, 4)}
            for score, chunk in scored[:TOP_K]
        ]
