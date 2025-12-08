def create_plotly_chart(plotly_data, title="Накопительный PnL по символам", chart_type='pnl'):
    """
    Создает график plotly из подготовленных данных

    Args:
        plotly_data: данные из prepare_data_for_plotly()
        title: заголовок графика
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
            title=title,
            hovermode='x unified',
            template='plotly_white',
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
            title=title,
            xaxis_title="Время (UTC)",
            yaxis_title=y_title,
            hovermode='x unified',
            template='plotly_white',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )

    return fig
