from datetime import datetime, timezone
from collections import defaultdict


def prepare_data_for_plotly(data):
    """
    Преобразует данные закрытых позиций для построения графика в plotly

    Args:
        data: список словарей с данными закрытых позиций

    Returns:
        dict: данные готовые для plotly, сгруппированные по символам
    """
    if not data:
        return {}

    # Группируем данные по символам
    symbol_data = defaultdict(list)
    all_positions = []  # Для общей линии

    for position in data:
        symbol = position.get('symbol', 'UNKNOWN')
        created_time = position.get('updatedTime', '0')
        closed_pnl = position.get('closedPnl', '0')
        close_fee = position.get('closeFee', '0')
        open_fee = position.get('openFee', '0')
        cum_entry_value = position.get('cumEntryValue', '0')
        cum_exit_value = position.get('cumExitValue', '0')

        # Преобразуем время из миллисекунд в datetime
        timestamp_ms = int(created_time)
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)

        # Вычисляем метрики
        net_pnl = float(closed_pnl)
        total_fees = float(close_fee) + float(open_fee)
        total_volume = float(cum_entry_value) + float(cum_exit_value)

        position_data = {
            'time': dt,
            'pnl': net_pnl,
            'fees': total_fees,
            'volume': total_volume
        }

        symbol_data[symbol].append(position_data)
        all_positions.append(position_data)

    # Обрабатываем данные для каждого символа
    result = {}

    for symbol, positions in symbol_data.items():
        # Сортируем по времени
        positions_sorted = sorted(positions, key=lambda x: x['time'])

        # Вычисляем накопительные итоги
        cumulative_pnl = 0
        cumulative_fees = 0
        cumulative_volume = 0

        x_values = []
        y_pnl = []
        y_fees = []
        y_volume = []

        for pos in positions_sorted:
            cumulative_pnl += pos['pnl']
            cumulative_fees += pos['fees']
            cumulative_volume += pos['volume']

            x_values.append(pos['time'])
            y_pnl.append(cumulative_pnl)
            y_fees.append(cumulative_fees)
            y_volume.append(cumulative_volume)

        result[symbol] = {
            'x': x_values,
            'pnl': y_pnl,
            'fees': y_fees,
            'volume': y_volume
        }

    # Добавляем общую линию по всем символам
    if all_positions:
        all_positions_sorted = sorted(all_positions, key=lambda x: x['time'])

        cumulative_pnl = 0
        cumulative_fees = 0
        cumulative_volume = 0

        x_values = []
        y_pnl = []
        y_fees = []
        y_volume = []

        for pos in all_positions_sorted:
            cumulative_pnl += pos['pnl']
            cumulative_fees += pos['fees']
            cumulative_volume += pos['volume']

            x_values.append(pos['time'])
            y_pnl.append(cumulative_pnl)
            y_fees.append(cumulative_fees)
            y_volume.append(cumulative_volume)

        result['__ALL__'] = {
            'x': x_values,
            'pnl': y_pnl,
            'fees': y_fees,
            'volume': y_volume
        }

    return result


def data_summary(plotly_data):
    """
    Возвращает статистику по подготовленным данным в структурированном формате
    
    Returns:
        dict: Словарь с общей информацией и данными по каждому символу
    """
    if not plotly_data:
        return {
            'total_symbols': 0,
            'symbols': []
        }

    symbols_data = []
    
    for symbol, data in plotly_data.items():
        if symbol == '__ALL__':
            display_name = "ВСЕ СИМВОЛЫ (ИТОГО)"
            is_total = True
        else:
            display_name = symbol
            is_total = False

        total_trades = len(data['x'])
        final_pnl = data['pnl'][-1] if data['pnl'] else 0
        total_fees = data['fees'][-1] if data['fees'] else 0
        total_volume = data['volume'][-1] if data['volume'] else 0
        first_trade = data['x'][0] if data['x'] else None
        last_trade = data['x'][-1] if data['x'] else None

        symbols_data.append({
            'symbol': symbol,
            'display_name': display_name,
            'is_total': is_total,
            'total_trades': total_trades,
            'final_pnl': final_pnl,
            'total_fees': total_fees,
            'total_volume': total_volume,
            'first_trade': first_trade,
            'last_trade': last_trade
        })

    return {
        'total_symbols': len([s for s in plotly_data.keys() if s != '__ALL__']),
        'symbols': symbols_data
    }


