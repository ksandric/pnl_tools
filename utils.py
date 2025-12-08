import hashlib
import os
import pickle
from datetime import datetime, timezone, timedelta


# Папка для кеша
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)


async def send_telegram_message(chat_id: int, chat: int, text: str):
    TOKEN = '' 
    async with httpx.AsyncClient() as client:
        await client.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": chat, "text": text, "parse_mode": "HTML"})


def generate_cache_key(api_key: str, action: str, start_datetime: str = None, end_datetime: str = None) -> str:
    """Генерирует ключ кеша на основе параметров запроса"""
    # Хешируем API ключ для безопасности
    api_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
    
    if action == "get_pnl_today":
        # Кеш по текущей дате
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"{api_hash}_{action}_{today}"
    
    elif action == "get_pnl_yesterday":
        # Кеш по вчерашней дате
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        return f"{api_hash}_{action}_{yesterday}"
    
    elif action == "get_pnl_current_month":
        # Кеш по текущему месяцу
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        return f"{api_hash}_{action}_{current_month}"
    
    elif action == "get_pnl_previous_month":
        # Кеш по предыдущему месяцу
        current = datetime.now(timezone.utc)
        if current.month == 1:
            prev_month = f"{current.year - 1}-12"
        else:
            prev_month = f"{current.year}-{current.month - 1:02d}"
        return f"{api_hash}_{action}_{prev_month}"
    
    elif action == "get_pnl_custom":
        # Кеш по диапазону дат
        if start_datetime and end_datetime:
            return f"{api_hash}_{action}_{start_datetime}_{end_datetime}"
    
    return f"{api_hash}_{action}_unknown"


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
