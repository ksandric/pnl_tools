import time
import asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import httpx
import uvicorn
import exchange
import data
import data_profit
import chart
from datetime import datetime, timezone
from utils import generate_cache_key, load_from_cache, save_to_cache

# pip3 install fastapi uvicorn pydantic apscheduler requests

app = FastAPI()
last_requests = {}
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# [Unit]
# Description=Async app Service
# After=multi-user.target
# [Service]
# Type=simple
# WorkingDirectory=/opt/pnl
# ExecStart=/opt/pnl uvicorn run_app:app --host 0.0.0.0 --port 8082
# RestartSec=61
# Restart=always
# [Install]
# WantedBy=multi-user.target


@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/profit", response_class=HTMLResponse)
async def profit_page(request: Request):
    """Profit analysis page"""
    return templates.TemplateResponse("profit.html", {"request": request})


@app.post("/process", response_class=HTMLResponse)
async def process_form_loading(
    request: Request,
    api_key: str = Form(...),
    api_secret: str = Form(...),
    start_datetime: str = Form(None),
    end_datetime: str = Form(None),
    symbols: str = Form(None),
    chart_type: str = Form("pnl"),
    action: str = Form(...)
):
    """Show loading page with form data embedded"""
    return templates.TemplateResponse("loading.html", {
        "request": request,
        "api_key": api_key,
        "api_secret": api_secret,
        "start_datetime": start_datetime or "",
        "end_datetime": end_datetime or "",
        "symbols": symbols or "",
        "chart_type": chart_type,
        "action": action
    })