def get_data_summary_html(plotly_data):
    """Возвращает HTML с краткой статистикой по подготовленным данным в виде таблицы"""
    summary = data_summary(plotly_data)
    
    if summary['total_symbols'] == 0:
        return "<p>Нет данных для отображения</p>"

    html_parts = []
    html_parts.append(f"<h3>Всего символов: {summary['total_symbols']}</h3>")
    
    # Создаем таблицу в стиле Windows 95
    html_parts.append('''
    <table style="width: 100%; border-collapse: collapse; border: 2px solid; border-color: #808080 #ffffff #ffffff #808080; background-color: #ffffff; font-size: 11px;">
        <thead>
            <tr style="background-color: #000080; color: white;">
                <th style="padding: 5px; border: 1px solid #808080; text-align: left;">Symbol</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Trades</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">PnL</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Fees</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Volume</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: left;">First Trade</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: left;">Last Trade</th>
            </tr>
        </thead>
        <tbody>
    ''')
    
    # Сортируем: сначала обычные символы, потом итог
    regular_symbols = [s for s in summary['symbols'] if not s['is_total']]
    total_symbols = [s for s in summary['symbols'] if s['is_total']]
    
    for symbol_data in regular_symbols + total_symbols:
        if symbol_data['is_total']:
            row_style = "background-color: #c0c0c0; font-weight: bold;"
        else:
            row_style = "background-color: #ffffff;"
        
        pnl_color = "green" if symbol_data['final_pnl'] > 0 else "red" if symbol_data['final_pnl'] < 0 else "black"
        
        first_trade_str = str(symbol_data['first_trade']) if symbol_data['first_trade'] else '-'
        last_trade_str = str(symbol_data['last_trade']) if symbol_data['last_trade'] else '-'
        
        html_parts.append(f'''
            <tr style="{row_style}">
                <td style="padding: 5px; border: 1px solid #808080;">{symbol_data["display_name"]}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right;">{symbol_data["total_trades"]}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right; color: {pnl_color}; font-weight: bold;">{symbol_data["final_pnl"]:.4f}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right;">{symbol_data["total_fees"]:.4f}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right;">{symbol_data["total_volume"]:.2f}</td>
                <td style="padding: 5px; border: 1px solid #808080; font-size: 10px;">{first_trade_str}</td>
                <td style="padding: 5px; border: 1px solid #808080; font-size: 10px;">{last_trade_str}</td>
            </tr>
        ''')
    
    html_parts.append('''
        </tbody>
    </table>
    ''')

    return ''.join(html_parts)


