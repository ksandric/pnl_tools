import time
import asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
import uvicorn
import exchange
import data
import chart
from datetime import datetime, timezone
from utils import generate_cache_key, load_from_cache, save_to_cache

# pip3 install fastapi uvicorn pydantic apscheduler requests

app = FastAPI()
last_requests = {}
templates = Jinja2Templates(directory="templates")

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


@app.post("/process", response_class=HTMLResponse)
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
                title = "PnL Today"
            elif action == "get_pnl_yesterday":
                pnl_data = exchange.get_pnl_yesterday(api_key, api_secret, category="linear")
                title = "PnL Yesterday"
            elif action == "get_pnl_current_month":
                pnl_data = exchange.get_pnl_current_month(api_key, api_secret, category="linear")
                title = "PnL Current Month"
            elif action == "get_pnl_previous_month":
                pnl_data = exchange.get_pnl_previous_month(api_key, api_secret, category="linear")
                title = "PnL Previous Month"
            elif action == "get_pnl_custom":
                # Для кастомного периода нужно преобразовать даты в миллисекунды
                if start_datetime and end_datetime:
                    start_dt = datetime.fromisoformat(start_datetime).replace(tzinfo=timezone.utc)
                    end_dt = datetime.fromisoformat(end_datetime).replace(tzinfo=timezone.utc)
                    start_ms = int(start_dt.timestamp() * 1000)
                    end_ms = int(end_dt.timestamp() * 1000)
                    pnl_data = exchange.get_all_closed_pnl(api_key, api_secret, category="linear", 
                                                           start_time=start_ms, end_time=end_ms)
                    title = f"PnL Custom Period"
                else:
                    return HTMLResponse(content="<h1>Error: Start and End datetime are required for custom range</h1>")
            else:
                return HTMLResponse(content="<h1>Error: Unknown action</h1>")
            
            # Сохраняем в кеш
            save_to_cache(cache_key, pnl_data)
        
        # Устанавливаем заголовок если не был установлен (для кеша)
        if 'title' not in locals():
            if action == "get_pnl_today":
                title = "PnL Today"
            elif action == "get_pnl_yesterday":
                title = "PnL Yesterday"
            elif action == "get_pnl_current_month":
                title = "PnL Current Month"
            elif action == "get_pnl_previous_month":
                title = "PnL Previous Month"
            elif action == "get_pnl_custom":
                title = "PnL Custom Period"
        
        title = title_prefix + title
        
        # Подготавливаем данные для графика
        plotly_data = data.prepare_data_for_plotly(pnl_data)
        
        # Получаем статистику в HTML формате
        summary_html = data.get_data_summary_html(plotly_data)
        
        # Создаем график с выбранным типом
        fig = chart.create_plotly_chart(plotly_data, title=title, chart_type=chart_type)
        
        if fig:
            # Преобразуем график в HTML
            graph_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
            
            # Возвращаем HTML страницу с графиком через шаблон
            return templates.TemplateResponse("results.html", {
                "request": request,
                "title": title,
                "graph_html": graph_html,
                "summary_html": summary_html
            })
        else:
            return HTMLResponse(content="<h1>Error: Could not generate chart</h1>")
            
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {str(e)}</h1>")


if __name__ == "__main__":
    uvicorn.run("run_app:app", host="127.0.0.1", port=8082, reload=True)