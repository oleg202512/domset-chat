from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_PATH = BASE_DIR / "База_знаний_ДомСеть.txt"
STATIC_DIR = BASE_DIR / "static"

AI_API_BASE_URL = "https://ai-api.neural-university.ru/v1"
CHAT_MODEL = "gpt-5.6-luna"
EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K = 5
MAX_HISTORY_MESSAGES = 16

SYSTEM_PROMPT = (
    'Ты — специалист технической поддержки интернет-провайдера "ДомСеть". '
    "Отвечай пользователю на русском языке. Помогай разбираться с настройкой "
    "Wi-Fi роутеров, подключением и типовыми проблемами. Отвечай понятно, "
    "вежливо и по существу. Используй найденные фрагменты базы знаний, но "
    "не выдумывай сведения, которых в них нет. Если информации недостаточно, "
    "честно скажи об этом и предложи обратиться к специалисту."
)