def prepare_executions_for_table(data):
    """
    Преобразует данные исполненных сделок (/v5/execution/list) для отображения в таблице

    Args:
        data: список словарей с данными исполненных сделок

    Returns:
        dict: данные готовые для таблицы, сгруппированные по символам
    """
    if not data:
        return {}

    # Группируем данные по символам
    symbol_data = defaultdict(lambda: {
        'executions': [],
        'total_qty': 0,
        'total_value': 0,
        'total_fee': 0,
        'buy_count': 0,
        'sell_count': 0,
        'buy_qty': 0,
        'sell_qty': 0
    })

    for execution in data:
        symbol = execution.get('symbol', 'UNKNOWN')
        exec_time = execution.get('execTime', '0')
        exec_type = execution.get('execType', 'Unknown')
        side = execution.get('side', 'Unknown')
        exec_qty = execution.get('execQty', '0')
        exec_price = execution.get('execPrice', '0')
        exec_value = execution.get('execValue', '0')
        exec_fee = execution.get('execFee', '0')
        order_id = execution.get('orderId', '')
        exec_id = execution.get('execId', '')
        fee_rate = execution.get('feeRate', '0')
        is_maker = execution.get('isMaker', False)

        # Преобразуем время из миллисекунд в datetime
        timestamp_ms = int(exec_time)
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)

        qty = float(exec_qty)
        value = float(exec_value)
        fee = float(exec_fee)
        price = float(exec_price)

        execution_record = {
            'time': dt,
            'exec_id': exec_id,
            'order_id': order_id,
            'side': side,
            'exec_type': exec_type,
            'qty': qty,
            'price': price,
            'value': value,
            'fee': fee,
            'fee_rate': float(fee_rate),
            'is_maker': is_maker
        }

        symbol_data[symbol]['executions'].append(execution_record)
        symbol_data[symbol]['total_qty'] += qty
        symbol_data[symbol]['total_value'] += value
        symbol_data[symbol]['total_fee'] += fee

        if side.lower() == 'buy':
            symbol_data[symbol]['buy_count'] += 1
            symbol_data[symbol]['buy_qty'] += qty
        elif side.lower() == 'sell':
            symbol_data[symbol]['sell_count'] += 1
            symbol_data[symbol]['sell_qty'] += qty

    # Сортируем исполнения по времени для каждого символа
    for symbol in symbol_data:
        symbol_data[symbol]['executions'].sort(key=lambda x: x['time'])

    return dict(symbol_data)


def executions_summary(executions_data):
    """
    Возвращает статистику по исполненным сделкам в структурированном формате

    Args:
        executions_data: результат prepare_executions_for_table

    Returns:
        dict: Словарь с общей информацией и данными по каждому символу
    """
    if not executions_data:
        return {
            'total_symbols': 0,
            'total_executions': 0,
            'symbols': []
        }

    symbols_stats = []
    total_executions = 0
    total_value = 0
    total_fee = 0
    total_buy = 0
    total_sell = 0

    for symbol, data in executions_data.items():
        executions_list = data['executions']
        total_trades = len(executions_list)
        total_executions += total_trades

        first_exec = executions_list[0] if executions_list else None
        last_exec = executions_list[-1] if executions_list else None

        avg_price = (data['total_value'] / data['total_qty']) if data['total_qty'] > 0 else 0

        symbols_stats.append({
            'symbol': symbol,
            'total_executions': total_trades,
            'buy_count': data['buy_count'],
            'sell_count': data['sell_count'],
            'buy_qty': data['buy_qty'],
            'sell_qty': data['sell_qty'],
            'total_qty': data['total_qty'],
            'total_value': data['total_value'],
            'total_fee': data['total_fee'],
            'avg_price': avg_price,
            'first_exec_time': first_exec['time'] if first_exec else None,
            'last_exec_time': last_exec['time'] if last_exec else None
        })

        total_value += data['total_value']
        total_fee += data['total_fee']
        total_buy += data['buy_count']
        total_sell += data['sell_count']

    # Сортируем по объему торговли (убывание)
    symbols_stats.sort(key=lambda x: x['total_value'], reverse=True)

    return {
        'total_symbols': len(executions_data),
        'total_executions': total_executions,
        'total_value': total_value,
        'total_fee': total_fee,
        'total_buy': total_buy,
        'total_sell': total_sell,
        'symbols': symbols_stats
    }


