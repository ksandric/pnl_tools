"""
Модуль для анализа результатов торгов на Bybit UTA
Включает кэширование данных, синхронизацию и расчёт доходности
"""

import os
import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

import exchange


# ============================================================================
# Константы
# ============================================================================

CACHE_DIR = "cache"
MAX_HISTORY_DAYS = 730  # 2 года - максимум для Transaction Log API


# ============================================================================
# Функции для работы с кэшем
# ============================================================================

def get_cache_path(user_id, data_type):
    """Получить путь к файлу кэша
    
    Args:
        user_id: ID пользователя (из API key info)
        data_type: Тип данных (transaction_logs, deposits, withdrawals, metadata)
    
    Returns:
        str: Путь к файлу кэша
    """
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    return os.path.join(CACHE_DIR, f"{user_id}_{data_type}.json")


def load_cached_data(user_id, data_type):
    """Загрузить данные из кэша
    
    Args:
        user_id: ID пользователя
        data_type: Тип данных
    
    Returns:
        list или dict: Загруженные данные или пустой список/словарь
    """
    cache_path = get_cache_path(user_id, data_type)
    
    if not os.path.exists(cache_path):
        return [] if data_type != "metadata" else {}
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Загружено из кэша {data_type}: {len(data) if isinstance(data, list) else 'metadata'}")
            return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"Ошибка загрузки кэша {data_type}: {e}")
        return [] if data_type != "metadata" else {}


def save_cached_data(user_id, data_type, data):
    """Сохранить данные в кэш
    
    Args:
        user_id: ID пользователя
        data_type: Тип данных
        data: Данные для сохранения
    """
    cache_path = get_cache_path(user_id, data_type)
    
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Сохранено в кэш {data_type}: {len(data) if isinstance(data, list) else 'metadata'}")
    except IOError as e:
        print(f"Ошибка сохранения кэша {data_type}: {e}")


def get_metadata(user_id):
    """Получить метаданные синхронизации"""
    return load_cached_data(user_id, "metadata")


def save_metadata(user_id, metadata):
    """Сохранить метаданные синхронизации"""
    save_cached_data(user_id, "metadata", metadata)


def update_sync_time(user_id, data_type):
    """Обновить время последней синхронизации для типа данных"""
    metadata = get_metadata(user_id)
    
    if "last_sync" not in metadata:
        metadata["last_sync"] = {}
    
    metadata["last_sync"][data_type] = datetime.now(timezone.utc).isoformat()
    save_metadata(user_id, metadata)


def get_last_sync_time(user_id, data_type):
    """Получить время последней синхронизации
    
    Returns:
        datetime или None
    """
    metadata = get_metadata(user_id)
    
    last_sync_str = metadata.get("last_sync", {}).get(data_type)
    if last_sync_str:
        return datetime.fromisoformat(last_sync_str)
    return None


def merge_and_dedupe(existing_data, new_data, id_field="id"):
    """Объединить данные и удалить дубликаты
    
    Args:
        existing_data: Существующие данные
        new_data: Новые данные
        id_field: Поле для идентификации уникальных записей
    
    Returns:
        list: Объединённые данные без дубликатов
    """
    if not existing_data:
        return new_data
    if not new_data:
        return existing_data
    
    # Создаём словарь по id для быстрого поиска
    data_dict = {item.get(id_field): item for item in existing_data}
    
    # Добавляем новые записи (перезаписываем если уже есть)
    for item in new_data:
        data_dict[item.get(id_field)] = item
    
    # Возвращаем как список
    return list(data_dict.values())


def get_newest_timestamp(data, time_field="transactionTime"):
    """Получить самую новую метку времени из данных
    
    Returns:
        int: Timestamp в миллисекундах или None
    """
    if not data:
        return None
    
    timestamps = []
    for item in data:
        ts = item.get(time_field)
        if ts:
            timestamps.append(int(ts))
    
    return max(timestamps) if timestamps else None


def get_oldest_timestamp(data, time_field="transactionTime"):
    """Получить самую старую метку времени из данных
    
    Returns:
        int: Timestamp в миллисекундах или None
    """
    if not data:
        return None
    
    timestamps = []
    for item in data:
        ts = item.get(time_field)
        if ts:
            timestamps.append(int(ts))
    
    return min(timestamps) if timestamps else None


