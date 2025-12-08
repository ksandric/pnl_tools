import hashlib
import os
import pickle
import re
from datetime import datetime, timezone, timedelta
import httpx
import config


# Папка для кеша
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)


async def send_telegram_message(chat_id: int, chat: int, text: str):
    TOKEN = config.TELEGRAM_BOT_TOKEN 
    async with httpx.AsyncClient() as client:
        await client.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat, "text": text, "parse_mode": "HTML"})


def generate_cache_key(api_key: str, action: str, start_datetime: str = None, end_datetime: str = None) -> str:
    """Генерирует ключ кеша на основе параметров запроса"""
    # Хешируем API ключ для безопасности
    api_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
    
    if action == "get_pnl_today":
        # Кеш по текущей дате
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"{api_hash}_{action}_{today}"
        return sanitize_cache_key(key)
    
    elif action == "get_pnl_yesterday":
        # Кеш по вчерашней дате
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        key = f"{api_hash}_{action}_{yesterday}"
        return sanitize_cache_key(key)
    
    elif action == "get_pnl_current_month":
        # Кеш по текущему месяцу
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        key = f"{api_hash}_{action}_{current_month}"
        return sanitize_cache_key(key)
    
    elif action == "get_pnl_previous_month":
        # Кеш по предыдущему месяцу
        current = datetime.now(timezone.utc)
        if current.month == 1:
            prev_month = f"{current.year - 1}-12"
        else:
            prev_month = f"{current.year}-{current.month - 1:02d}"
        key = f"{api_hash}_{action}_{prev_month}"
        return sanitize_cache_key(key)
    
    elif action == "get_pnl_custom":
        # Кеш по диапазону дат
        if start_datetime and end_datetime:
            # Форматируем datetime строки в безопасный для имени файла формат
            # Возможный вход: '2025-01-01T00:00' или похожие. Заменим 'T' на '_' для читаемости
            def fmt(dt_str: str) -> str:
                try:
                    s = dt_str.replace('T', '_')
                except Exception:
                    s = dt_str
                return s

            s_start = fmt(start_datetime)
            s_end = fmt(end_datetime)
            key = f"{api_hash}_{action}_{s_start}_{s_end}"
            return sanitize_cache_key(key)
    
    return sanitize_cache_key(f"{api_hash}_{action}_unknown")


def sanitize_cache_key(key: str) -> str:
    """Sanitize a cache key so it becomes a valid filename on Windows and other OS.

    Replaces any character that is not alphanumeric, dot, underscore or hyphen with an underscore.
    Also collapses repeated underscores and trims leading/trailing separators.
    """
    # Replace any unsafe character with underscore
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", key)
    # Collapse multiple underscores to a single one
    safe = re.sub(r"_+", "_", safe)
    # Trim leading/trailing underscores or dots
    safe = safe.strip("_.")
    # Fallback to a short hash if result becomes empty
    if not safe:
        safe = hashlib.md5(key.encode()).hexdigest()[:12]
    return safe


def get_cache_file_path(cache_key: str) -> str:
    """Возвращает путь к файлу кеша"""
    return os.path.join(CACHE_DIR, f"{cache_key}.pkl")


def load_from_cache(cache_key: str):
    """Загружает данные из кеша"""
    cache_file = get_cache_file_path(cache_key)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Ошибка загрузки кеша: {e}")
            return None
    return None


def save_to_cache(cache_key: str, data):
    """Сохраняет данные в кеш"""
    cache_file = get_cache_file_path(cache_key)
    try:
        with open(cache_file, "wb") as f:
            pickle.dump(data, f)
        print(f"Данные сохранены в кеш: {cache_file}")
    except Exception as e:
        print(f"Ошибка сохранения в кеш: {e}")