def get_executions_summary_html(executions_data):
    """
    Возвращает HTML с краткой статистикой по исполненным сделкам в виде таблицы

    Args:
        executions_data: результат prepare_executions_for_table

    Returns:
        str: HTML-строка с таблицей статистики
    """
    summary = executions_summary(executions_data)

    if summary['total_symbols'] == 0:
        return "<p>Нет данных для отображения</p>"

    html_parts = []
    html_parts.append(f"<h3>Всего символов: {summary['total_symbols']} | Всего сделок: {summary['total_executions']}</h3>")
    html_parts.append(f"<p style='font-size: 11px;'>Покупки: {summary['total_buy']} | Продажи: {summary['total_sell']} | Общая комиссия: {summary['total_fee']:.4f} USDT</p>")

    # Создаем таблицу в стиле Windows 95
    html_parts.append('''
    <table style="width: 100%; border-collapse: collapse; border: 2px solid; border-color: #808080 #ffffff #ffffff #808080; background-color: #ffffff; font-size: 11px;">
        <thead>
            <tr style="background-color: #000080; color: white;">
                <th style="padding: 5px; border: 1px solid #808080; text-align: left;">Symbol</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Executions</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Buy/Sell</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Total Qty</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Avg Price</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Total Value</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Total Fee</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: left;">First / Last Exec</th>
            </tr>
        </thead>
        <tbody>
    ''')

    for symbol_data in summary['symbols']:
        buy_sell_ratio = f"{symbol_data['buy_count']}/{symbol_data['sell_count']}"
        first_time = str(symbol_data['first_exec_time']) if symbol_data['first_exec_time'] else '-'
        last_time = str(symbol_data['last_exec_time']) if symbol_data['last_exec_time'] else '-'

        html_parts.append(f'''
            <tr style="background-color: #ffffff;">
                <td style="padding: 5px; border: 1px solid #808080; font-weight: bold;">{symbol_data["symbol"]}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right;">{symbol_data["total_executions"]}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right;">{buy_sell_ratio}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right;">{symbol_data["total_qty"]:.4f}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right;">{symbol_data["avg_price"]:.4f}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right;">{symbol_data["total_value"]:.2f}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right;">{symbol_data["total_fee"]:.4f}</td>
                <td style="padding: 5px; border: 1px solid #808080; font-size: 10px;">{first_time[:19]} / {last_time[:19]}</td>
            </tr>
        ''')

    html_parts.append('''
        </tbody>
    </table>
    ''')

    return ''.join(html_parts)