@app.post("/process_async", response_class=HTMLResponse)
async def process_form(
    request: Request,
    api_key: str = Form(...),
    api_secret: str = Form(...),
    start_datetime: str = Form(None),
    end_datetime: str = Form(None),
    symbols: str = Form(None),
    chart_type: str = Form("pnl"),
    action: str = Form(...)
):
    try:
        # Генерируем ключ кеша
        cache_key = generate_cache_key(api_key, action, start_datetime, end_datetime)
        
        # Проверяем кеш
        pnl_data = load_from_cache(cache_key)
        
        if pnl_data is not None:
            print(f"Используем кешированные данные для ключа: {cache_key}")
            title_prefix = "[CACHED] "
        else:
            print(f"Загружаем новые данные для ключа: {cache_key}")
            title_prefix = ""
            
            # Получаем данные в зависимости от action
            if action == "get_pnl_today":
                pnl_data = exchange.get_pnl_today(api_key, api_secret, category="linear")
                title = "Range: Today"
            elif action == "get_pnl_yesterday":
                pnl_data = exchange.get_pnl_yesterday(api_key, api_secret, category="linear")
                title = "Range: Yesterday"
            elif action == "get_pnl_current_month":
                pnl_data = exchange.get_pnl_current_month(api_key, api_secret, category="linear")
                title = "Range: Current Month"
            elif action == "get_pnl_previous_month":
                pnl_data = exchange.get_pnl_previous_month(api_key, api_secret, category="linear")
                title = "Range: Previous Month"
            elif action == "get_pnl_custom":
                # Для кастомного периода нужно преобразовать даты в миллисекунды
                if start_datetime and end_datetime:
                    start_dt = datetime.fromisoformat(start_datetime).replace(tzinfo=timezone.utc)
                    end_dt = datetime.fromisoformat(end_datetime).replace(tzinfo=timezone.utc)
                    start_ms = int(start_dt.timestamp() * 1000)
                    end_ms = int(end_dt.timestamp() * 1000)
                    pnl_data = exchange.get_all_closed_pnl(api_key, api_secret, category="linear", 
                                                           start_time=start_ms, end_time=end_ms)
                    title = f"Range: Custom Period"
                else:
                    return HTMLResponse(content="<h1>Error: Start and End datetime are required for custom range</h1>")
            else:
                return HTMLResponse(content="<h1>Error: Unknown action</h1>")
            
            # Сохраняем в кеш
            save_to_cache(cache_key, pnl_data)
        
        # Устанавливаем заголовок если не был установлен (для кеша)
        if 'title' not in locals():
            if action == "get_pnl_today":
                title = "Range: Today"
            elif action == "get_pnl_yesterday":
                title = "Range: Yesterday"
            elif action == "get_pnl_current_month":
                title = "Range: Current Month"
            elif action == "get_pnl_previous_month":
                title = "Range: Previous Month"
            elif action == "get_pnl_custom":
                title = "Range: Custom Period"
        
        title = title_prefix + title
        
        # Подготавливаем данные для графика
        plotly_data = data.prepare_data_for_plotly(pnl_data)
        
        # Получаем статистику в HTML формате
        summary_html = data.get_data_summary_html(plotly_data)
        
        # Создаем график с выбранным типом
        fig = chart.create_plotly_chart(plotly_data, chart_type=chart_type)
        
        # --- Загрузка информации о балансе и позициях (без кеширования) ---
        account_summary_html = ""
        try:
            print("Загружаем информацию о балансе и позициях...")
            account_summary_data = data.get_account_summary(api_key, api_secret, category="linear", account_type="UNIFIED")
            # Добавляем api_key и api_secret в данные для использования в format_account_summary_html
            account_summary_data["api_key"] = api_key
            account_summary_data["api_secret"] = api_secret
            account_summary_html = data.format_account_summary_html(account_summary_data)
        except Exception as ex:
            print(f"Ошибка загрузки account summary: {ex}")
            account_summary_html = f"<p>Ошибка загрузки информации о балансе и позициях: {ex}</p>"
        
        # --- Загрузка дополнительных данных: executions и transfers ---
        executions_html = ""
        transfers_html = ""
        
        # Проверяем кеш для executions
        executions_cache_key = cache_key + "_executions"
        executions_data = load_from_cache(executions_cache_key)
        
        if executions_data is not None:
            print(f"Используем кешированные данные executions для ключа: {executions_cache_key}")
        else:
            print(f"Загружаем новые данные executions для ключа: {executions_cache_key}")
            try:
                if action == "get_pnl_today":
                    executions_data = exchange.get_executions_today(api_key, api_secret, category="spot")
                elif action == "get_pnl_yesterday":
                    executions_data = exchange.get_executions_yesterday(api_key, api_secret, category="spot")
                elif action == "get_pnl_current_month":
                    executions_data = exchange.get_executions_current_month(api_key, api_secret, category="spot")
                elif action == "get_pnl_previous_month":
                    executions_data = exchange.get_executions_previous_month(api_key, api_secret, category="spot")
                elif action == "get_pnl_custom":
                    if start_datetime and end_datetime:
                        start_dt = datetime.fromisoformat(start_datetime).replace(tzinfo=timezone.utc)
                        end_dt = datetime.fromisoformat(end_datetime).replace(tzinfo=timezone.utc)
                        start_ms = int(start_dt.timestamp() * 1000)
                        end_ms = int(end_dt.timestamp() * 1000)
                        executions_data = exchange.get_all_executions(api_key, api_secret, category="spot", 
                                                                      start_time=start_ms, end_time=end_ms)
                    else:
                        executions_data = []
                else:
                    executions_data = []
                
                save_to_cache(executions_cache_key, executions_data)
            except Exception as ex:
                print(f"Ошибка загрузки executions: {ex}")
                executions_data = []
        
        # Обрабатываем executions данные
        if executions_data:
            try:
                executions_table_data = data.prepare_executions_for_table(executions_data)
                executions_html = data.get_executions_summary_html(executions_table_data)
            except Exception as ex:
                print(f"Ошибка обработки executions: {ex}")
                executions_html = f"<p>Ошибка обработки данных executions: {ex}</p>"
        
        # Проверяем кеш для transfers (inter, universal, deposits, withdraws)
        transfers_cache_key = cache_key + "_transfers"
        transfers_cached = load_from_cache(transfers_cache_key)
        
        if transfers_cached is not None:
            print(f"Используем кешированные данные transfers для ключа: {transfers_cache_key}")
            inter_transfers = transfers_cached.get('inter', [])
            universal_transfers = transfers_cached.get('universal', [])
            deposits = transfers_cached.get('deposits', [])
            withdraws = transfers_cached.get('withdraws', [])
        else:
            print(f"Загружаем новые данные transfers для ключа: {transfers_cache_key}")
            inter_transfers = []
            universal_transfers = []
            deposits = []
            withdraws = []
            
            try:
                if action == "get_pnl_today":
                    inter_transfers = exchange.get_inter_transfers_today(api_key, api_secret)
                    universal_transfers = exchange.get_universal_transfers_today(api_key, api_secret)
                    deposits = exchange.get_deposits_today(api_key, api_secret)
                    withdraws = exchange.get_withdraws_today(api_key, api_secret)
                elif action == "get_pnl_yesterday":
                    inter_transfers = exchange.get_inter_transfers_yesterday(api_key, api_secret)
                    universal_transfers = exchange.get_universal_transfers_yesterday(api_key, api_secret)
                    deposits = exchange.get_deposits_yesterday(api_key, api_secret)
                    withdraws = exchange.get_withdraws_yesterday(api_key, api_secret)
                elif action == "get_pnl_current_month":
                    inter_transfers = exchange.get_inter_transfers_current_month(api_key, api_secret)
                    universal_transfers = exchange.get_universal_transfers_current_month(api_key, api_secret)
                    deposits = exchange.get_deposits_current_month(api_key, api_secret)
                    withdraws = exchange.get_withdraws_current_month(api_key, api_secret)
                elif action == "get_pnl_previous_month":
                    inter_transfers = exchange.get_inter_transfers_previous_month(api_key, api_secret)
                    universal_transfers = exchange.get_universal_transfers_previous_month(api_key, api_secret)
                    deposits = exchange.get_deposits_previous_month(api_key, api_secret)
                    withdraws = exchange.get_withdraws_previous_month(api_key, api_secret)
                elif action == "get_pnl_custom":
                    if start_datetime and end_datetime:
                        start_dt = datetime.fromisoformat(start_datetime).replace(tzinfo=timezone.utc)
                        end_dt = datetime.fromisoformat(end_datetime).replace(tzinfo=timezone.utc)
                        start_ms = int(start_dt.timestamp() * 1000)
                        end_ms = int(end_dt.timestamp() * 1000)
                        inter_transfers = exchange.get_all_inter_transfers(api_key, api_secret, start_time=start_ms, end_time=end_ms)
                        universal_transfers = exchange.get_all_universal_transfers(api_key, api_secret, start_time=start_ms, end_time=end_ms)
                        deposits = exchange.get_all_deposits(api_key, api_secret, start_time=start_ms, end_time=end_ms)
                        withdraws = exchange.get_all_withdraws(api_key, api_secret, start_time=start_ms, end_time=end_ms)
                
                # Сохраняем в кеш все transfers данные вместе
                save_to_cache(transfers_cache_key, {
                    'inter': inter_transfers,
                    'universal': universal_transfers,
                    'deposits': deposits,
                    'withdraws': withdraws
                })
            except Exception as ex:
                print(f"Ошибка загрузки transfers: {ex}")
        
        # Обрабатываем transfers данные
        if inter_transfers or universal_transfers or deposits or withdraws:
            try:
                transfers_table_data = data.prepare_transfers_for_table(
                    inter_transfers=inter_transfers,
                    universal_transfers=universal_transfers,
                    deposits=deposits,
                    withdraws=withdraws
                )
                transfers_html = data.get_transfers_summary_html(transfers_table_data)
            except Exception as ex:
                print(f"Ошибка обработки transfers: {ex}")
                transfers_html = f"<p>Ошибка обработки данных transfers: {ex}</p>"
        
        if fig:
            # Преобразуем график в HTML
            graph_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
            
            # Возвращаем HTML страницу с графиком через шаблон
            return templates.TemplateResponse("results.html", {
                "request": request,
                "title": title,
                "graph_html": graph_html,
                "summary_html": summary_html,
                "account_summary_html": account_summary_html,
                "executions_html": executions_html,
                "transfers_html": transfers_html,
                # Echo submitted form values so the results page can render a filled form
                "api_key": api_key,
                "api_secret": api_secret,
                "start_datetime": start_datetime,
                "end_datetime": end_datetime,
                "symbols": symbols,
                "chart_type": chart_type,
                "action": action
            })
        else:
            return HTMLResponse(content="<h1>Error: Could not generate chart</h1>")
            
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {str(e)}</h1>")