# ============================================================================
# Функции синхронизации данных
# ============================================================================

def sync_transaction_logs(api_key, api_secret, currency="USDT", full_reload=False):
    """Синхронизировать логи транзакций
    
    Args:
        api_key: API ключ
        api_secret: API секрет
        currency: Валюта для фильтрации (USDT, USDC и т.д.)
        full_reload: Если True - полная перезагрузка за 2 года
    
    Returns:
        list: Синхронизированные данные
    """
    print("\n=== Синхронизация Transaction Logs ===")
    
    user_id = exchange.get_user_id(api_key, api_secret)
    cached_data = load_cached_data(user_id, "transaction_logs")
    
    now = datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    
    if full_reload or not cached_data:
        # Полная загрузка за 2 года
        print("Полная загрузка данных за 2 года...")
        start_time = now - timedelta(days=MAX_HISTORY_DAYS)
        start_ms = int(start_time.timestamp() * 1000)
        
        new_data = exchange.get_all_transaction_logs(
            api_key, api_secret,
            account_type="UNIFIED",
            currency=currency,
            start_time=start_ms,
            end_time=now_ms
        )
        
        merged_data = new_data
    else:
        # Инкрементальная загрузка
        newest_ts = get_newest_timestamp(cached_data, "transactionTime")
        
        if newest_ts:
            # Загружаем с последней записи + 1 мс
            start_ms = newest_ts + 1
            print(f"Инкрементальная загрузка с {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)}")
        else:
            # Нет данных в кэше - загружаем за 2 года
            start_time = now - timedelta(days=MAX_HISTORY_DAYS)
            start_ms = int(start_time.timestamp() * 1000)
        
        new_data = exchange.get_all_transaction_logs(
            api_key, api_secret,
            account_type="UNIFIED",
            currency=currency,
            start_time=start_ms,
            end_time=now_ms
        )
        
        merged_data = merge_and_dedupe(cached_data, new_data, "id")
    
    # Сортируем по времени
    merged_data.sort(key=lambda x: int(x.get("transactionTime", 0)))
    
    # Сохраняем в кэш
    save_cached_data(user_id, "transaction_logs", merged_data)
    update_sync_time(user_id, "transaction_logs")
    
    # Обновляем метаданные о диапазоне данных
    metadata = get_metadata(user_id)
    if "data_range" not in metadata:
        metadata["data_range"] = {}
    
    oldest = get_oldest_timestamp(merged_data, "transactionTime")
    newest = get_newest_timestamp(merged_data, "transactionTime")
    
    if oldest and newest:
        metadata["data_range"]["transaction_logs"] = {
            "oldest": datetime.fromtimestamp(oldest / 1000, tz=timezone.utc).isoformat(),
            "newest": datetime.fromtimestamp(newest / 1000, tz=timezone.utc).isoformat(),
            "count": len(merged_data)
        }
    
    metadata["user_id"] = user_id
    metadata["currency"] = currency
    save_metadata(user_id, metadata)
    
    print(f"Всего записей после синхронизации: {len(merged_data)}")
    return merged_data