def prepare_transfers_for_table(inter_transfers=None, universal_transfers=None, deposits=None, withdraws=None):
    """
    Преобразует данные переводов, депозитов и выводов для отображения в таблице
    Объединяет данные из:
    - /v5/asset/transfer/query-inter-transfer-list (внутренние переводы)
    - /v5/asset/transfer/query-universal-transfer-list (универсальные переводы)
    - /v5/asset/deposit/query-record (депозиты)
    - /v5/asset/withdraw/query-record (выводы)

    Args:
        inter_transfers: список внутренних переводов
        universal_transfers: список универсальных переводов
        deposits: список депозитов
        withdraws: список выводов

    Returns:
        dict: данные готовые для таблицы, сгруппированные по монетам
    """
    # Группируем данные по монетам (coin)
    coin_data = defaultdict(lambda: {
        'inter_transfers': [],
        'universal_transfers': [],
        'deposits': [],
        'withdraws': [],
        'total_inter_amount': 0,
        'total_universal_amount': 0,
        'total_deposit_amount': 0,
        'total_withdraw_amount': 0,
        'inter_count': 0,
        'universal_count': 0,
        'deposit_count': 0,
        'withdraw_count': 0
    })

    # Обрабатываем внутренние переводы
    if inter_transfers:
        for transfer in inter_transfers:
            coin = transfer.get('coin', 'UNKNOWN')
            timestamp = transfer.get('timestamp', '0')
            amount = transfer.get('amount', '0')
            from_account = transfer.get('fromAccountType', '')
            to_account = transfer.get('toAccountType', '')
            transfer_id = transfer.get('transferId', '')
            status = transfer.get('status', '')

            dt = datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.utc)
            amt = float(amount)

            record = {
                'time': dt,
                'transfer_id': transfer_id,
                'from': from_account,
                'to': to_account,
                'amount': amt,
                'status': status,
                'type': 'inter'
            }

            coin_data[coin]['inter_transfers'].append(record)
            coin_data[coin]['total_inter_amount'] += amt
            coin_data[coin]['inter_count'] += 1

    # Обрабатываем универсальные переводы
    if universal_transfers:
        for transfer in universal_transfers:
            coin = transfer.get('coin', 'UNKNOWN')
            timestamp = transfer.get('timestamp', '0')
            amount = transfer.get('amount', '0')
            from_member = transfer.get('fromMemberId', '')
            to_member = transfer.get('toMemberId', '')
            transfer_id = transfer.get('transferId', '')
            status = transfer.get('status', '')

            dt = datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.utc)
            amt = float(amount)

            record = {
                'time': dt,
                'transfer_id': transfer_id,
                'from': from_member,
                'to': to_member,
                'amount': amt,
                'status': status,
                'type': 'universal'
            }

            coin_data[coin]['universal_transfers'].append(record)
            coin_data[coin]['total_universal_amount'] += amt
            coin_data[coin]['universal_count'] += 1

    # Обрабатываем депозиты
    if deposits:
        for deposit in deposits:
            coin = deposit.get('coin', 'UNKNOWN')
            success_at = deposit.get('successAt', '0')
            amount = deposit.get('amount', '0')
            tx_id = deposit.get('txID', '')
            status = deposit.get('status', '')
            chain = deposit.get('chain', '')

            dt = datetime.fromtimestamp(int(success_at) / 1000, tz=timezone.utc) if success_at != '0' else None
            amt = float(amount)

            record = {
                'time': dt,
                'tx_id': tx_id,
                'chain': chain,
                'amount': amt,
                'status': status,
                'type': 'deposit'
            }

            coin_data[coin]['deposits'].append(record)
            coin_data[coin]['total_deposit_amount'] += amt
            coin_data[coin]['deposit_count'] += 1

    # Обрабатываем выводы
    if withdraws:
        for withdraw in withdraws:
            coin = withdraw.get('coin', 'UNKNOWN')
            create_time = withdraw.get('createTime', '0')
            amount = withdraw.get('amount', '0')
            withdraw_id = withdraw.get('withdrawId', '')
            status = withdraw.get('status', '')
            chain = withdraw.get('chain', '')

            dt = datetime.fromtimestamp(int(create_time) / 1000, tz=timezone.utc) if create_time != '0' else None
            amt = float(amount)

            record = {
                'time': dt,
                'withdraw_id': withdraw_id,
                'chain': chain,
                'amount': amt,
                'status': status,
                'type': 'withdraw'
            }

            coin_data[coin]['withdraws'].append(record)
            coin_data[coin]['total_withdraw_amount'] += amt
            coin_data[coin]['withdraw_count'] += 1

    # Сортируем записи по времени для каждой монеты
    for coin in coin_data:
        for key in ['inter_transfers', 'universal_transfers', 'deposits', 'withdraws']:
            coin_data[coin][key].sort(key=lambda x: x['time'] if x['time'] else datetime.min.replace(tzinfo=timezone.utc))

    return dict(coin_data)