# ============================================================================
# Profit Analysis Routes
# ============================================================================

@app.post("/profit/process", response_class=HTMLResponse)
async def profit_process_loading(
    request: Request,
    api_key: str = Form(...),
    api_secret: str = Form(...),
    currency: str = Form("USDT"),
    start_datetime: str = Form(None),
    end_datetime: str = Form(None),
    show_balance: str = Form(None),
    force_sync: str = Form(None),
    full_reload: str = Form(None),
    action: str = Form("analyze")
):
    """Show loading page for profit analysis"""
    return templates.TemplateResponse("profit_loading.html", {
        "request": request,
        "api_key": api_key,
        "api_secret": api_secret,
        "currency": currency,
        "start_datetime": start_datetime or "",
        "end_datetime": end_datetime or "",
        "show_balance": show_balance or "",
        "force_sync": force_sync or "",
        "full_reload": full_reload or "",
        "action": action
    })


@app.post("/profit/process_async", response_class=HTMLResponse)
async def profit_process(
    request: Request,
    api_key: str = Form(...),
    api_secret: str = Form(...),
    currency: str = Form("USDT"),
    start_datetime: str = Form(None),
    end_datetime: str = Form(None),
    show_balance: str = Form(None),
    force_sync: str = Form(None),
    full_reload: str = Form(None),
    action: str = Form("analyze")
):
    """Process profit analysis request"""
    try:
        # Parse boolean options
        show_balance_bool = show_balance == "1"
        force_sync_bool = force_sync == "1"
        full_reload_bool = full_reload == "1"
        
        # Parse datetime if provided
        start_dt = None
        end_dt = None
        if start_datetime and end_datetime:
            start_dt = datetime.fromisoformat(start_datetime).replace(tzinfo=timezone.utc)
            end_dt = datetime.fromisoformat(end_datetime).replace(tzinfo=timezone.utc)
        
        if action == "sync_only":
            # Just sync data without analysis
            data_profit.sync_all_data(api_key, api_secret, currency, full_reload_bool)
            
            user_id = exchange.get_user_id(api_key, api_secret)
            metadata = data_profit.get_metadata(user_id)
            
            return templates.TemplateResponse("profit_results.html", {
                "request": request,
                "summary_html": "<div style='padding: 20px; text-align: center;'><h2>✅ Data Sync Complete</h2><p>Data has been synchronized successfully.</p></div>",
                "profitability_chart_html": "<p style='text-align: center; padding: 40px;'>No chart - sync only mode</p>",
                "balance_chart_html": None,
                "by_type_html": "<p>Run analysis to see breakdown</p>",
                "by_symbol_html": "<p>Run analysis to see breakdown</p>",
                "cache_info_html": format_cache_info_html(metadata),
                "api_key": api_key,
                "api_secret": api_secret,
                "currency": currency,
                "start_datetime": start_datetime,
                "end_datetime": end_datetime,
                "show_balance": show_balance_bool,
                "analysis_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            })
        
        # Full analysis
        result = data_profit.analyze_trading_performance(
            api_key, api_secret,
            start_time=start_dt,
            end_time=end_dt,
            currency=currency,
            force_sync=force_sync_bool,
            full_reload=full_reload_bool
        )
        
        # Generate summary HTML
        summary_html = data_profit.get_performance_summary_html(result)
        
        # Generate profitability chart
        profitability_chart = chart.create_profitability_chart(
            result['profitability_chart'],
            show_balance=show_balance_bool
        )
        profitability_chart_html = profitability_chart.to_html(full_html=False, include_plotlyjs='cdn') if profitability_chart else "<p>Could not generate chart</p>"
        
        # Generate balance chart if requested
        balance_chart_html = None
        if show_balance_bool:
            balance_chart = chart.create_balance_chart(result['profitability_chart'])
            if balance_chart:
                balance_chart_html = balance_chart.to_html(full_html=False, include_plotlyjs='cdn')
        
        # Generate breakdown tables
        by_type_html = format_by_type_html(result.get('by_type', {}))
        by_symbol_html = format_by_symbol_html(result.get('by_symbol', {}))
        
        # Cache info
        user_id = exchange.get_user_id(api_key, api_secret)
        metadata = data_profit.get_metadata(user_id)
        cache_info_html = format_cache_info_html(metadata)
        
        return templates.TemplateResponse("profit_results.html", {
            "request": request,
            "summary_html": summary_html,
            "profitability_chart_html": profitability_chart_html,
            "balance_chart_html": balance_chart_html,
            "by_type_html": by_type_html,
            "by_symbol_html": by_symbol_html,
            "cache_info_html": cache_info_html,
            "api_key": api_key,
            "api_secret": api_secret,
            "currency": currency,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "show_balance": show_balance_bool,
            "analysis_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(content=f"""
        <html>
        <head><title>Error</title><link rel="stylesheet" href="/static/style.css"></head>
        <body>
            <div class="window">
                <div class="title-bar"><div class="title-bar-text">⚠️ Error</div></div>
                <div class="window-body">
                    <h2>Error during analysis</h2>
                    <pre style="background: #fff; padding: 10px; border: 1px solid #808080; overflow: auto;">{str(e)}</pre>
                    <p><a href="/profit">← Back to Profit Analysis</a></p>
                </div>
            </div>
        </body>
        </html>
        """)


def format_by_type_html(by_type: dict) -> str:
    """Format transaction type breakdown as HTML table"""
    if not by_type:
        return "<p>No data available</p>"
    
    html = '''
    <table style="width: 100%; border-collapse: collapse; border: 2px solid; border-color: #808080 #ffffff #ffffff #808080; background-color: #ffffff; font-size: 11px;">
        <thead>
            <tr style="background-color: #000080; color: white;">
                <th style="padding: 5px; border: 1px solid #808080; text-align: left;">Transaction Type</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Amount</th>
            </tr>
        </thead>
        <tbody>
    '''
    
    for trans_type, amount in sorted(by_type.items(), key=lambda x: abs(x[1]), reverse=True):
        color = "green" if amount > 0 else "red" if amount < 0 else "black"
        html += f'''
            <tr>
                <td style="padding: 5px; border: 1px solid #808080;">{trans_type}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right; color: {color}; font-weight: bold;">{amount:+.4f}</td>
            </tr>
        '''
    
    html += '</tbody></table>'
    return html


def format_by_symbol_html(by_symbol: dict) -> str:
    """Format symbol breakdown as HTML table"""
    if not by_symbol:
        return "<p>No data available</p>"
    
    html = '''
    <table style="width: 100%; border-collapse: collapse; border: 2px solid; border-color: #808080 #ffffff #ffffff #808080; background-color: #ffffff; font-size: 11px;">
        <thead>
            <tr style="background-color: #000080; color: white;">
                <th style="padding: 5px; border: 1px solid #808080; text-align: left;">Symbol</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">PnL</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Fees</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: right;">Trades</th>
            </tr>
        </thead>
        <tbody>
    '''
    
    # Sort by PnL descending
    sorted_symbols = sorted(by_symbol.items(), key=lambda x: x[1].get('pnl', 0), reverse=True)
    
    for symbol, data in sorted_symbols:
        pnl = data.get('pnl', 0)
        fees = data.get('fees', 0)
        trades = data.get('trades', 0)
        pnl_color = "green" if pnl > 0 else "red" if pnl < 0 else "black"
        
        html += f'''
            <tr>
                <td style="padding: 5px; border: 1px solid #808080;">{symbol}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right; color: {pnl_color}; font-weight: bold;">{pnl:+.4f}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right; color: red;">{fees:.4f}</td>
                <td style="padding: 5px; border: 1px solid #808080; text-align: right;">{trades}</td>
            </tr>
        '''
    
    html += '</tbody></table>'
    return html


def format_cache_info_html(metadata: dict) -> str:
    """Format cache metadata as HTML"""
    if not metadata:
        return "<p>No cache information available</p>"
    
    html = '''
    <table style="width: 100%; border-collapse: collapse; border: 2px solid; border-color: #808080 #ffffff #ffffff #808080; background-color: #ffffff; font-size: 11px;">
        <thead>
            <tr style="background-color: #000080; color: white;">
                <th style="padding: 5px; border: 1px solid #808080; text-align: left;">Property</th>
                <th style="padding: 5px; border: 1px solid #808080; text-align: left;">Value</th>
            </tr>
        </thead>
        <tbody>
    '''
    
    html += f'''
        <tr>
            <td style="padding: 5px; border: 1px solid #808080;">User ID</td>
            <td style="padding: 5px; border: 1px solid #808080;">{metadata.get('user_id', 'N/A')}</td>
        </tr>
        <tr>
            <td style="padding: 5px; border: 1px solid #808080;">Currency</td>
            <td style="padding: 5px; border: 1px solid #808080;">{metadata.get('currency', 'N/A')}</td>
        </tr>
    '''
    
    # Last sync times
    last_sync = metadata.get('last_sync', {})
    for data_type, sync_time in last_sync.items():
        html += f'''
            <tr>
                <td style="padding: 5px; border: 1px solid #808080;">Last Sync: {data_type}</td>
                <td style="padding: 5px; border: 1px solid #808080;">{sync_time[:19] if sync_time else 'Never'}</td>
            </tr>
        '''
    
    # Data ranges
    data_range = metadata.get('data_range', {})
    for data_type, range_info in data_range.items():
        if isinstance(range_info, dict):
            oldest = range_info.get('oldest', 'N/A')[:10] if range_info.get('oldest') else 'N/A'
            newest = range_info.get('newest', 'N/A')[:10] if range_info.get('newest') else 'N/A'
            count = range_info.get('count', 0)
            html += f'''
                <tr style="background-color: #e0e0e0;">
                    <td style="padding: 5px; border: 1px solid #808080;">{data_type} range</td>
                    <td style="padding: 5px; border: 1px solid #808080;">{oldest} → {newest} ({count} records)</td>
                </tr>
            '''
    
    html += '</tbody></table>'
    return html


if __name__ == "__main__":
    uvicorn.run("run_app:app", host="0.0.0.0", port=8082, reload=False)