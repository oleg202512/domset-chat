from __future__ import annotations

import re
import logging
from collections import defaultdict
from uuid import UUID

from fastapi import Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import APIConnectionError, APIError, AuthenticationError, RateLimitError
from pydantic import BaseModel, Field

from fastapi import FastAPI

from .config import KNOWLEDGE_BASE_PATH, STATIC_DIR
from .llm_service import create_client, generate_response
from .rag import KnowledgeBase


app = FastAPI(title="ДомСеть: Техподдержка")
logger = logging.getLogger("domset")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
knowledge_base = KnowledgeBase(KNOWLEDGE_BASE_PATH)
sessions: dict[str, list[dict[str, str]]] = defaultdict(list)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    chunks: list[dict[str, object]]


def get_api_key(authorization: str | None, x_api_key: str | None) -> str:
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    raise HTTPException(status_code=401, detail="Введите API-ключ в настройках приложения.")


def validate_session_id(session_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", session_id):
        raise HTTPException(status_code=400, detail="Некорректный идентификатор чата.")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> ChatResponse:
    validate_session_id(request.session_id)
    api_key = get_api_key(authorization, x_api_key)
    client = create_client(api_key)
    history = sessions[request.session_id]
    history.append({"role": "user", "content": request.message.strip()})

    try:
        chunks = await knowledge_base.search(client, request.message)
        answer = await generate_response(client, history, chunks)
    except AuthenticationError:
        history.pop()
        raise HTTPException(status_code=401, detail="API-ключ недействителен или отозван.")
    except RateLimitError:
        history.pop()
        raise HTTPException(status_code=429, detail="Лимит API исчерпан. Попробуйте позже.")
    except APIConnectionError:
        history.pop()
        raise HTTPException(status_code=502, detail="Не удалось подключиться к AI-сервису.")
    except APIError:
        history.pop()
        logger.exception("AI API returned an error")
        raise HTTPException(status_code=502, detail="AI-сервис временно недоступен.")
    except Exception:
        history.pop()
        logger.exception("Unexpected error while processing chat request")
        raise HTTPException(status_code=500, detail="Произошла внутренняя ошибка. Попробуйте ещё раз.")

    history.append({"role": "assistant", "content": answer})
    return ChatResponse(answer=answer, chunks=chunks)


@app.delete("/api/chat/{session_id}")
async def new_chat(session_id: str) -> dict[str, str]:
    validate_session_id(session_id)
    sessions.pop(session_id, None)
    return {"message": "История чата очищена."}