def sync_deposits(api_key, api_secret, coin=None, full_reload=False):
    """Синхронизировать депозиты
    
    Args:
        api_key: API ключ
        api_secret: API секрет
        coin: Монета для фильтрации
        full_reload: Если True - полная перезагрузка
    
    Returns:
        list: Синхронизированные данные
    """
    print("\n=== Синхронизация Deposits ===")
    
    user_id = exchange.get_user_id(api_key, api_secret)
    cached_data = load_cached_data(user_id, "deposits")
    
    now = datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    
    if full_reload or not cached_data:
        # Полная загрузка (для депозитов ограничение меньше)
        print("Полная загрузка депозитов...")
        start_time = now - timedelta(days=365)  # 1 год для депозитов
        start_ms = int(start_time.timestamp() * 1000)
        
        new_data = exchange.get_all_deposits(
            api_key, api_secret,
            coin=coin,
            start_time=start_ms,
            end_time=now_ms
        )
        
        merged_data = new_data
    else:
        # Инкрементальная загрузка
        newest_ts = get_newest_timestamp(cached_data, "successAt")
        
        if newest_ts:
            start_ms = newest_ts + 1
            print(f"Инкрементальная загрузка с {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)}")
        else:
            start_time = now - timedelta(days=365)
            start_ms = int(start_time.timestamp() * 1000)
        
        new_data = exchange.get_all_deposits(
            api_key, api_secret,
            coin=coin,
            start_time=start_ms,
            end_time=now_ms
        )
        
        # Для депозитов используем txID как id
        merged_data = merge_and_dedupe(cached_data, new_data, "txID")
    
    # Сортируем по времени
    merged_data.sort(key=lambda x: int(x.get("successAt", 0) or 0))
    
    save_cached_data(user_id, "deposits", merged_data)
    update_sync_time(user_id, "deposits")
    
    print(f"Всего депозитов после синхронизации: {len(merged_data)}")
    return merged_data


def sync_withdrawals(api_key, api_secret, coin=None, full_reload=False):
    """Синхронизировать выводы
    
    Args:
        api_key: API ключ
        api_secret: API секрет
        coin: Монета для фильтрации
        full_reload: Если True - полная перезагрузка
    
    Returns:
        list: Синхронизированные данные
    """
    print("\n=== Синхронизация Withdrawals ===")
    
    user_id = exchange.get_user_id(api_key, api_secret)
    cached_data = load_cached_data(user_id, "withdrawals")
    
    now = datetime.now(timezone.utc)
    now_ms = int(now.timestamp() * 1000)
    
    if full_reload or not cached_data:
        print("Полная загрузка выводов...")
        start_time = now - timedelta(days=365)
        start_ms = int(start_time.timestamp() * 1000)
        
        new_data = exchange.get_all_withdraws(
            api_key, api_secret,
            coin=coin,
            start_time=start_ms,
            end_time=now_ms
        )
        
        merged_data = new_data
    else:
        newest_ts = get_newest_timestamp(cached_data, "updateTime")
        
        if newest_ts:
            start_ms = newest_ts + 1
            print(f"Инкрементальная загрузка с {datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)}")
        else:
            start_time = now - timedelta(days=365)
            start_ms = int(start_time.timestamp() * 1000)
        
        new_data = exchange.get_all_withdraws(
            api_key, api_secret,
            coin=coin,
            start_time=start_ms,
            end_time=now_ms
        )
        
        merged_data = merge_and_dedupe(cached_data, new_data, "withdrawId")
    
    merged_data.sort(key=lambda x: int(x.get("updateTime", 0) or 0))
    
    save_cached_data(user_id, "withdrawals", merged_data)
    update_sync_time(user_id, "withdrawals")
    
    print(f"Всего выводов после синхронизации: {len(merged_data)}")
    return merged_data


def sync_all_data(api_key, api_secret, currency="USDT", full_reload=False):
    """Синхронизировать все данные
    
    Args:
        api_key: API ключ
        api_secret: API секрет
        currency: Валюта для transaction logs
        full_reload: Если True - полная перезагрузка всех данных
    
    Returns:
        dict: Словарь со всеми синхронизированными данными
    """
    print("\n" + "=" * 60)
    print("ПОЛНАЯ СИНХРОНИЗАЦИЯ ДАННЫХ")
    print("=" * 60)
    
    transaction_logs = sync_transaction_logs(api_key, api_secret, currency, full_reload)
    deposits = sync_deposits(api_key, api_secret, full_reload=full_reload)
    withdrawals = sync_withdrawals(api_key, api_secret, full_reload=full_reload)
    
    print("\n" + "=" * 60)
    print("СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА")
    print(f"Transaction Logs: {len(transaction_logs)}")
    print(f"Deposits: {len(deposits)}")
    print(f"Withdrawals: {len(withdrawals)}")
    print("=" * 60)
    
    return {
        "transaction_logs": transaction_logs,
        "deposits": deposits,
        "withdrawals": withdrawals
    }


# ============================================================================
# Функции анализа данных
# ============================================================================

