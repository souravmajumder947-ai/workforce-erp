from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V10.1 KPI RENDER + LIVE LOGIC FIX"
if MARK in s:
    print("V10.1 patch already applied")
    raise SystemExit(0)

# 1) Insert marker just before V10 KPI section so the patch is identifiable.
anchor = '''    # Reference-style KPI rail, driven by live selected-date data.
    _v10_kpi_items = ['''
if anchor not in s:
    raise RuntimeError("V10 KPI anchor not found")
s = s.replace(
    anchor,
    '''    # V10.1 KPI RENDER + LIVE LOGIC FIX
    # Reference-style KPI rail, driven by live selected-date data.
    _v10_kpi_items = [''',
    1,
)

# 2) Replace raw nested HTML grid (which Streamlit can interpret as a code block)
#    with six independent Streamlit columns, each rendering one safe card.
old_kpi = '''    _v10_kpi_html = "".join(
        f"""
        <div class="v10-kpi {tone}">
          <div class="v10-kpi-icon">{icon}</div>
          <div><small>{html.escape(label)}</small><b>{value}</b><span>{html.escape(sub)}</span></div>
        </div>
        """
        for icon, label, value, sub, tone in _v10_kpi_items
    )
    st.markdown(f'<div class="v10-kpi-grid">{_v10_kpi_html}</div>', unsafe_allow_html=True)
'''
new_kpi = '''    _v10_kpi_cols = st.columns(6, gap="small")
    for _v10_i, (icon, label, value, sub, tone) in enumerate(_v10_kpi_items):
        with _v10_kpi_cols[_v10_i]:
            st.markdown(
                (
                    f'<div class="v10-kpi {tone}">'
                    f'<div class="v10-kpi-icon">{icon}</div>'
                    f'<div><small>{html.escape(label)}</small>'
                    f'<b>{value}</b><span>{html.escape(sub)}</span></div>'
                    f'</div>'
                ),
                unsafe_allow_html=True,
            )
'''
if old_kpi not in s:
    raise RuntimeError("Old KPI HTML block not found")
s = s.replace(old_kpi, new_kpi, 1)

# 3) The workforce health score should not punish an empty current-day source
#    as if it were bad attendance. Show a data-pending state until attendance exists.
old_health_state = '''    if _v10_health >= 90:
        _v10_health_word, _v10_health_tone = "Excellent", "good"
    elif _v10_health >= 75:
        _v10_health_word, _v10_health_tone = "Good", "good"
    elif _v10_health >= 55:
        _v10_health_word, _v10_health_tone = "Attention", "warn"
    else:
        _v10_health_word, _v10_health_tone = "Action Required", "danger"
'''
new_health_state = '''    if _v94_upload_pending:
        _v10_health_word, _v10_health_tone = "Awaiting Attendance", "warn"
        # Keep the ring meaningful as a system-readiness score until daily attendance arrives.
        _v10_health = max(0.0, min(100.0, (_v10_salary_ready * 0.55) + (_v10_dept_ready * 0.45)))
    elif _v10_health >= 90:
        _v10_health_word, _v10_health_tone = "Excellent", "good"
    elif _v10_health >= 75:
        _v10_health_word, _v10_health_tone = "Good", "good"
    elif _v10_health >= 55:
        _v10_health_word, _v10_health_tone = "Attention", "warn"
    else:
        _v10_health_word, _v10_health_tone = "Action Required", "danger"
'''
if old_health_state not in s:
    raise RuntimeError("Health-state block not found")
s = s.replace(old_health_state, new_health_state, 1)

# 4) Current-month payroll is normally still open. Only flag "not finalized"
#    on this dashboard when the selected payroll month is earlier than the current month.
alert_old = '''    if _v94_payroll_pending and "Payroll" in available_modules:
        _v10_alerts.append(("Payroll Not Finalized", f"{global_payroll_month.strftime('%b %Y')} is not fully closed", "Medium", "Payroll"))
'''
alert_new = '''    _v10_this_month = datetime.now(IST).date().replace(day=1)
    _v10_payroll_close_due = global_payroll_month < _v10_this_month
    if _v94_payroll_pending and _v10_payroll_close_due and "Payroll" in available_modules:
        _v10_alerts.append(("Payroll Not Finalized", f"{global_payroll_month.strftime('%b %Y')} is not fully closed", "Medium", "Payroll"))
'''
if alert_old not in s:
    raise RuntimeError("Payroll alert block not found")
s = s.replace(alert_old, alert_new, 1)

# 5) Exact date labels on the trend chart: avoids repeated/overlapping temporal ticks.
old_trend_prep = '''        _v10_trend = (
            _v10_trend_raw.groupby(["work_date", "Trend"], as_index=False)["employees"].sum()
            if not _v10_trend_raw.empty else pd.DataFrame()
        )
'''
new_trend_prep = '''        _v10_trend = (
            _v10_trend_raw.groupby(["work_date", "Trend"], as_index=False)["employees"].sum()
            if not _v10_trend_raw.empty else pd.DataFrame()
        )
        if not _v10_trend.empty:
            _v10_trend["Date Label"] = _v10_trend["work_date"].dt.strftime("%d %b")
'''
if old_trend_prep not in s:
    raise RuntimeError("Trend prep block not found")
s = s.replace(old_trend_prep, new_trend_prep, 1)

old_chart_x = '''                        x=alt.X("work_date:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0)),'''
new_chart_x = '''                        x=alt.X("Date Label:N", title=None, sort=None, axis=alt.Axis(labelAngle=0)),'''
if old_chart_x not in s:
    raise RuntimeError("Trend x-axis block not found")
s = s.replace(old_chart_x, new_chart_x, 1)

# 6) CSS: Streamlit columns now own the grid. Make each card fill its column cleanly.
css_anchor = '''/* KPI rail */
.v10-kpi-grid{
  display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin:8px 0 10px;
}
.v10-kpi{
'''
css_new = '''/* KPI rail */
.v10-kpi-grid{
  display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin:8px 0 10px;
}
body:has(.v10-live-home-marker) div[data-testid="stHorizontalBlock"]:has(.v10-kpi){
  gap:.45rem!important;
  margin:8px 0 10px!important;
}
body:has(.v10-live-home-marker) div[data-testid="stColumn"]:has(.v10-kpi){
  min-width:0!important;
}
.v10-kpi{
  width:100%;
'''
if css_anchor not in s:
    raise RuntimeError("KPI CSS anchor not found")
s = s.replace(css_anchor, css_new, 1)

p.write_text(s, encoding="utf-8")
print("Applied V10.1 KPI rendering and live logic fixes")
