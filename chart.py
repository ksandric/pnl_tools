def create_plotly_chart(plotly_data, chart_type='pnl'):
    """
    Создает график plotly из подготовленных данных

    Args:
        plotly_data: данные из prepare_data_for_plotly()
        chart_type: тип графика - 'pnl', 'fees', 'volume' или 'all'

    Returns:
        plotly. graph_objects.Figure
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        print("Установите plotly: pip install plotly")
        return None

    if not plotly_data:
        print("Нет данных для построения графика")
        return None

    if chart_type == 'all':
        # Создаем графики с подграфиками
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('Накопительный PnL', 'Накопительные комиссии', 'Накопительный объем'),
            vertical_spacing=0.1,
            row_heights=[0.4, 0.3, 0.3]
        )

        for symbol, data in plotly_data.items():
            if symbol == '__ALL__':
                line_width = 3
                display_name = "ВСЕ СИМВОЛЫ"
            else:
                line_width = 2
                display_name = symbol

            # PnL
            fig.add_trace(
                go.Scatter(
                    x=data['x'],
                    y=data['pnl'],
                    mode='lines',
                    name=display_name,
                    line=dict(width=line_width),
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                  'Время: %{x}<br>' +
                                  'PnL: %{y:.4f}<br>' +
                                  '<extra></extra>',
                    showlegend=True
                ),
                row=1, col=1
            )

            # Комиссии
            fig.add_trace(
                go.Scatter(
                    x=data['x'],
                    y=data['fees'],
                    mode='lines',
                    name=display_name,
                    line=dict(width=line_width),
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                  'Время: %{x}<br>' +
                                  'Комиссии: %{y:.4f}<br>' +
                                  '<extra></extra>',
                    showlegend=False
                ),
                row=2, col=1
            )

            # Объем
            fig.add_trace(
                go.Scatter(
                    x=data['x'],
                    y=data['volume'],
                    mode='lines',
                    name=display_name,
                    line=dict(width=line_width),
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                  'Время: %{x}<br>' +
                                  'Объем: %{y:. 2f}<br>' +
                                  '<extra></extra>',
                    showlegend=False
                ),
                row=3, col=1
            )

        fig.update_xaxes(title_text="Время (UTC)", row=3, col=1)
        fig.update_yaxes(title_text="PnL", row=1, col=1)
        fig.update_yaxes(title_text="Комиссии", row=2, col=1)
        fig.update_yaxes(title_text="Объем", row=3, col=1)

        fig.update_layout(
            hovermode='x unified',
            template='simple_white',
            height=900,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=1.02,
                itemclick='toggle',
                itemdoubleclick='toggleothers'
            ),
            updatemenus=[
                dict(
                    type="buttons",
                    direction="left",
                    buttons=[
                        dict(
                            args=[{"visible": True}],
                            label="Показать все",
                            method="restyle"
                        ),
                        dict(
                            args=[{"visible": "legendonly"}],
                            label="Скрыть все",
                            method="restyle"
                        )
                    ],
                    pad={"r": 10, "t": 10},
                    showactive=False,
                    x=0.0,
                    xanchor="left",
                    y=1.15,
                    yanchor="top"
                )
            ]
        )

    else:
        # Один график для выбранной метрики
        fig = go.Figure()

        y_field = chart_type  # 'pnl', 'fees' или 'volume'

        if chart_type == 'pnl':
            y_title = "Накопительный PnL"
            y_format = ".4f"
        elif chart_type == 'fees':
            y_title = "Накопительные комиссии"
            y_format = ".4f"
        else:  # volume
            y_title = "Накопительный объем"
            y_format = ".2f"

        for symbol, data in plotly_data.items():
            if symbol == '__ALL__':
                line_width = 4
                display_name = "ВСЕ СИМВОЛЫ"
                line_dash = 'solid'
            else:
                line_width = 2
                display_name = symbol
                line_dash = 'solid'

            fig.add_trace(go.Scatter(
                x=data['x'],
                y=data[y_field],
                mode='lines+markers',
                name=display_name,
                line=dict(width=line_width, dash=line_dash),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                              'Время: %{x}<br>' +
                              f'{y_title}: %{{y:{y_format}}}<br>' +
                              '<extra></extra>'
            ))

        fig.update_layout(
            height=600,
            xaxis_title="Время (UTC)",
            yaxis_title=y_title,
            hovermode='x unified',
            template='simple_white',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                itemclick='toggle',
                itemdoubleclick='toggleothers'
            ),
            updatemenus=[
                dict(
                    type="buttons",
                    direction="left",
                    buttons=[
                        dict(
                            args=[{"visible": True}],
                            label="Показать все",
                            method="restyle"
                        ),
                        dict(
                            args=[{"visible": "legendonly"}],
                            label="Скрыть все",
                            method="restyle"
                        )
                    ],
                    pad={"r": 10, "t": 10},
                    showactive=False,
                    x=0.0,
                    xanchor="left",
                    y=1.12,
                    yanchor="top"
                )
            ]
        )

    return fig

def create_profitability_chart(profitability_data, show_balance=False):
    """
    Создает график доходности в процентах

    Args:
        profitability_data: данные из calculate_profitability_chart()
        show_balance: показывать ли также абсолютный баланс

    Returns:
        plotly.graph_objects.Figure
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        print("Установите plotly: pip install plotly")
        return None

    if not profitability_data or not profitability_data.get('timestamps'):
        print("Нет данных для построения графика")
        return None

    timestamps = profitability_data['timestamps']
    profitability_pct = profitability_data['profitability_percent']
    balance = profitability_data.get('balance', [])
    adjusted_balance = profitability_data.get('adjusted_balance', [])
    
    if show_balance and balance:
        # Создаем два графика
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Доходность (%)', 'Баланс'),
            vertical_spacing=0.12,
            row_heights=[0.6, 0.4]
        )
        
        # График доходности
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=profitability_pct,
                mode='lines',
                name='Доходность',
                line=dict(color='#2E86AB', width=2),
                fill='tozeroy',
                fillcolor='rgba(46, 134, 171, 0.2)',
                hovertemplate='<b>Доходность</b><br>' +
                              'Время: %{x}<br>' +
                              'Доходность: %{y:.2f}%<br>' +
                              '<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Линия нуля
        fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)
        
        # График баланса
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=balance,
                mode='lines',
                name='Баланс (факт)',
                line=dict(color='#A23B72', width=2),
                hovertemplate='<b>Баланс (факт)</b><br>' +
                              'Время: %{x}<br>' +
                              'Баланс: %{y:.4f}<br>' +
                              '<extra></extra>'
            ),
            row=2, col=1
        )
        
        if adjusted_balance:
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=adjusted_balance,
                    mode='lines',
                    name='Баланс (без депозитов/выводов)',
                    line=dict(color='#F18F01', width=2, dash='dot'),
                    hovertemplate='<b>Баланс (скорректированный)</b><br>' +
                                  'Время: %{x}<br>' +
                                  'Баланс: %{y:.4f}<br>' +
                                  '<extra></extra>'
                ),
                row=2, col=1
            )
        
        fig.update_xaxes(title_text="Время (UTC)", row=2, col=1)
        fig.update_yaxes(title_text="Доходность (%)", row=1, col=1)
        fig.update_yaxes(title_text="Баланс", row=2, col=1)
        
        fig.update_layout(
            height=700,
            hovermode='x unified',
            template='simple_white',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=1.02,
                itemclick='toggle',
                itemdoubleclick='toggleothers'
            ),
            updatemenus=[
                dict(
                    type="buttons",
                    direction="left",
                    buttons=[
                        dict(
                            args=[{"visible": True}],
                            label="Показать все",
                            method="restyle"
                        ),
                        dict(
                            args=[{"visible": "legendonly"}],
                            label="Скрыть все",
                            method="restyle"
                        )
                    ],
                    pad={"r": 10, "t": 10},
                    showactive=False,
                    x=0.0,
                    xanchor="left",
                    y=1.12,
                    yanchor="top"
                )
            ]
        )
    else:
        # Только график доходности
        fig = go.Figure()
        
        # Получаем данные для текущей точки с unrealized PnL
        current_timestamp = profitability_data.get('current_timestamp')
        current_profit_with_unrealized = profitability_data.get('current_profit_percent_with_unrealized')
        unrealized_pnl = profitability_data.get('unrealized_pnl', 0)
        
        # Добавляем текущую точку в данные для продолжения линии
        extended_timestamps = list(timestamps)
        extended_profitability = list(profitability_pct)
        
        if current_timestamp and current_profit_with_unrealized is not None:
            extended_timestamps.append(current_timestamp)
            extended_profitability.append(current_profit_with_unrealized)
        
        # Определяем цвет заливки в зависимости от конечной доходности (с unrealized)
        final_profit = extended_profitability[-1] if extended_profitability else 0
        if final_profit >= 0:
            line_color = '#2E7D32'  # Зеленый
            fill_color = 'rgba(46, 125, 50, 0.2)'
        else:
            line_color = '#C62828'  # Красный
            fill_color = 'rgba(198, 40, 40, 0.2)'
        
        fig.add_trace(go.Scatter(
            x=extended_timestamps,
            y=extended_profitability,
            mode='lines',
            name='Доходность',
            line=dict(color=line_color, width=2.5),
            fill='tozeroy',
            fillcolor=fill_color,
            hovertemplate='<b>Доходность</b><br>' +
                          'Время: %{x}<br>' +
                          'Доходность: %{y:.2f}%<br>' +
                          '<extra></extra>'
        ))
        
        # Линия нуля
        fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
        
        # Аннотация с итоговой доходностью на конце линии
        initial_balance = profitability_data.get('initial_balance', 0)
        
        if extended_timestamps:
            # Текст аннотации - если есть unrealized, показываем его
            if current_timestamp and current_profit_with_unrealized is not None and unrealized_pnl != 0:
                annotation_text = f"<b>{final_profit:+.2f}%</b><br><i>(unrealized: {unrealized_pnl:+.2f})</i>"
            else:
                annotation_text = f"<b>{final_profit:+.2f}%</b>"
            
            fig.add_annotation(
                x=extended_timestamps[-1],
                y=final_profit,
                text=annotation_text,
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=line_color,
                font=dict(size=14, color=line_color),
                bgcolor='white',
                bordercolor=line_color,
                borderwidth=1,
                borderpad=4
            )
        
        fig.update_layout(
            height=700,
            xaxis_title="Время (UTC)",
            yaxis_title="Доходность (%)",
            hovermode='x unified',
            template='simple_white',
            title=dict(
                text=f"График доходности: {initial_balance:.2f}",
                font=dict(size=14)
            ),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                itemclick='toggle',
                itemdoubleclick='toggleothers'
            )
        )

    return fig