def filter_data_by_period(data, start_time, end_time, time_field="transactionTime"):
    """Фильтровать данные по временному периоду
    
    Args:
        data: Список данных
        start_time: Начало периода (datetime или timestamp в мс)
        end_time: Конец периода (datetime или timestamp в мс)
        time_field: Название поля с временем
    
    Returns:
        list: Отфильтрованные данные
    """
    if isinstance(start_time, datetime):
        start_ms = int(start_time.timestamp() * 1000)
    else:
        start_ms = start_time
    
    if isinstance(end_time, datetime):
        end_ms = int(end_time.timestamp() * 1000)
    else:
        end_ms = end_time
    
    filtered = []
    for item in data:
        ts = int(item.get(time_field, 0) or 0)
        if start_ms <= ts <= end_ms:
            filtered.append(item)
    
    return filtered


def calculate_trading_metrics(transaction_logs):
    """Рассчитать метрики торговли из логов транзакций
    
    Args:
        transaction_logs: Список логов транзакций
    
    Returns:
        dict: Метрики торговли
    """
    metrics = {
        "trading_pnl": 0.0,       # Реализованный PnL (cashFlow от торговли)
        "trading_fees": 0.0,      # Торговые комиссии
        "funding_fees": 0.0,      # Фандинг
        "transfers_in": 0.0,      # Переводы на аккаунт
        "transfers_out": 0.0,     # Переводы с аккаунта
        "total_trades": 0,        # Количество сделок
        "by_type": defaultdict(float),  # Группировка по типам
        "by_symbol": defaultdict(lambda: {"pnl": 0.0, "fees": 0.0, "trades": 0})
    }
    
    for log in transaction_logs:
        log_type = log.get("type", "")
        symbol = log.get("symbol", "UNKNOWN")
        
        cash_flow = float(log.get("cashFlow", 0) or 0)
        fee = float(log.get("fee", 0) or 0)
        funding = float(log.get("funding", 0) or 0)
        change = float(log.get("change", 0) or 0)
        
        metrics["by_type"][log_type] += change
        
        if log_type == "TRADE":
            metrics["trading_pnl"] += cash_flow
            metrics["trading_fees"] += fee
            metrics["total_trades"] += 1
            metrics["by_symbol"][symbol]["pnl"] += cash_flow
            metrics["by_symbol"][symbol]["fees"] += fee
            metrics["by_symbol"][symbol]["trades"] += 1
            
        elif log_type == "SETTLEMENT":
            # Settlement включает funding и session settlement
            metrics["funding_fees"] += funding
            metrics["trading_pnl"] += cash_flow  # 8-hour P&L
            
        elif log_type == "TRANSFER_IN":
            metrics["transfers_in"] += abs(change)
            
        elif log_type == "TRANSFER_OUT":
            metrics["transfers_out"] += abs(change)
    
    # Чистый профит от торговли
    metrics["net_trading_profit"] = (
        metrics["trading_pnl"] + 
        metrics["funding_fees"] - 
        metrics["trading_fees"]
    )
    
    return metrics


