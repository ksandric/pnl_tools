import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta


def generate_signature(api_secret, params):
    """Генерация подписи для запроса"""
    param_str = urlencode(sorted(params.items()))
    hash_obj = hmac.new(
        bytes(api_secret, "utf-8"),
        bytes(param_str, "utf-8"),
        hashlib.sha256
    )
    return hash_obj.hexdigest()


def send_request(api_key, api_secret, endpoint, params=None):
    """Отправка запроса к API Bybit"""
    if params is None:
        params = {}

    base_url = "https://api.bybit.com"
    timestamp = str(int(time.time() * 1000))

    params["api_key"] = api_key
    params["timestamp"] = timestamp
    params["recv_window"] = "5000"

    signature = generate_signature(api_secret, params)
    params["sign"] = signature

    url = f"{base_url}{endpoint}"

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса: {e}")
        return None


def get_closed_pnl(api_key, api_secret, category="linear", symbol=None,
                   start_time=None, end_time=None, limit=50, cursor=None):
    """Получение одной страницы закрытых позиций"""
    endpoint = "/v5/position/closed-pnl"
    params = {
        "category": category,
        "limit": min(limit, 100)
    }

    if symbol:
        params["symbol"] = symbol
    if start_time:
        params["startTime"] = start_time
    if end_time:
        params["endTime"] = end_time
    if cursor:
        params["cursor"] = cursor

    response = send_request(api_key, api_secret, endpoint, params)

    if response and response.get("retCode") == 0:
        return response.get("result", {})
    else:
        print(f"Ошибка API: {response}")
        return {}


def get_all_closed_pnl(api_key, api_secret, category="linear", symbol=None,
                       start_time=None, end_time=None):
    """Получение всех закрытых позиций с пагинацией и разбивкой на периоды по 7 дней"""

    # Если указаны временные рамки, проверяем их размер
    if start_time and end_time:
        # Максимальный диапазон - 7 дней в миллисекундах
        max_range_ms = 7 * 24 * 60 * 60 * 1000
        time_diff = end_time - start_time

        # Если диапазон больше 7 дней, разбиваем на куски
        if time_diff > max_range_ms:
            print(f"Диапазон превышает 7 дней, разбиваем на периоды...")
            all_data = []
            current_start = start_time

            while current_start < end_time:
                current_end = min(current_start + max_range_ms, end_time)

                print(
                    f"\nЗагрузка периода: {datetime.fromtimestamp(current_start / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(current_end / 1000, tz=timezone.utc)}")

                period_data = get_all_closed_pnl_single_period(
                    api_key, api_secret, category, symbol, current_start, current_end
                )

                all_data.extend(period_data)
                current_start = current_end + 1  # Переходим к следующему периоду

                # Задержка между периодами
                time.sleep(0.3)

            print(f"\nВсего загружено записей за весь период: {len(all_data)}")
            return all_data

    # Если диапазон 7 дней или меньше (или не указан), используем обычную загрузку
    return get_all_closed_pnl_single_period(api_key, api_secret, category, symbol, start_time, end_time)


def get_all_closed_pnl_single_period(api_key, api_secret, category="linear", symbol=None,
                                     start_time=None, end_time=None):
    """Получение всех закрытых позиций для одного периода (до 7 дней) с пагинацией"""
    all_data = []
    cursor = None
    page = 1

    while True:
        print(f"  Загрузка страницы {page}...")

        result = get_closed_pnl(
            api_key, api_secret, category, symbol,
            start_time, end_time, limit=100, cursor=cursor
        )

        if not result:
            break

        data_list = result.get("list", [])

        if not data_list:
            break

        all_data.extend(data_list)
        print(f"  Получено записей: {len(data_list)}")

        # Проверка наличия следующей страницы
        next_cursor = result.get("nextPageCursor")
        if not next_cursor:
            break

        cursor = next_cursor
        page += 1

        # Небольшая задержка между запросами
        time.sleep(0.2)

    print(f"  Всего записей за период: {len(all_data)}")
    return all_data


def get_current_day_utc():
    """Получить начало и конец текущего дня по UTC в миллисекундах"""
    now = datetime.now(timezone.utc)
    start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
    end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59, 999999, tzinfo=timezone.utc)

    start_ms = int(start_of_day.timestamp() * 1000)
    end_ms = int(end_of_day.timestamp() * 1000)

    return start_ms, end_ms


def get_previous_day_utc():
    """Получить начало и конец прошлого дня по UTC в миллисекундах"""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    start_of_day = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0, tzinfo=timezone.utc)
    end_of_day = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59, 999999, tzinfo=timezone.utc)

    start_ms = int(start_of_day.timestamp() * 1000)
    end_ms = int(end_of_day.timestamp() * 1000)

    return start_ms, end_ms


def get_current_month_utc():
    """Получить начало и конец текущего месяца по UTC в миллисекундах"""
    now = datetime.now(timezone.utc)
    start_of_month = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Конец текущего месяца - это текущий момент
    end_of_month = now

    start_ms = int(start_of_month.timestamp() * 1000)
    end_ms = int(end_of_month.timestamp() * 1000)

    return start_ms, end_ms


def get_previous_month_utc():
    """Получить начало и конец прошлого месяца по UTC в миллисекундах"""
    now = datetime.now(timezone.utc)

    # Первый день текущего месяца
    first_day_current_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # Последний день прошлого месяца
    last_day_previous_month = first_day_current_month - timedelta(days=1)

    # Первый день прошлого месяца
    start_of_month = datetime(last_day_previous_month.year, last_day_previous_month.month, 1, 0, 0, 0,
                              tzinfo=timezone.utc)

    # Последний момент прошлого месяца
    end_of_month = datetime(last_day_previous_month.year, last_day_previous_month.month, last_day_previous_month.day,
                            23, 59, 59, 999999, tzinfo=timezone.utc)

    start_ms = int(start_of_month.timestamp() * 1000)
    end_ms = int(end_of_month.timestamp() * 1000)

    return start_ms, end_ms


def get_pnl_today(api_key, api_secret, category="linear", symbol=None):
    """Получить данные за текущий день по UTC"""
    start_ms, end_ms = get_current_day_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_closed_pnl(api_key, api_secret, category, symbol, start_ms, end_ms)


def get_pnl_yesterday(api_key, api_secret, category="linear", symbol=None):
    """Получить данные за прошлый день по UTC"""
    start_ms, end_ms = get_previous_day_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_closed_pnl(api_key, api_secret, category, symbol, start_ms, end_ms)


def get_pnl_current_month(api_key, api_secret, category="linear", symbol=None):
    """Получить данные за текущий месяц по UTC"""
    start_ms, end_ms = get_current_month_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_closed_pnl(api_key, api_secret, category, symbol, start_ms, end_ms)


def get_pnl_previous_month(api_key, api_secret, category="linear", symbol=None):
    """Получить данные за прошлый месяц по UTC"""
    start_ms, end_ms = get_previous_month_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_closed_pnl(api_key, api_secret, category, symbol, start_ms, end_ms)
