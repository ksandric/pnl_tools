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


# ============================================================================
# Функции для работы с исполненными сделками на споте /v5/execution/list
# ============================================================================

def get_execution_list(api_key, api_secret, category="spot", symbol=None,
                       start_time=None, end_time=None, limit=50, cursor=None):
    """Получение одной страницы исполненных сделок"""
    endpoint = "/v5/execution/list"
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


def get_all_executions(api_key, api_secret, category="spot", symbol=None,
                       start_time=None, end_time=None):
    """Получение всех исполненных сделок с пагинацией и разбивкой на периоды по 7 дней"""

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

                period_data = get_all_executions_single_period(
                    api_key, api_secret, category, symbol, current_start, current_end
                )

                all_data.extend(period_data)
                current_start = current_end + 1  # Переходим к следующему периоду

                # Задержка между периодами
                time.sleep(0.3)

            print(f"\nВсего загружено записей за весь период: {len(all_data)}")
            return all_data

    # Если диапазон 7 дней или меньше (или не указан), используем обычную загрузку
    return get_all_executions_single_period(api_key, api_secret, category, symbol, start_time, end_time)


def get_all_executions_single_period(api_key, api_secret, category="spot", symbol=None,
                                     start_time=None, end_time=None):
    """Получение всех исполненных сделок для одного периода (до 7 дней) с пагинацией"""
    all_data = []
    cursor = None
    page = 1

    while True:
        print(f"  Загрузка страницы {page}...")

        result = get_execution_list(
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


def get_executions_today(api_key, api_secret, category="spot", symbol=None):
    """Получить исполненные сделки за текущий день по UTC"""
    start_ms, end_ms = get_current_day_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_executions(api_key, api_secret, category, symbol, start_ms, end_ms)


def get_executions_yesterday(api_key, api_secret, category="spot", symbol=None):
    """Получить исполненные сделки за прошлый день по UTC"""
    start_ms, end_ms = get_previous_day_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_executions(api_key, api_secret, category, symbol, start_ms, end_ms)


def get_executions_current_month(api_key, api_secret, category="spot", symbol=None):
    """Получить исполненные сделки за текущий месяц по UTC"""
    start_ms, end_ms = get_current_month_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_executions(api_key, api_secret, category, symbol, start_ms, end_ms)


def get_executions_previous_month(api_key, api_secret, category="spot", symbol=None):
    """Получить исполненные сделки за прошлый месяц по UTC"""
    start_ms, end_ms = get_previous_month_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_executions(api_key, api_secret, category, symbol, start_ms, end_ms)


# ============================================================================
# Функции для работы с внутренними переводами /v5/asset/transfer/query-inter-transfer-list
# ============================================================================

def get_inter_transfer_list(api_key, api_secret, coin=None,
                            start_time=None, end_time=None, limit=50, cursor=None):
    """Получение одной страницы внутренних переводов"""
    endpoint = "/v5/asset/transfer/query-inter-transfer-list"
    params = {
        "limit": min(limit, 50)  # Максимум 50 для этого эндпоинта
    }

    if coin:
        params["coin"] = coin
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


def get_all_inter_transfers(api_key, api_secret, coin=None,
                            start_time=None, end_time=None):
    """Получение всех внутренних переводов с пагинацией и разбивкой на периоды по 30 дней"""

    # Если указаны временные рамки, проверяем их размер
    if start_time and end_time:
        # Максимальный диапазон - 30 дней в миллисекундах
        max_range_ms = 30 * 24 * 60 * 60 * 1000
        time_diff = end_time - start_time

        # Если диапазон больше 30 дней, разбиваем на куски
        if time_diff > max_range_ms:
            print(f"Диапазон превышает 30 дней, разбиваем на периоды...")
            all_data = []
            current_start = start_time

            while current_start < end_time:
                current_end = min(current_start + max_range_ms, end_time)

                print(
                    f"\nЗагрузка периода: {datetime.fromtimestamp(current_start / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(current_end / 1000, tz=timezone.utc)}")

                period_data = get_all_inter_transfers_single_period(
                    api_key, api_secret, coin, current_start, current_end
                )

                all_data.extend(period_data)
                current_start = current_end + 1  # Переходим к следующему периоду

                # Задержка между периодами
                time.sleep(0.3)

            print(f"\nВсего загружено записей за весь период: {len(all_data)}")
            return all_data

    # Если диапазон 30 дней или меньше (или не указан), используем обычную загрузку
    return get_all_inter_transfers_single_period(api_key, api_secret, coin, start_time, end_time)


def get_all_inter_transfers_single_period(api_key, api_secret, coin=None,
                                         start_time=None, end_time=None):
    """Получение всех внутренних переводов для одного периода (до 30 дней) с пагинацией"""
    all_data = []
    cursor = None
    page = 1

    while True:
        print(f"  Загрузка страницы {page}...")

        result = get_inter_transfer_list(
            api_key, api_secret, coin,
            start_time, end_time, limit=50, cursor=cursor
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


def get_inter_transfers_today(api_key, api_secret, coin=None):
    """Получить внутренние переводы за текущий день по UTC"""
    start_ms, end_ms = get_current_day_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_inter_transfers(api_key, api_secret, coin, start_ms, end_ms)


def get_inter_transfers_yesterday(api_key, api_secret, coin=None):
    """Получить внутренние переводы за прошлый день по UTC"""
    start_ms, end_ms = get_previous_day_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_inter_transfers(api_key, api_secret, coin, start_ms, end_ms)


def get_inter_transfers_current_month(api_key, api_secret, coin=None):
    """Получить внутренние переводы за текущий месяц по UTC"""
    start_ms, end_ms = get_current_month_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_inter_transfers(api_key, api_secret, coin, start_ms, end_ms)


def get_inter_transfers_previous_month(api_key, api_secret, coin=None):
    """Получить внутренние переводы за прошлый месяц по UTC"""
    start_ms, end_ms = get_previous_month_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_inter_transfers(api_key, api_secret, coin, start_ms, end_ms)


# ============================================================================
# Функции для работы с внешними переводами /v5/asset/transfer/query-universal-transfer-list
# ============================================================================

def get_universal_transfer_list(api_key, api_secret, coin=None,
                                start_time=None, end_time=None, limit=50, cursor=None):
    """Получение одной страницы универсальных (внешних) переводов"""
    endpoint = "/v5/asset/transfer/query-universal-transfer-list"
    params = {
        "limit": min(limit, 50)  # Максимум 50 для этого эндпоинта
    }

    if coin:
        params["coin"] = coin
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


def get_all_universal_transfers(api_key, api_secret, coin=None,
                                start_time=None, end_time=None):
    """Получение всех универсальных переводов с пагинацией и разбивкой на периоды по 30 дней"""

    # Если указаны временные рамки, проверяем их размер
    if start_time and end_time:
        # Максимальный диапазон - 30 дней в миллисекундах
        max_range_ms = 30 * 24 * 60 * 60 * 1000
        time_diff = end_time - start_time

        # Если диапазон больше 30 дней, разбиваем на куски
        if time_diff > max_range_ms:
            print(f"Диапазон превышает 30 дней, разбиваем на периоды...")
            all_data = []
            current_start = start_time

            while current_start < end_time:
                current_end = min(current_start + max_range_ms, end_time)

                print(
                    f"\nЗагрузка периода: {datetime.fromtimestamp(current_start / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(current_end / 1000, tz=timezone.utc)}")

                period_data = get_all_universal_transfers_single_period(
                    api_key, api_secret, coin, current_start, current_end
                )

                all_data.extend(period_data)
                current_start = current_end + 1  # Переходим к следующему периоду

                # Задержка между периодами
                time.sleep(0.3)

            print(f"\nВсего загружено записей за весь период: {len(all_data)}")
            return all_data

    # Если диапазон 30 дней или меньше (или не указан), используем обычную загрузку
    return get_all_universal_transfers_single_period(api_key, api_secret, coin, start_time, end_time)


def get_all_universal_transfers_single_period(api_key, api_secret, coin=None,
                                              start_time=None, end_time=None):
    """Получение всех универсальных переводов для одного периода (до 30 дней) с пагинацией"""
    all_data = []
    cursor = None
    page = 1

    while True:
        print(f"  Загрузка страницы {page}...")

        result = get_universal_transfer_list(
            api_key, api_secret, coin,
            start_time, end_time, limit=50, cursor=cursor
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


def get_universal_transfers_today(api_key, api_secret, coin=None):
    """Получить универсальные переводы за текущий день по UTC"""
    start_ms, end_ms = get_current_day_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_universal_transfers(api_key, api_secret, coin, start_ms, end_ms)


def get_universal_transfers_yesterday(api_key, api_secret, coin=None):
    """Получить универсальные переводы за прошлый день по UTC"""
    start_ms, end_ms = get_previous_day_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_universal_transfers(api_key, api_secret, coin, start_ms, end_ms)


def get_universal_transfers_current_month(api_key, api_secret, coin=None):
    """Получить универсальные переводы за текущий месяц по UTC"""
    start_ms, end_ms = get_current_month_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_universal_transfers(api_key, api_secret, coin, start_ms, end_ms)


def get_universal_transfers_previous_month(api_key, api_secret, coin=None):
    """Получить универсальные переводы за прошлый месяц по UTC"""
    start_ms, end_ms = get_previous_month_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_universal_transfers(api_key, api_secret, coin, start_ms, end_ms)


# ============================================================================
# Функции для работы с выводами средств /v5/asset/withdraw/query-record
# ============================================================================

def get_withdraw_record(api_key, api_secret, coin=None, withdraw_type=None,
                        start_time=None, end_time=None, limit=50, cursor=None):
    """Получение одной страницы записей о выводах"""
    endpoint = "/v5/asset/withdraw/query-record"
    params = {
        "limit": min(limit, 50)  # Максимум 50 для этого эндпоинта
    }

    if coin:
        params["coin"] = coin
    if withdraw_type:
        params["withdrawType"] = withdraw_type
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


def get_all_withdraws(api_key, api_secret, coin=None, withdraw_type=None,
                     start_time=None, end_time=None):
    """Получение всех записей о выводах с пагинацией и разбивкой на периоды по 30 дней"""

    # Если указаны временные рамки, проверяем их размер
    if start_time and end_time:
        # Максимальный диапазон - 30 дней в миллисекундах
        max_range_ms = 30 * 24 * 60 * 60 * 1000
        time_diff = end_time - start_time

        # Если диапазон больше 30 дней, разбиваем на куски
        if time_diff > max_range_ms:
            print(f"Диапазон превышает 30 дней, разбиваем на периоды...")
            all_data = []
            current_start = start_time

            while current_start < end_time:
                current_end = min(current_start + max_range_ms, end_time)

                print(
                    f"\nЗагрузка периода: {datetime.fromtimestamp(current_start / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(current_end / 1000, tz=timezone.utc)}")

                period_data = get_all_withdraws_single_period(
                    api_key, api_secret, coin, withdraw_type, current_start, current_end
                )

                all_data.extend(period_data)
                current_start = current_end + 1  # Переходим к следующему периоду

                # Задержка между периодами
                time.sleep(0.3)

            print(f"\nВсего загружено записей за весь период: {len(all_data)}")
            return all_data

    # Если диапазон 30 дней или меньше (или не указан), используем обычную загрузку
    return get_all_withdraws_single_period(api_key, api_secret, coin, withdraw_type, start_time, end_time)


def get_all_withdraws_single_period(api_key, api_secret, coin=None, withdraw_type=None,
                                   start_time=None, end_time=None):
    """Получение всех записей о выводах для одного периода (до 30 дней) с пагинацией"""
    all_data = []
    cursor = None
    page = 1

    while True:
        print(f"  Загрузка страницы {page}...")

        result = get_withdraw_record(
            api_key, api_secret, coin, withdraw_type,
            start_time, end_time, limit=50, cursor=cursor
        )

        if not result:
            break

        data_list = result.get("rows", [])  # Для withdraw используется "rows", а не "list"

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


def get_withdraws_today(api_key, api_secret, coin=None, withdraw_type=None):
    """Получить записи о выводах за текущий день по UTC"""
    start_ms, end_ms = get_current_day_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_withdraws(api_key, api_secret, coin, withdraw_type, start_ms, end_ms)


def get_withdraws_yesterday(api_key, api_secret, coin=None, withdraw_type=None):
    """Получить записи о выводах за прошлый день по UTC"""
    start_ms, end_ms = get_previous_day_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_withdraws(api_key, api_secret, coin, withdraw_type, start_ms, end_ms)


def get_withdraws_current_month(api_key, api_secret, coin=None, withdraw_type=None):
    """Получить записи о выводах за текущий месяц по UTC"""
    start_ms, end_ms = get_current_month_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_withdraws(api_key, api_secret, coin, withdraw_type, start_ms, end_ms)


def get_withdraws_previous_month(api_key, api_secret, coin=None, withdraw_type=None):
    """Получить записи о выводах за прошлый месяц по UTC"""
    start_ms, end_ms = get_previous_month_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_withdraws(api_key, api_secret, coin, withdraw_type, start_ms, end_ms)


# ============================================================================
# Функции для работы с депозитами средств /v5/asset/deposit/query-record
# ============================================================================

def get_deposit_record(api_key, api_secret, coin=None,
                       start_time=None, end_time=None, limit=50, cursor=None):
    """Получение одной страницы записей о депозитах"""
    endpoint = "/v5/asset/deposit/query-record"
    params = {
        "limit": min(limit, 50)  # Максимум 50 для этого эндпоинта
    }

    if coin:
        params["coin"] = coin
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


def get_all_deposits(api_key, api_secret, coin=None,
                    start_time=None, end_time=None):
    """Получение всех записей о депозитах с пагинацией и разбивкой на периоды по 30 дней"""

    # Если указаны временные рамки, проверяем их размер
    if start_time and end_time:
        # Максимальный диапазон - 30 дней в миллисекундах
        max_range_ms = 30 * 24 * 60 * 60 * 1000
        time_diff = end_time - start_time

        # Если диапазон больше 30 дней, разбиваем на куски
        if time_diff > max_range_ms:
            print(f"Диапазон превышает 30 дней, разбиваем на периоды...")
            all_data = []
            current_start = start_time

            while current_start < end_time:
                current_end = min(current_start + max_range_ms, end_time)

                print(
                    f"\nЗагрузка периода: {datetime.fromtimestamp(current_start / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(current_end / 1000, tz=timezone.utc)}")

                period_data = get_all_deposits_single_period(
                    api_key, api_secret, coin, current_start, current_end
                )

                all_data.extend(period_data)
                current_start = current_end + 1  # Переходим к следующему периоду

                # Задержка между периодами
                time.sleep(0.3)

            print(f"\nВсего загружено записей за весь период: {len(all_data)}")
            return all_data

    # Если диапазон 30 дней или меньше (или не указан), используем обычную загрузку
    return get_all_deposits_single_period(api_key, api_secret, coin, start_time, end_time)


def get_all_deposits_single_period(api_key, api_secret, coin=None,
                                  start_time=None, end_time=None):
    """Получение всех записей о депозитах для одного периода (до 30 дней) с пагинацией"""
    all_data = []
    cursor = None
    page = 1

    while True:
        print(f"  Загрузка страницы {page}...")

        result = get_deposit_record(
            api_key, api_secret, coin,
            start_time, end_time, limit=50, cursor=cursor
        )

        if not result:
            break

        data_list = result.get("rows", [])  # Для deposit используется "rows", а не "list"

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


def get_deposits_today(api_key, api_secret, coin=None):
    """Получить записи о депозитах за текущий день по UTC"""
    start_ms, end_ms = get_current_day_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_deposits(api_key, api_secret, coin, start_ms, end_ms)


def get_deposits_yesterday(api_key, api_secret, coin=None):
    """Получить записи о депозитах за прошлый день по UTC"""
    start_ms, end_ms = get_previous_day_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_deposits(api_key, api_secret, coin, start_ms, end_ms)


def get_deposits_current_month(api_key, api_secret, coin=None):
    """Получить записи о депозитах за текущий месяц по UTC"""
    start_ms, end_ms = get_current_month_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_deposits(api_key, api_secret, coin, start_ms, end_ms)


def get_deposits_previous_month(api_key, api_secret, coin=None):
    """Получить записи о депозитах за прошлый месяц по UTC"""
    start_ms, end_ms = get_previous_month_utc()
    print(
        f"Период: {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)} - {datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)}")
    return get_all_deposits(api_key, api_secret, coin, start_ms, end_ms)


# ============================================================================
# Функции для работы с информацией об API ключе /v5/user/query-api
# ============================================================================

def query_api_key_info(api_key, api_secret):
    """Получение информации об API ключе"""
    endpoint = "/v5/user/query-api"
    params = {}

    response = send_request(api_key, api_secret, endpoint, params)

    if response and response.get("retCode") == 0:
        result = response.get("result", {})
        
        # Форматированный вывод информации
        if result:
            print("\n=== Информация об API ключе ===")
            print(f"ID: {result.get('id', 'N/A')}")
            print(f"Note: {result.get('note', 'N/A')}")
            print(f"API Key: {result.get('apiKey', 'N/A')}")
            print(f"Read Only: {result.get('readOnly', 'N/A')}")
            print(f"Secret: {'***' if result.get('secret') else 'N/A'}")
            print(f"Permissions: {result.get('permissions', {})}")
            print(f"IPs: {result.get('ips', [])}")
            print(f"Type: {result.get('type', 'N/A')}")
            print(f"Deadlink Time: {result.get('deadlineDay', 'N/A')}")
            print(f"Expired At: {result.get('expiredAt', 'N/A')}")
            print(f"Created At: {result.get('createdAt', 'N/A')}")
            print(f"Unified: {result.get('unified', 'N/A')}")
            print(f"UTA: {result.get('uta', 'N/A')}")
            print(f"User ID: {result.get('userID', 'N/A')}")
            print(f"Inviter ID: {result.get('inviterID', 'N/A')}")
            print(f"VIP Level: {result.get('vipLevel', 'N/A')}")
            print(f"MKT Maker Level: {result.get('mktMakerLevel', 'N/A')}")
            print(f"Affiliate ID: {result.get('affiliateID', 'N/A')}")
            print(f"RSA Public Key: {result.get('rsaPublicKey', 'N/A')}")
            print(f"Is Parent Key: {result.get('isMaster', 'N/A')}")
            print("=" * 35)
        
        return result
    else:
        print(f"Ошибка API: {response}")
        return {}


# ============================================================================
# Функции для работы с балансом кошелька /v5/account/wallet-balance
# ============================================================================

def get_wallet_balance(api_key, api_secret, account_type="UNIFIED", coin=None):
    """Получение баланса кошелька
    
    Args:
        api_key: API ключ
        api_secret: API секрет
        account_type: Тип аккаунта (UNIFIED, CONTRACT, SPOT, INVESTMENT, OPTION, FUND)
        coin: Название монеты (опционально, для фильтрации по конкретной монете)
    
    Returns:
        dict: Информация о балансе кошелька
    """
    endpoint = "/v5/account/wallet-balance"
    params = {
        "accountType": account_type
    }
    
    if coin:
        params["coin"] = coin

    response = send_request(api_key, api_secret, endpoint, params)

    if response and response.get("retCode") == 0:
        result = response.get("result", {})
        
        # Форматированный вывод информации
        if result and result.get("list"):
            print(f"\n=== Баланс кошелька ({account_type}) ===")
            
            for account in result.get("list", []):
                print(f"\nAccount Type: {account.get('accountType', 'N/A')}")
                print(f"Account LTV: {account.get('accountLTV', 'N/A')}")
                print(f"Account IMR: {account.get('accountIMR', 'N/A')}")
                print(f"Account MMR: {account.get('accountMMR', 'N/A')}")
                print(f"Total Equity: {account.get('totalEquity', 'N/A')}")
                print(f"Total Wallet Balance: {account.get('totalWalletBalance', 'N/A')}")
                print(f"Total Margin Balance: {account.get('totalMarginBalance', 'N/A')}")
                print(f"Total Available Balance: {account.get('totalAvailableBalance', 'N/A')}")
                print(f"Total Perp UPL: {account.get('totalPerpUPL', 'N/A')}")
                print(f"Total Initial Margin: {account.get('totalInitialMargin', 'N/A')}")
                print(f"Total Maintenance Margin: {account.get('totalMaintenanceMargin', 'N/A')}")
                
                coins = account.get("coin", [])
                if coins:
                    print(f"\nМонеты ({len(coins)}):")
                    for coin_data in coins:
                        print(f"  {coin_data.get('coin', 'N/A')}:")
                        print(f"    Equity: {coin_data.get('equity', 'N/A')}")
                        print(f"    UsdValue: {coin_data.get('usdValue', 'N/A')}")
                        print(f"    Wallet Balance: {coin_data.get('walletBalance', 'N/A')}")
                        print(f"    Available: {coin_data.get('availableToWithdraw', 'N/A')}")
                        print(f"    Borrowed: {coin_data.get('borrowed', 'N/A')}")
                        print(f"    Free: {coin_data.get('free', 'N/A')}")
                        print(f"    Locked: {coin_data.get('locked', 'N/A')}")
                
                print("-" * 50)
            
            print("=" * 50)
        
        return result
    else:
        print(f"Ошибка API: {response}")
        return {}


# ============================================================================
# Функции для работы со списком позиций /v5/position/list
# ============================================================================

def get_position_list(api_key, api_secret, category="linear", symbol=None, 
                     base_coin=None, settle_coin=None, limit=200, cursor=None):
    """Получение списка позиций
    
    Args:
        api_key: API ключ
        api_secret: API секрет
        category: Тип продукта (linear, inverse, option)
        symbol: Символ (опционально)
        base_coin: Базовая монета (для option)
        settle_coin: Монета расчета (опционально)
        limit: Лимит записей (макс 200)
        cursor: Курсор для пагинации
    
    Returns:
        dict: Результат с информацией о позициях
    """
    endpoint = "/v5/position/list"
    params = {
        "category": category,
        "limit": min(limit, 200)
    }
    
    if symbol:
        params["symbol"] = symbol
    if base_coin:
        params["baseCoin"] = base_coin
    if settle_coin:
        params["settleCoin"] = settle_coin
    if cursor:
        params["cursor"] = cursor

    response = send_request(api_key, api_secret, endpoint, params)

    if response and response.get("retCode") == 0:
        return response.get("result", {})
    else:
        print(f"Ошибка API: {response}")
        return {}


def get_all_positions(api_key, api_secret, category="linear", symbol=None,
                     base_coin=None, settle_coin="USDT"):
    """Получение всех позиций с пагинацией
    
    Args:
        api_key: API ключ
        api_secret: API секрет
        category: Тип продукта (linear, inverse, option)
        symbol: Символ (опционально)
        base_coin: Базовая монета (для option)
        settle_coin: Монета расчета (опционально)
    
    Returns:
        list: Список всех позиций
    """
    all_positions = []
    cursor = None
    page = 1

    while True:
        print(f"  Загрузка страницы {page}...")

        result = get_position_list(
            api_key, api_secret, category, symbol,
            base_coin, settle_coin, limit=200, cursor=cursor
        )

        if not result:
            break

        positions_list = result.get("list", [])

        if not positions_list:
            break

        all_positions.extend(positions_list)
        print(f"  Получено позиций: {len(positions_list)}")

        # Проверка наличия следующей страницы
        next_cursor = result.get("nextPageCursor")
        if not next_cursor:
            break

        cursor = next_cursor
        page += 1

        # Небольшая задержка между запросами
        time.sleep(0.2)

    print(f"  Всего позиций: {len(all_positions)}")
    
    # Форматированный вывод
    if all_positions:
        print(f"\n=== Позиции ({category}) ===")
        for pos in all_positions:
            print(f"\n{pos.get('symbol', 'N/A')}:")
            print(f"  Side: {pos.get('side', 'N/A')}")
            print(f"  Size: {pos.get('size', 'N/A')}")
            print(f"  Position Value: {pos.get('positionValue', 'N/A')}")
            print(f"  Entry Price: {pos.get('avgPrice', 'N/A')}")
            print(f"  Mark Price: {pos.get('markPrice', 'N/A')}")
            print(f"  Liq Price: {pos.get('liqPrice', 'N/A')}")
            print(f"  Unrealised PnL: {pos.get('unrealisedPnl', 'N/A')}")
            print(f"  Cumulative PnL: {pos.get('cumRealisedPnl', 'N/A')}")
            print(f"  Leverage: {pos.get('leverage', 'N/A')}")
            print(f"  Position Status: {pos.get('positionStatus', 'N/A')}")
            print(f"  TP/SL Mode: {pos.get('tpslMode', 'N/A')}")
            print(f"  Take Profit: {pos.get('takeProfit', 'N/A')}")
            print(f"  Stop Loss: {pos.get('stopLoss', 'N/A')}")
            print(f"  Trailing Stop: {pos.get('trailingStop', 'N/A')}")
        print("=" * 50)
    
    return all_positions