def transfers_summary(transfers_data):
    """
    Возвращает статистику по переводам, депозитам и выводам в структурированном формате

    Args:
        transfers_data: результат prepare_transfers_for_table

    Returns:
        dict: Словарь с общей информацией и данными по каждой монете
    """
    if not transfers_data:
        return {
            'total_coins': 0,
            'total_operations': 0,
            'coins': []
        }

    coins_stats = []
    total_operations = 0

    for coin, data in transfers_data.items():
        total_ops = (data['inter_count'] + data['universal_count'] + 
                     data['deposit_count'] + data['withdraw_count'])
        total_operations += total_ops

        # Net flow: deposits + inter_in + universal_in - withdraws - inter_out - universal_out
        # Упрощенно: deposits - withdraws (для более точного расчета нужно анализировать направление переводов)
        net_flow = data['total_deposit_amount'] - data['total_withdraw_amount']

        # Собираем все временные метки
        all_times = []
        for transfers_list in [data['inter_transfers'], data['universal_transfers'], 
                              data['deposits'], data['withdraws']]:
            for item in transfers_list:
                if item['time']:
                    all_times.append(item['time'])

        first_time = min(all_times) if all_times else None
        last_time = max(all_times) if all_times else None

        coins_stats.append({
            'coin': coin,
            'inter_count': data['inter_count'],
            'universal_count': data['universal_count'],
            'deposit_count': data['deposit_count'],
            'withdraw_count': data['withdraw_count'],
            'total_inter_amount': data['total_inter_amount'],
            'total_universal_amount': data['total_universal_amount'],
            'total_deposit_amount': data['total_deposit_amount'],
            'total_withdraw_amount': data['total_withdraw_amount'],
            'net_flow': net_flow,
            'total_operations': total_ops,
            'first_operation': first_time,
            'last_operation': last_time
        })

    # Сортируем по общему количеству операций (убывание)
    coins_stats.sort(key=lambda x: x['total_operations'], reverse=True)

    return {
        'total_coins': len(transfers_data),
        'total_operations': total_operations,
        'coins': coins_stats
    }


def get_transfers_summary_html(transfers_data):
    """
    Возвращает HTML с краткой статистикой по переводам, депозитам и выводам в виде таблицы

    Args:
        transfers_data: результат prepare_transfers_for_table

    Returns:
        str: HTML-строка с таблицей статистики
    """
    summary = transfers_summary(transfers_data)

    if summary['total_coins'] == 0:
        return "<p>Нет данных для отображения</p>"

    html_parts = []
    html_parts.append(f"<h3>Всего монет: {summary['total_coins']} | Всего операций: {summary['total_operations']}</h3>")

    # Создаем таблицу в стиле Windows 95
    html_parts.append('''
    <table style="width: 100%; border-collapse: collapse; border: 2px solid; border-color: #808080 #ffffff #ffffff #808080; background-color: #ffffff; font-size: 11px;">
        <thead>
            <tr style="background-color: #000080; color: white;">
                <th style="padding: 5px; border: 1px solid #808080; text-align: left;">Coin</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Deposits</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Withdraws</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Inter Transfers</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Universal Transfers</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Net Flow</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: left;">First / Last Operation</th>
            </tr>
        </thead>
        <tbody>
    ''')

    for coin_stats in summary['coins']:
        deposits_str = f"{coin_stats['deposit_count']} ({coin_stats['total_deposit_amount']:.4f})"
        withdraws_str = f"{coin_stats['withdraw_count']} ({coin_stats['total_withdraw_amount']:.4f})"
        inter_str = f"{coin_stats['inter_count']} ({coin_stats['total_inter_amount']:.4f})"
        universal_str = f"{coin_stats['universal_count']} ({coin_stats['total_universal_amount']:.4f})"
        
        net_flow = coin_stats['net_flow']
        net_flow_color = "green" if net_flow > 0 else "red" if net_flow < 0 else "black"
        net_flow_str = f"{net_flow:+.4f}"

        first_time = str(coin_stats['first_operation'])[:19] if coin_stats['first_operation'] else '-'
        last_time = str(coin_stats['last_operation'])[:19] if coin_stats['last_operation'] else '-'

        html_parts.append(f'''
            <tr style="background-color: #ffffff;">
                <td style="padding: 5px; border: 1px solid #808080; font-weight: bold;">{coin_stats["coin"]}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right;">{deposits_str}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right;">{withdraws_str}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right;">{inter_str}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right;">{universal_str}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right; color: {net_flow_color}; font-weight: bold;">{net_flow_str}</td>
                <td style="padding: 5px; border: 1px solid #808080; font-size: 10px;">{first_time} / {last_time}</td>
            </tr>
        ''')

    html_parts.append('''
        </tbody>
    </table>
    ''')

    return ''.join(html_parts)