def create_balance_chart(profitability_data):
    """
    Создает график баланса с разделением на фактический и скорректированный

    Args:
        profitability_data: данные из calculate_profitability_chart()

    Returns:
        plotly.graph_objects.Figure
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("Установите plotly: pip install plotly")
        return None

    if not profitability_data or not profitability_data.get('timestamps'):
        print("Нет данных для построения графика")
        return None

    timestamps = profitability_data['timestamps']
    balance = profitability_data.get('balance', [])
    adjusted_balance = profitability_data.get('adjusted_balance', [])
    
    fig = go.Figure()
    
    # Фактический баланс
    if balance:
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=balance,
            mode='lines',
            name='Баланс (фактический)',
            line=dict(color='#1976D2', width=2),
            hovertemplate='<b>Баланс (факт)</b><br>' +
                          'Время: %{x}<br>' +
                          'Баланс: %{y:.4f}<br>' +
                          '<extra></extra>'
        ))
    
    # Скорректированный баланс (без влияния депозитов/выводов)
    if adjusted_balance:
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=adjusted_balance,
            mode='lines',
            name='Баланс (без депозитов/выводов)',
            line=dict(color='#F57C00', width=2, dash='dash'),
            hovertemplate='<b>Баланс (скорректированный)</b><br>' +
                          'Время: %{x}<br>' +
                          'Баланс: %{y:.4f}<br>' +
                          '<extra></extra>'
        ))
    
    # Добавляем текущую точку с effective balance (баланс + unrealized PnL)
    current_timestamp = profitability_data.get('current_timestamp')
    current_balance = profitability_data.get('current_balance', 0)
    effective_balance = profitability_data.get('effective_balance', 0)
    unrealized_pnl = profitability_data.get('unrealized_pnl', 0)
    
    if current_timestamp and effective_balance:
        # Точка эффективного баланса (с unrealized)
        fig.add_trace(go.Scatter(
            x=[current_timestamp],
            y=[effective_balance],
            mode='markers',
            name=f'unrealized: {effective_balance:.2f}',
            marker=dict(
                color='#9C27B0',
                size=15,
                symbol='star',
                line=dict(color='white', width=2)
            ),
            hovertemplate='<b>unrealized</b><br>' +
                          'Время: %{x}<br>' +
                          f'Баланс: {effective_balance:.4f}<br>' +
                          f'Unrealized PnL: {unrealized_pnl:+.4f}<br>' +
                          '<extra></extra>'
        ))
        
        # Аннотация
        fig.add_annotation(
            x=current_timestamp,
            y=effective_balance,
            text=f"<b>⚡ {effective_balance:.2f}</b><br><i>unrealized: {unrealized_pnl:+.2f}</i>",
            showarrow=True,
            arrowhead=2,
            arrowcolor='#9C27B0',
            font=dict(size=11, color='#9C27B0'),
            bgcolor='white',
            bordercolor='#9C27B0',
            borderwidth=1,
            borderpad=3,
            ax=50,
            ay=-30
        )
    
    initial_balance = profitability_data.get('initial_balance', 0)
    
    # Линия капитальной базы
    fig.add_hline(
        y=initial_balance, 
        line_dash="dot", 
        line_color="green",
    )
    
    fig.update_layout(
        height=700,
        xaxis_title="Время (UTC)",
        yaxis_title="Баланс",
        hovermode='x unified',
        template='simple_white',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            itemclick='toggle',
            itemdoubleclick='toggleothers'
        ),
        title=dict(
            text="Динамика баланса",
            font=dict(size=14)
        ),
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                buttons=[
                    dict(
                        args=[{"visible": True}],
                        label="Показать все",
                        method="restyle"
                    ),
                    dict(
                        args=[{"visible": "legendonly"}],
                        label="Скрыть все",
                        method="restyle"
                    )
                ],
                pad={"r": 10, "t": 10},
                showactive=False,
                x=0.0,
                xanchor="left",
                y=1.12,
                yanchor="top"
            )
        ]
    )

    return fig


def create_pnl_by_symbol_chart(pnl_by_symbol_data, max_symbols=20):
    """
    Создает оптимизированный график накопительного PnL по монетам
    
    Args:
        pnl_by_symbol_data: данные из calculate_pnl_by_symbol()
        max_symbols: максимальное количество монет для отображения
    
    Returns:
        plotly.graph_objects.Figure
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("Установите plotly: pip install plotly")
        return None
    
    if not pnl_by_symbol_data or not pnl_by_symbol_data.get('data'):
        print("Нет данных для построения графика")
        return None
    
    symbols = pnl_by_symbol_data['symbols'][:max_symbols]
    data = pnl_by_symbol_data['data']
    
    fig = go.Figure()
    
    # Используем Scattergl для оптимизации (WebGL rendering)
    for symbol in symbols:
        symbol_data = data[symbol]
        
        # Определяем цвет линии (зеленый для прибыли, красный для убытка)
        final_pnl = symbol_data['pnl'][-1] if symbol_data['pnl'] else 0
        line_color = '#2E7D32' if final_pnl >= 0 else '#C62828'
        
        fig.add_trace(go.Scattergl(  # Используем Scattergl вместо Scatter
            x=symbol_data['timestamps'],
            y=symbol_data['pnl'],
            mode='lines',
            name=f"{symbol} ({final_pnl:+.2f})",
            line=dict(width=1.5),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Время: %{x}<br>' +
                          'PnL: %{y:.4f}<br>' +
                          '<extra></extra>',
            visible='legendonly' if abs(final_pnl) < 10 else True  # Скрываем мелкие по умолчанию
        ))
    
    # Линия нуля
    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
    
    fig.update_layout(
        height=600,
        xaxis_title="Время (UTC)",
        yaxis_title="Накопительный PnL",
        hovermode='closest',  # Используем closest вместо x unified для производительности
        template='simple_white',
        title=dict(
            text=f"PnL по монетам (топ-{len(symbols)})",
            font=dict(size=14)
        ),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.02,
            itemclick='toggle',
            itemdoubleclick='toggleothers',
            font=dict(size=10)  # Уменьшаем шрифт легенды
        ),
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                buttons=[
                    dict(
                        args=[{"visible": True}],
                        label="Показать все",
                        method="restyle"
                    ),
                    dict(
                        args=[{"visible": "legendonly"}],
                        label="Скрыть все",
                        method="restyle"
                    )
                ],
                pad={"r": 10, "t": 10},
                showactive=False,
                x=0.0,
                xanchor="left",
                y=1.12,
                yanchor="top"
            )
        ],
        # Оптимизация производительности
        xaxis=dict(
            autorange=True,
            rangeslider=dict(visible=False)  # Отключаем rangeslider для производительности
        )
    )
    
    return fig