import yfinance as yf
t = yf.Ticker('RKLB')

print('=== recommendations ===')
r = t.recommendations
if r is not None:
    print(f'Type: {type(r)}')
    print(f'Columns: {r.columns.tolist()}')
    print(r.tail(3))
else:
    print('None')

print('\n=== recommendations_summary ===')
try:
    rs = t.recommendations_summary
    if rs is not None:
        print(f'Type: {type(rs)}')
        print(f'Columns: {rs.columns.tolist()}')
        print(rs)
    else:
        print('None')
except Exception as e:
    print(f'Error: {e}')

print('\n=== earnings_dates ===')
try:
    ed = t.earnings_dates
    if ed is not None:
        print(f'Type: {type(ed)}')
        print(f'Columns: {ed.columns.tolist()}')
        print(ed.head(8))
    else:
        print('None')
except Exception as e:
    print(f'Error: {e}')

print('\n=== info analyst fields ===')
info = t.info
for k in ['recommendationKey','numberOfAnalystOpinions','targetMeanPrice']:
    print(f'{k}: {info.get(k)}')
