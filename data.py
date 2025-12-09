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
