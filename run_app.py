from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
import exchange
import data
import data_profit
import chart
from datetime import datetime, timezone

# pip3 install fastapi uvicorn pydantic apscheduler requests

app = FastAPI()
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
@app.get("/profit", response_class=HTMLResponse)
async def profit_page(
    request: Request,
    api_key: str = None,
    api_secret: str = None,
    currency: str = "USDT",
    category: str = "linear",
    start_datetime: str = None,
    end_datetime: str = None,
    force_sync: str = None,
    full_reload: str = None,
    show_symbol_chart: str = None
):
    """Profit analysis page with query parameter support"""
    return templates.TemplateResponse("profit.html", {
        "request": request,
        "api_key": api_key or "",
        "api_secret": api_secret or "",
        "currency": currency,
        "category": category,
        "start_datetime": start_datetime or "",
        "end_datetime": end_datetime or "",
        "force_sync": force_sync == "1",
        "full_reload": full_reload == "1",
        "show_symbol_chart": show_symbol_chart == "1"
    })


# ============================================================================
# Profit Analysis Routes
# ============================================================================

@app.post("/profit/process", response_class=HTMLResponse)
async def profit_process_loading(
    request: Request,
    api_key: str = Form(...),
    api_secret: str = Form(...),
    currency: str = Form("USDT"),
    category: str = Form("linear"),
    start_datetime: str = Form(None),
    end_datetime: str = Form(None),
    force_sync: str = Form(None),
    full_reload: str = Form(None),
    show_symbol_chart: str = Form(None),
    action: str = Form("analyze")
):
    """Show loading page for profit analysis"""
    return templates.TemplateResponse("profit_loading.html", {
        "request": request,
        "api_key": api_key,
        "api_secret": api_secret,
        "currency": currency,
        "category": category,
        "start_datetime": start_datetime or "",
        "end_datetime": end_datetime or "",
        "force_sync": force_sync or "",
        "full_reload": full_reload or "",
        "show_symbol_chart": show_symbol_chart or "",
        "action": action
    })