def calculate_profitability_chart(transaction_logs, initial_balance=None):
    """Рассчитать данные для графика доходности в %
    
    Алгоритм исключает влияние депозитов и выводов на доходность.
    Доходность рассчитывается как: (trading_profit / capital_base) * 100%
    
    Args:
        transaction_logs: Список логов транзакций (отсортированных по времени)
        initial_balance: Начальный баланс (если None - определяется автоматически)
    
    Returns:
        dict: Данные для графика
    """
    if not transaction_logs:
        return {
            "timestamps": [],
            "balance": [],
            "adjusted_balance": [],
            "profitability_percent": [],
            "initial_balance": 0,
            "final_balance": 0,
            "final_adjusted_balance": 0,
            "total_profit_percent": 0
        }
    
    # Сортируем по времени
    sorted_logs = sorted(transaction_logs, key=lambda x: int(x.get("transactionTime", 0)))
    
    timestamps = []
    balance_values = []
    adjusted_balance_values = []
    profitability_percent = []
    
    # Суммарные депозиты и выводы для расчёта "капитальной базы"
    total_deposits = 0.0
    total_withdrawals = 0.0
    
    # Первый проход - считаем начальные депозиты и определяем капитальную базу
    # Капитальная база = сумма всех депозитов минус сумма всех выводов
    first_trading_balance = None
    
    for log in sorted_logs:
        log_type = log.get("type", "")
        change = float(log.get("change", 0) or 0)
        balance = float(log.get("cashBalance", 0) or 0)
        
        if log_type == "TRANSFER_IN":
            total_deposits += abs(change)
        elif log_type == "TRANSFER_OUT":
            total_withdrawals += abs(change)
        
        # Запоминаем первый баланс после торговых операций (не переводов)
        if first_trading_balance is None and log_type not in ("TRANSFER_IN", "TRANSFER_OUT"):
            # Баланс ДО этой торговой операции
            first_trading_balance = balance - change
    
    # Определяем начальный капитал для расчёта доходности
    if initial_balance is None:
        # Капитальная база = чистые вложения (депозиты - выводы)
        capital_base = total_deposits - total_withdrawals
        if capital_base <= 0:
            # Если нет депозитов или выводы больше депозитов,
            # берём первый известный баланс
            first_log = sorted_logs[0]
            first_balance = float(first_log.get("cashBalance", 0) or 0)
            first_change = float(first_log.get("change", 0) or 0)
            capital_base = first_balance - first_change
            if capital_base <= 0:
                capital_base = first_balance if first_balance > 0 else 1.0
        initial_balance = capital_base
    
    # Накопленные переводы для корректировки текущего баланса
    cumulative_deposits = 0.0
    cumulative_withdrawals = 0.0
    
    for log in sorted_logs:
        ts = int(log.get("transactionTime", 0))
        balance = float(log.get("cashBalance", 0) or 0)
        change = float(log.get("change", 0) or 0)
        log_type = log.get("type", "")
        
        # Накапливаем переводы
        if log_type == "TRANSFER_IN":
            cumulative_deposits += abs(change)
        elif log_type == "TRANSFER_OUT":
            cumulative_withdrawals += abs(change)
        
        # Скорректированный баланс = текущий баланс - депозиты + выводы
        # Это показывает сколько бы было на счёте если бы не было переводов
        adjusted_balance = balance - cumulative_deposits + cumulative_withdrawals
        
        # Прибыль/убыток от торговли = adjusted_balance (он может быть отрицательным)
        # Доходность = прибыль / начальный капитал * 100
        # Но лучше считать относительно капитальной базы
        
        # Альтернативный расчёт:
        # trading_pnl = текущий баланс - (депозиты - выводы) = balance - capital_base
        # profitability = trading_pnl / capital_base * 100
        
        trading_pnl = balance - (cumulative_deposits - cumulative_withdrawals)
        
        if initial_balance > 0:
            profit_pct = (trading_pnl / initial_balance) * 100
        else:
            profit_pct = 0.0
        
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        
        timestamps.append(dt)
        balance_values.append(balance)
        adjusted_balance_values.append(adjusted_balance)
        profitability_percent.append(profit_pct)
    
    return {
        "timestamps": timestamps,
        "balance": balance_values,
        "adjusted_balance": adjusted_balance_values,
        "profitability_percent": profitability_percent,
        "initial_balance": initial_balance,
        "capital_base": initial_balance,
        "total_deposits": total_deposits,
        "total_withdrawals": total_withdrawals,
        "final_balance": balance_values[-1] if balance_values else 0,
        "final_adjusted_balance": adjusted_balance_values[-1] if adjusted_balance_values else 0,
        "total_profit_percent": profitability_percent[-1] if profitability_percent else 0,
        "transaction_logs": sorted_logs  # Добавляем исходные логи для детализации
    }


