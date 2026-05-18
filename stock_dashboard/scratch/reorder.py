"""차트 블록을 col_main 맨 아래로 이동시키는 스크립트"""
path = r"c:\Users\khw21\.gemini\stagna\stock_dashboard\deep_analyzer.py"

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 차트 블록: line 304~425 (0-indexed: 303~424)
chart_block = lines[303:425]
before_chart = lines[:303]
after_chart = lines[425:]

# after_chart 안에서 verdict 끝 위치 찾기
verdict_end_idx = None
for i, line in enumerate(after_chart):
    if "</p></div>" in line and "verdict" not in line and "unsafe_allow_html" in line:
        verdict_end_idx = i

# 더 정확한 매칭: long_term_html 뒤의 마지막 verdict closing
for i, line in enumerate(after_chart):
    if "{long_term_html}" in line:
        # 다음 줄이 </p></div> 닫는 줄
        verdict_end_idx = i + 1
        break

print(f"Chart block: {len(chart_block)} lines")
print(f"Verdict end index in after_chart: {verdict_end_idx}")
if verdict_end_idx is not None:
    print(f"Verdict end line content: {after_chart[verdict_end_idx].strip()[:60]}")

# 차트 블록 앞에 구분선 추가
separator = ["\n", "    # --- 기술적 분석 차트 (하단 배치) ---\n", "    st.markdown('<hr>', unsafe_allow_html=True)\n"]

new_after = after_chart[:verdict_end_idx+1] + separator + chart_block + after_chart[verdict_end_idx+1:]
new_content = before_chart + new_after

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_content)

print("Done! Chart moved to bottom of col_main.")