@app.post("/profit/process_async", response_class=HTMLResponse)
async def profit_process(
    request: Request,
    api_key: str = Form(...),
    api_secret: str = Form(...),
    currency: str = Form("USDT"),
    category: str = Form("linear"),
    start_datetime: str = Form(None),
    end_datetime: str = Form(None),
    force_sync: str = Form(None),
    full_reload: str = Form(None),
    show_symbol_chart: str = Form(None),
    action: str = Form("analyze")
):
    """Process profit analysis request"""
    try:
        # Parse boolean options
        force_sync_bool = force_sync == "1"
        full_reload_bool = full_reload == "1"
        show_symbol_chart_bool = show_symbol_chart == "1"
        
        # Parse datetime if provided
        start_dt = None
        end_dt = None
        if start_datetime and end_datetime:
            start_dt = datetime.fromisoformat(start_datetime).replace(tzinfo=timezone.utc)
            end_dt = datetime.fromisoformat(end_datetime).replace(tzinfo=timezone.utc)
        
        if action == "sync_only":
            # Just sync data without analysis
            data_profit.sync_all_data(api_key, api_secret, full_reload_bool)
            
            user_id = exchange.get_user_id(api_key, api_secret)
            metadata = data_profit.get_metadata(user_id)
            
            # Create a minimal result for sync-only mode
            sync_result = {
                "currency": currency,
                "period": {"start": None, "end": None},
                "initial_balance": 0,
                "current_balance": 0,
                "unrealized_pnl": 0,
                "effective_balance": 0,
                "trading_pnl": 0,
                "trading_fees": 0,
                "funding_fees": 0,
                "net_trading_profit": 0,
                "total_trades": 0,
                "deposits": 0,
                "deposits_count": 0,
                "withdrawals": 0,
                "withdrawals_count": 0,
                "total_profit_percent": 0,
                "current_profit_percent_with_unrealized": 0
            }
            
            return templates.TemplateResponse("profit_results.html", {
                "request": request,
                "result": sync_result,
                "profitability_chart_html": "<p style='text-align: center; padding: 40px;'>No chart - sync only mode</p>",
                "balance_chart_html": None,
                "by_type": {},
                "by_symbol": {},
                "cache_info": metadata,
                "api_key": api_key,
                "api_secret": api_secret,
                "currency": currency,
                "category": category,
                "start_datetime": start_datetime,
                "end_datetime": end_datetime,
                "analysis_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            })
        
        # Full analysis
        result = data_profit.analyze_trading_performance(
            api_key, api_secret,
            start_time=start_dt,
            end_time=end_dt,
            currency=currency,
            category=category,
            force_sync=force_sync_bool,
            full_reload=full_reload_bool
        )
        
        # Generate profitability chart
        profitability_chart = chart.create_profitability_chart(
            result['profitability_chart']
        )
        
        # Config для графика с кнопкой полноэкранного просмотра
        chart_config = {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToAdd': ['toImage'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'profitability_chart',
                'height': 1080,
                'width': 1920,
                'scale': 2
            }
        }
        
        profitability_chart_html = profitability_chart.to_html(full_html=False, include_plotlyjs='cdn', config=chart_config) if profitability_chart else "<p>Could not generate chart</p>"
        
        # Generate balance chart (always)
        balance_chart = chart.create_balance_chart(result['profitability_chart'])
        
        balance_chart_config = {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToAdd': ['toImage'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'balance_chart',
                'height': 1080,
                'width': 1920,
                'scale': 2
            }
        }
        
        balance_chart_html = balance_chart.to_html(full_html=False, include_plotlyjs='cdn', config=balance_chart_config) if balance_chart else None
        
        # Generate PnL by symbol chart (optional)
        symbol_chart_html = None
        print(f"DEBUG: show_symbol_chart_bool = {show_symbol_chart_bool}")
        print(f"DEBUG: pnl_by_symbol_chart exists = {bool(result.get('pnl_by_symbol_chart'))}")
        if result.get('pnl_by_symbol_chart'):
            pnl_data = result['pnl_by_symbol_chart']
            print(f"DEBUG: pnl_by_symbol_chart type = {type(pnl_data)}")
            print(f"DEBUG: pnl_by_symbol_chart keys = {pnl_data.keys() if isinstance(pnl_data, dict) else 'not a dict'}")
            if isinstance(pnl_data, dict) and 'data' in pnl_data:
                print(f"DEBUG: number of symbols = {len(pnl_data['data'])}")
        
        if show_symbol_chart_bool and result.get('pnl_by_symbol_chart'):
            pnl_by_symbol_data = result['pnl_by_symbol_chart']
            # Check if there's actual data
            if isinstance(pnl_by_symbol_data, dict) and pnl_by_symbol_data.get('data'):
                print(f"DEBUG: Creating symbol chart with {len(pnl_by_symbol_data['data'])} symbols")
                symbol_chart = chart.create_pnl_by_symbol_chart(pnl_by_symbol_data)
                
                symbol_chart_config = {
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToAdd': ['toImage'],
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'pnl_by_symbol_chart',
                        'height': 1080,
                        'width': 1920,
                        'scale': 2
                    }
                }
                
                symbol_chart_html = symbol_chart.to_html(full_html=False, include_plotlyjs='cdn', config=symbol_chart_config) if symbol_chart else None
                print(f"DEBUG: symbol_chart_html created = {bool(symbol_chart_html)}")
            else:
                print("DEBUG: No symbol data available - pnl_by_symbol_chart is empty or has no 'data' key")
        else:
            if not show_symbol_chart_bool:
                print("DEBUG: Symbol chart disabled - checkbox not checked")
            if not result.get('pnl_by_symbol_chart'):
                print("DEBUG: Symbol chart disabled - no data in result")
        
        # Load account summary (balance and positions)
        account_summary_html = ""
        try:
            account_summary_data = data.get_account_summary(api_key, api_secret, category="linear", account_type="UNIFIED")
            account_summary_data["api_key"] = api_key
            account_summary_data["api_secret"] = api_secret
            account_summary_html = data.format_account_summary_html(account_summary_data)
        except Exception as ex:
            print(f"Error loading account summary: {ex}")
            account_summary_html = f"<p>Error loading account information: {ex}</p>"
        
        # Cache info
        user_id = exchange.get_user_id(api_key, api_secret)
        metadata = data_profit.get_metadata(user_id)
        
        # Sort by_symbol by PnL descending
        by_symbol_sorted = sorted(
            result.get('by_symbol', {}).items(),
            key=lambda x: x[1].get('pnl', 0),
            reverse=True
        )
        
        # Sort by_type by absolute amount descending
        by_type_sorted = sorted(
            result.get('by_type', {}).items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        # Get detailed transfers data
        deposits_list = result.get('deposits_detail', [])
        withdrawals_list = result.get('withdrawals_detail', [])
        
        # Get transfer transactions from transaction logs
        transfer_in_list = []
        transfer_out_list = []
        transaction_logs = result.get('profitability_chart', {}).get('transaction_logs', [])
        for log in transaction_logs:
            log_type = log.get('type', '')
            if log_type == 'TRANSFER_IN':
                transfer_in_list.append(log)
            elif log_type == 'TRANSFER_OUT':
                transfer_out_list.append(log)
        
        return templates.TemplateResponse("profit_results.html", {
            "request": request,
            "result": result,
            "profitability_chart_html": profitability_chart_html,
            "balance_chart_html": balance_chart_html,
            "symbol_chart_html": symbol_chart_html,
            "account_summary_html": account_summary_html,
            "by_type": by_type_sorted,
            "by_symbol": by_symbol_sorted,
            "deposits_list": deposits_list,
            "withdrawals_list": withdrawals_list,
            "transfer_in_list": transfer_in_list,
            "transfer_out_list": transfer_out_list,
            "show_symbol_chart": "1" if show_symbol_chart_bool else "0",
            "cache_info": metadata,
            "api_key": api_key,
            "api_secret": api_secret,
            "currency": currency,
            "category": category,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
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
                <div class="title-bar"><div class="title-bar-text">Error</div></div>
                <div class="window-body">
                    <h2>Error during analysis</h2>
                    <pre style="background: #fff; padding: 10px; border: 1px solid #808080; overflow: auto;">{str(e)}</pre>
                    <p><a href="/profit">Back to Profit Analysis</a></p>
                </div>
            </div>
        </body>
        </html>
        """)


if __name__ == "__main__":
    uvicorn.run("run_app:app", host="0.0.0.0", port=8082, reload=False)