def analyze_trading_performance(api_key, api_secret, 
                                start_time=None, end_time=None,
                                currency="USDT",
                                force_sync=False,
                                full_reload=False):
    """Анализировать результаты торгов
    
    Args:
        api_key: API ключ
        api_secret: API секрет
        start_time: Начало периода анализа (datetime или None для всех данных)
        end_time: Конец периода анализа (datetime или None для текущего момента)
        currency: Валюта для анализа
        force_sync: Принудительная синхронизация перед анализом
        full_reload: Полная перезагрузка данных
    
    Returns:
        dict: Результаты анализа с данными для графика
    """
    print("\n" + "=" * 60)
    print("АНАЛИЗ РЕЗУЛЬТАТОВ ТОРГОВ")
    print("=" * 60)
    
    user_id = exchange.get_user_id(api_key, api_secret)
    
    # Синхронизация данных если нужно
    if force_sync or full_reload:
        sync_all_data(api_key, api_secret, currency, full_reload)
    else:
        # Проверяем актуальность кэша
        last_sync = get_last_sync_time(user_id, "transaction_logs")
        if last_sync is None:
            print("Кэш пуст, выполняем синхронизацию...")
            sync_all_data(api_key, api_secret, currency, full_reload=True)
        else:
            # Если прошло больше часа - обновляем
            hours_since_sync = (datetime.now(timezone.utc) - last_sync).total_seconds() / 3600
            if hours_since_sync > 1:
                print(f"Кэш устарел ({hours_since_sync:.1f} часов), обновляем...")
                sync_all_data(api_key, api_secret, currency, full_reload=False)
    
    # Загружаем данные из кэша
    transaction_logs = load_cached_data(user_id, "transaction_logs")
    deposits = load_cached_data(user_id, "deposits")
    withdrawals = load_cached_data(user_id, "withdrawals")
    
    # Фильтруем по периоду если указан
    if start_time or end_time:
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(days=MAX_HISTORY_DAYS)
        
        transaction_logs = filter_data_by_period(
            transaction_logs, start_time, end_time, "transactionTime"
        )
        deposits = filter_data_by_period(
            deposits, start_time, end_time, "successAt"
        )
        withdrawals = filter_data_by_period(
            withdrawals, start_time, end_time, "updateTime"
        )
        
        period_start = start_time
        period_end = end_time
    else:
        # Определяем период по данным
        oldest = get_oldest_timestamp(transaction_logs, "transactionTime")
        newest = get_newest_timestamp(transaction_logs, "transactionTime")
        
        period_start = datetime.fromtimestamp(oldest / 1000, tz=timezone.utc) if oldest else None
        period_end = datetime.fromtimestamp(newest / 1000, tz=timezone.utc) if newest else None
    
    # Рассчитываем метрики
    metrics = calculate_trading_metrics(transaction_logs)
    
    # Суммируем депозиты и выводы из отдельных эндпоинтов
    total_deposits = sum(float(d.get("amount", 0) or 0) for d in deposits)
    total_withdrawals = sum(float(w.get("amount", 0) or 0) for w in withdrawals)
    
    # Данные для графика доходности
    profitability_data = calculate_profitability_chart(transaction_logs)
    
    # Получаем текущий баланс и unrealized PnL
    current_balance = 0.0
    unrealized_pnl = 0.0
    total_equity = 0.0
    total_margin_balance = 0.0
    
    try:
        wallet_balance = exchange.get_wallet_balance(api_key, api_secret, account_type="UNIFIED")
        if wallet_balance and wallet_balance.get("list"):
            for account in wallet_balance.get("list", []):
                # Общие показатели аккаунта
                total_equity = float(account.get("totalEquity", 0) or 0)
                total_margin_balance = float(account.get("totalMarginBalance", 0) or 0)
                unrealized_pnl = float(account.get("totalPerpUPL", 0) or 0)
                
                # Баланс по конкретной валюте
                for coin_data in account.get("coin", []):
                    if coin_data.get("coin") == currency:
                        current_balance = float(coin_data.get("walletBalance", 0) or 0)
                        break
    except Exception as e:
        print(f"Ошибка получения баланса: {e}")
        current_balance = profitability_data.get("final_balance", 0)
    
    # Добавляем текущую точку на график (с учётом unrealized PnL)
    # Эффективный баланс = текущий баланс + unrealized PnL
    effective_balance = current_balance + unrealized_pnl
    
    # Рассчитываем текущую доходность с учётом unrealized PnL
    # Используем ту же формулу что и для линии доходности:
    # trading_pnl = balance - (cumulative_deposits - cumulative_withdrawals)
    # profit_pct = (trading_pnl / initial_balance) * 100
    
    total_deposits = profitability_data.get("total_deposits", 0)
    total_withdrawals = profitability_data.get("total_withdrawals", 0)
    initial_balance = profitability_data.get("initial_balance", 0)
    
    if initial_balance > 0:
        # Trading PnL с учётом нереализованного - та же формула что в calculate_profitability_chart
        current_trading_pnl = effective_balance - (total_deposits - total_withdrawals)
        current_profit_percent_with_unrealized = (current_trading_pnl / initial_balance) * 100
    else:
        current_profit_percent_with_unrealized = 0.0
    
    # Добавляем текущую точку в данные графика
    profitability_data["current_timestamp"] = datetime.now(timezone.utc)
    profitability_data["current_balance"] = current_balance
    profitability_data["effective_balance"] = effective_balance
    profitability_data["unrealized_pnl"] = unrealized_pnl
    profitability_data["current_profit_percent_with_unrealized"] = current_profit_percent_with_unrealized
    
    result = {
        "period": {
            "start": period_start.isoformat() if period_start else None,
            "end": period_end.isoformat() if period_end else None
        },
        "currency": currency,
        "current_balance": current_balance,
        "initial_balance": profitability_data.get("initial_balance", 0),
        
        # Текущее состояние маржи
        "unrealized_pnl": unrealized_pnl,
        "effective_balance": effective_balance,
        "total_equity": total_equity,
        "total_margin_balance": total_margin_balance,
        "current_profit_percent_with_unrealized": current_profit_percent_with_unrealized,
        
        # Метрики торговли
        "trading_pnl": metrics["trading_pnl"],
        "trading_fees": metrics["trading_fees"],
        "funding_fees": metrics["funding_fees"],
        "net_trading_profit": metrics["net_trading_profit"],
        "total_trades": metrics["total_trades"],
        
        # Переводы (из transaction logs)
        "transfers_in": metrics["transfers_in"],
        "transfers_out": metrics["transfers_out"],
        
        # Депозиты/выводы (из отдельных эндпоинтов)
        "deposits": total_deposits,
        "withdrawals": total_withdrawals,
        "deposits_count": len(deposits),
        "withdrawals_count": len(withdrawals),
        "deposits_detail": deposits,
        "withdrawals_detail": withdrawals,
        
        # Доходность
        "total_profit_percent": profitability_data.get("total_profit_percent", 0),
        
        # Разбивка по типам транзакций
        "by_type": dict(metrics["by_type"]),
        
        # Разбивка по символам
        "by_symbol": {k: dict(v) for k, v in metrics["by_symbol"].items()},
        
        # Данные для графика
        "profitability_chart": profitability_data
    }
    
    # Вывод результатов
    print("\n" + "-" * 40)
    print("РЕЗУЛЬТАТЫ АНАЛИЗА")
    print("-" * 40)
    print(f"Период: {result['period']['start']} - {result['period']['end']}")
    print(f"Валюта: {currency}")
    print(f"Текущий баланс: {current_balance:.4f}")
    print(f"Unrealized PnL: {unrealized_pnl:.4f}")
    print(f"Эффективный баланс: {effective_balance:.4f}")
    print(f"Начальный баланс: {result['initial_balance']:.4f}")
    print()
    print(f"Реализованный PnL: {metrics['trading_pnl']:.4f}")
    print(f"Торговые комиссии: {metrics['trading_fees']:.4f}")
    print(f"Фандинг: {metrics['funding_fees']:.4f}")
    print(f"Чистый профит: {metrics['net_trading_profit']:.4f}")
    print(f"Всего сделок: {metrics['total_trades']}")
    print()
    print(f"Депозиты: {total_deposits:.4f} ({len(deposits)} шт)")
    print(f"Выводы: {total_withdrawals:.4f} ({len(withdrawals)} шт)")
    print()
    print(f"ДОХОДНОСТЬ (реализованная): {result['total_profit_percent']:.2f}%")
    print(f"ДОХОДНОСТЬ (с unrealized): {current_profit_percent_with_unrealized:.2f}%")
    print("-" * 40)
    
    return result
