import config
import exchange
import data
import chart
import os
import pickle

API_KEY = config.API_KEY
API_SECRET = config.API_SECRET

# exchange.get_pnl_today(API_KEY, API_SECRET, category="linear")
# exchange.get_pnl_yesterday(API_KEY, API_SECRET, category="linear")
# exchange.get_pnl_current_month(API_KEY, API_SECRET, category="linear")

print("\n=== ДАННЫЕ ЗА ПРОШЛЫЙ МЕСЯЦ ===")
cache_file = "previous_month_data.pkl"

if os.path.exists(cache_file):
    print("Загрузка данных из кеша...")
    with open(cache_file, "rb") as f:
        previous_month_data = pickle.load(f)
else:
    print("Получение данных с биржи...")
    previous_month_data = exchange.get_pnl_previous_month(API_KEY, API_SECRET, category="linear")
    with open(cache_file, "wb") as f:
        pickle.dump(previous_month_data, f)
    print("Данные сохранены в кеш")
print(f"Всего сделок за прошлый месяц: {len(previous_month_data)}")

plotly_data = data.prepare_data_for_plotly(previous_month_data)

# Вывод статистики
summary = data.data_summary(plotly_data)
print(f"\nВсего символов: {summary['total_symbols']}")
for symbol_data in summary['symbols']:
    print(f"\n{symbol_data['display_name']}:")
    print(f"  Количество сделок: {symbol_data['total_trades']}")
    print(f"  Итоговый PnL: {symbol_data['final_pnl']:.4f}")
    print(f"  Всего комиссий: {symbol_data['total_fees']:.4f}")
    print(f"  Общий объем: {symbol_data['total_volume']:.2f}")
    if symbol_data['first_trade']:
        print(f"  Первая сделка: {symbol_data['first_trade']}")
        print(f"  Последняя сделка: {symbol_data['last_trade']}")

# Вариант 1: График только PnL
fig_pnl = chart.create_plotly_chart(plotly_data, title="Накопительный PnL", chart_type='pnl')
if fig_pnl:
    fig_pnl.show()

# # Вариант 2: График только комиссий
# fig_fees = data.create_plotly_chart(plotly_data, title="Накопительные комиссии", chart_type='fees')
# if fig_fees:
#     fig_fees.show()
#
# # Вариант 3: График только объема
# fig_volume = data.create_plotly_chart(plotly_data, title="Накопительный объем торгов", chart_type='volume')
# if fig_volume:
#     fig_volume.show()
#
# # Вариант 4: Все графики вместе (3 подграфика)
# fig_all = data.create_plotly_chart(plotly_data, title="Полная статистика торговли", chart_type='all')
# if fig_all:
#     fig_all.show()