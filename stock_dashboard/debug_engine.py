import sys
sys.path.insert(0, '.')
from analysis_engine import fetch_analyst_data, fetch_earnings_data, generate_verdict, compute_scenario_targets

print("=== RKLB 애널리스트 ===")
a = fetch_analyst_data('RKLB')
print(f"Buy: {a['buy']}, Hold: {a['hold']}, Sell: {a['sell']}")

print("\n=== RKLB 어닝 ===")
e = fetch_earnings_data('RKLB')
print(f"어닝 데이터 {len(e)}개")
for item in e[:3]:
    print(item)

print("\n=== TSLA 애널리스트 ===")
a2 = fetch_analyst_data('TSLA')
print(f"Buy: {a2['buy']}, Hold: {a2['hold']}, Sell: {a2['sell']}")

print("\n=== 손절가 테스트 ===")
ov_mock = {'current_price': 124, 'avg_target': 100, 'high_target': 127, 'low_target': 60,
           'revenue_growth': 0.6, 'low_52w': 23}
targets = compute_scenario_targets(ov_mock)
print(f"Stop Loss: ${targets['stop_loss']} ({targets['stop_loss_pct']:+.1f}%)")
v = generate_verdict(ov_mock, {}, 21, 'B', targets)
print(f"Verdict stop_loss: {v.get('stop_loss')}")
