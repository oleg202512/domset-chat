from __future__ import annotations

from openai import AsyncOpenAI

from .config import AI_API_BASE_URL, CHAT_MODEL, MAX_HISTORY_MESSAGES, SYSTEM_PROMPT


def create_client(api_key: str) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=api_key, base_url=AI_API_BASE_URL)


async def generate_response(
    client: AsyncOpenAI,
    messages: list[dict[str, str]],
    chunks: list[dict[str, object]],
) -> str:
    # Платформа ограничивает размер тела запроса. В интерфейсе показываются
    # полные чанки, а в prompt отправляется компактная выдержка из каждого.
    context = "\n\n".join(
        f"Фрагмент {item['number']}:\n{str(item['text'])[:650]}" for item in chunks
    )
    prompt_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                "Контекст базы знаний для текущего вопроса:\n"
                f"{context}\n\n"
                "Сформулируй самостоятельный полезный ответ. Не упоминай внутренние "
                "чанки, embeddings или техническую архитектуру приложения."
            ),
        },
        *messages[-MAX_HISTORY_MESSAGES:],
    ]
    response = await client.chat.completions.create(
        model=CHAT_MODEL,
        messages=prompt_messages,
        max_completion_tokens=500,
        stream=False,
    )
    content = response.choices[0].message.content
    return content.strip() if content else "Не удалось получить содержательный ответ."
