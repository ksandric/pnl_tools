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
                x=1.02
            )
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
                x=0.01
            )
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
                x=1.02
            )
        )
    else:
        # Только график доходности
        fig = go.Figure()
        
        # Определяем цвет заливки в зависимости от текущей доходности
        final_profit = profitability_pct[-1] if profitability_pct else 0
        if final_profit >= 0:
            line_color = '#2E7D32'  # Зеленый
            fill_color = 'rgba(46, 125, 50, 0.2)'
        else:
            line_color = '#C62828'  # Красный
            fill_color = 'rgba(198, 40, 40, 0.2)'
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=profitability_pct,
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
        
        # Аннотация с итоговой доходностью
        initial_balance = profitability_data.get('initial_balance', 0)
        final_balance = profitability_data.get('final_adjusted_balance', 0)
        
        fig.add_annotation(
            x=timestamps[-1] if timestamps else None,
            y=final_profit,
            text=f"<b>{final_profit:+.2f}%</b>",
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
            height=500,
            xaxis_title="Время (UTC)",
            yaxis_title="Доходность (%)",
            hovermode='x unified',
            template='simple_white',
            title=dict(
                text=f"График доходности | Начальный баланс: {initial_balance:.2f}",
                font=dict(size=14)
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
    
    initial_balance = profitability_data.get('initial_balance', 0)
    
    # Линия начального баланса
    fig.add_hline(
        y=initial_balance, 
        line_dash="dot", 
        line_color="green",
        annotation_text=f"Начальный: {initial_balance:.2f}",
        annotation_position="bottom right"
    )
    
    fig.update_layout(
        height=500,
        xaxis_title="Время (UTC)",
        yaxis_title="Баланс",
        hovermode='x unified',
        template='simple_white',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        title=dict(
            text="Динамика баланса",
            font=dict(size=14)
        )
    )

    return fig