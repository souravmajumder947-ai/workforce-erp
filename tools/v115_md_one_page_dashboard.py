from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V11.5 MD ONE PAGE MONTHLY COMMAND CENTRE"
if MARK in s:
    print("V11.5 MD dashboard already applied")
    raise SystemExit(0)

anchor = '''    # 7-day attendance trend.
    _v10_trend_start = global_work_date - timedelta(days=6)
    _v10_trend_sql = """
        SELECT work_date, status, COUNT(*) AS employees
        FROM attendance
        WHERE work_date BETWEEN ? AND ?
    """
    _v10_trend_params = (_v10_trend_start.isoformat(), global_work_date.isoformat())
'''

insert = '''    # V11.5 MD ONE PAGE MONTHLY COMMAND CENTRE
    # The Home dashboard must be sufficient for MD review without opening operational tabs.
    _v115_first, _v115_last = _month_range(global_payroll_month)
    _v115_month_clause, _v115_month_params = v5_division_clause(global_division, "a.")
    try:
        _v115_month_att = read_df(
            """SELECT a.division,a.work_date,a.employee_id,a.status,a.ot_hours
               FROM attendance a
               WHERE a.work_date BETWEEN ? AND ? """ + _v115_month_clause + """
               ORDER BY a.work_date,a.division,a.employee_id""",
            (_v115_first.isoformat(), _v115_last.isoformat()) + _v115_month_params
        )
    except Exception:
        _v115_month_att = pd.DataFrame()

    _v115_month_status = (
        _v115_month_att["status"].fillna("").astype(str).str.strip()
        if not _v115_month_att.empty else pd.Series(dtype=str)
    )
    _v115_present_days = float((_v115_month_status == "Present").sum())
    _v115_half_days = float((_v115_month_status == "Half Day").sum())
    _v115_present_eq = _v115_present_days + (0.5 * _v115_half_days)
    _v115_absent_days = float(_v115_month_status.isin(["Absent","LWP"]).sum())
    _v115_leave_days = float(_v115_month_status.isin(["Leave","CL","SL","EL"]).sum())
    _v115_wo_days = float(_v115_month_status.isin(["WO","Holiday"]).sum())
    _v115_review_days = int((_v115_month_status == "HR Review").sum())
    _v115_att_records = len(_v115_month_att)
    _v115_att_employees = (
        int(_v115_month_att["employee_id"].astype(str).nunique())
        if not _v115_month_att.empty else 0
    )
    _v115_month_ot = (
        float(pd.to_numeric(_v115_month_att.get("ot_hours", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        if not _v115_month_att.empty else 0.0
    )
    _v115_present_rate = (
        (_v115_present_eq / _v115_att_records * 100.0)
        if _v115_att_records else 0.0
    )

    _v115_gross = (
        float(pd.to_numeric(payroll.get("Gross Earned", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        if not payroll.empty else 0.0
    )
    _v115_net = (
        float(pd.to_numeric(payroll.get("Net Payable", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        if not payroll.empty else 0.0
    )
    _v115_ot_pay = (
        float(pd.to_numeric(payroll.get("OT Pay", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        if not payroll.empty else 0.0
    )
    _v115_pf_esic = (
        float(
            pd.to_numeric(payroll.get("PF", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
            + pd.to_numeric(payroll.get("ESIC", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
        )
        if not payroll.empty else 0.0
    )

    try:
        _v115_contractor = contractor_month_summary(global_payroll_month)
        if global_division not in (ALL_DIVISIONS, "Greater Noida Plant"):
            _v115_contractor = _v115_contractor.iloc[0:0]
        _v115_contractor_cost = (
            float(pd.to_numeric(_v115_contractor.get("amount", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
            if not _v115_contractor.empty else 0.0
        )
    except Exception:
        _v115_contractor = pd.DataFrame()
        _v115_contractor_cost = 0.0

    _v115_ops = {}
    if global_division in (ALL_DIVISIONS, "Greater Noida Plant"):
        try:
            _v115_ops_df = read_df(
                """SELECT
                       COALESCE(SUM(CASE WHEN COALESCE(target_type,'')='FIXED_TON'
                           THEN COALESCE(NULLIF(good_output_ton,0),production_ton,0) ELSE 0 END),0) AS corr_output,
                       COALESCE(SUM(CASE WHEN COALESCE(target_type,'')='FIXED_TON'
                           THEN COALESCE(target_ton,0) ELSE 0 END),0) AS corr_target,
                       COALESCE(SUM(COALESCE(waste_ton,0)),0) AS waste_ton,
                       COALESCE(SUM(COALESCE(breakdown_hours,0)),0) AS breakdown_hours,
                       AVG(CASE WHEN COALESCE(target_type,'')='MATERIAL_CONVERSION'
                           AND conversion_pct>0 THEN conversion_pct END) AS conversion_pct,
                       AVG(CASE WHEN COALESCE(target_type,'')='MATERIAL_CONVERSION'
                           AND yield_pct>0 THEN yield_pct END) AS yield_pct
                   FROM production
                   WHERE work_date BETWEEN ? AND ?""",
                (_v115_first.isoformat(), _v115_last.isoformat())
            )
            if not _v115_ops_df.empty:
                _v115_ops = _v115_ops_df.iloc[0].to_dict()
        except Exception:
            _v115_ops = {}

    _v115_corr_output = float(_v115_ops.get("corr_output") or 0)
    _v115_corr_target = float(_v115_ops.get("corr_target") or 0)
    _v115_corr_achievement = (
        (_v115_corr_output / _v115_corr_target * 100.0)
        if _v115_corr_target > 0 else 0.0
    )
    _v115_waste = float(_v115_ops.get("waste_ton") or 0)
    _v115_breakdown = float(_v115_ops.get("breakdown_hours") or 0)
    _v115_conversion = float(_v115_ops.get("conversion_pct") or 0)
    _v115_yield = float(_v115_ops.get("yield_pct") or 0)

    st.markdown("### MD Monthly Command Centre")
    st.caption(
        f"Complete executive view for **{global_payroll_month.strftime('%B %Y')}** · "
        f"{html.escape(str(global_division))}. Daily cards above remain the selected Working Date; "
        "everything below is the full selected month."
    )

    _v115_kpi_items = [
        ("▣", "Present Eq. Days", f"{_v115_present_eq:,.1f}", f"{_v115_att_records:,} attendance records", "green"),
        ("●", "Absent / LWP Days", f"{_v115_absent_days:,.0f}", f"Present rate {_v115_present_rate:.1f}% of records", "red"),
        ("◒", "Leave Days", f"{_v115_leave_days:,.0f}", "CL · SL · EL · Leave", "amber"),
        ("◷", "WO / Holiday Days", f"{_v115_wo_days:,.0f}", f"Half days {_v115_half_days:,.0f}", "purple"),
        ("◴", "Monthly OT Hours", f"{_v115_month_ot:,.2f}", f"{_v115_att_employees:,} employees seen", "cyan"),
        ("!", "HR Review Pending", f"{_v115_review_days:,}", "Selected month", "red" if _v115_review_days else "green"),
    ]
    _v115_cols = st.columns(6, gap="small")
    for _v115_i, (_ic, _lb, _val, _sub, _tone) in enumerate(_v115_kpi_items):
        with _v115_cols[_v115_i]:
            st.markdown(
                (
                    f'<div class="v10-kpi {_tone}">'
                    f'<div class="v10-kpi-icon">{_ic}</div>'
                    f'<div><small>{html.escape(_lb)}</small>'
                    f'<b>{_val}</b><span>{html.escape(_sub)}</span></div>'
                    f'</div>'
                ),
                unsafe_allow_html=True,
            )

    _v115_cost_items = [
        ("₹", "Gross Earned", v5_money(_v115_gross) if can_view_salary(_current_role) else "Restricted", global_payroll_month.strftime("%b %Y"), "blue"),
        ("₹", "Net Payable", ("PENDING" if _v10_pay_blockers else v5_money(_v115_net)) if can_view_salary(_current_role) else "Restricted", f"{_v10_pay_blockers:,} payroll blocker(s)" if _v10_pay_blockers else "Ready", "amber" if _v10_pay_blockers else "green"),
        ("◴", "OT Pay", v5_money(_v115_ot_pay) if can_view_salary(_current_role) else "Restricted", "Attendance-linked", "cyan"),
        ("▤", "PF + ESIC", v5_money(_v115_pf_esic) if can_view_salary(_current_role) else "Restricted", "Employee deductions", "purple"),
        ("▣", "Contractor Payable", v5_money(_v115_contractor_cost), "Greater Noida · selected month", "amber"),
        ("🏭", "Corrugation Output", f"{_v115_corr_output:,.2f} T", f"Target {_v115_corr_target:,.2f} T · {_v115_corr_achievement:.1f}%", "blue"),
    ]
    _v115_cost_cols = st.columns(6, gap="small")
    for _v115_i, (_ic, _lb, _val, _sub, _tone) in enumerate(_v115_cost_items):
        with _v115_cost_cols[_v115_i]:
            st.markdown(
                (
                    f'<div class="v10-kpi {_tone}">'
                    f'<div class="v10-kpi-icon">{_ic}</div>'
                    f'<div><small>{html.escape(_lb)}</small>'
                    f'<b>{html.escape(str(_val))}</b><span>{html.escape(str(_sub))}</span></div>'
                    f'</div>'
                ),
                unsafe_allow_html=True,
            )

    # Division-wise monthly attendance is visible directly on the MD dashboard.
    _v115_div_rows = []
    _v115_scope_divisions = DIVISIONS if global_division == ALL_DIVISIONS else [global_division]
    for _v115_div in _v115_scope_divisions:
        _v115_sub_emp = employees[employees["division"].astype(str) == _v115_div] if not employees.empty else pd.DataFrame()
        _v115_sub = (
            _v115_month_att[_v115_month_att["division"].astype(str) == _v115_div].copy()
            if not _v115_month_att.empty else pd.DataFrame()
        )
        _v115_ss = (
            _v115_sub["status"].fillna("").astype(str).str.strip()
            if not _v115_sub.empty else pd.Series(dtype=str)
        )
        _v115_div_rows.append({
            "Division": _v115_div,
            "Active Employees": len(_v115_sub_emp),
            "Attendance Records": len(_v115_sub),
            "Present Eq. Days": float((_v115_ss == "Present").sum()) + 0.5 * float((_v115_ss == "Half Day").sum()),
            "Absent/LWP": int(_v115_ss.isin(["Absent","LWP"]).sum()),
            "Leave": int(_v115_ss.isin(["Leave","CL","SL","EL"]).sum()),
            "WO/Holiday": int(_v115_ss.isin(["WO","Holiday"]).sum()),
            "HR Review": int((_v115_ss == "HR Review").sum()),
            "OT Hours": (
                float(pd.to_numeric(_v115_sub.get("ot_hours", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
                if not _v115_sub.empty else 0.0
            ),
        })

    _v115_left, _v115_mid, _v115_right = st.columns([1.35, 1.0, 1.0], gap="small")
    with _v115_left:
        with st.container(border=True):
            st.markdown(
                '<div class="v10-panel-title"><span>DIVISION MONTHLY SUMMARY</span><small>MD view · no drill-down required</small></div>',
                unsafe_allow_html=True,
            )
            st.dataframe(
                pd.DataFrame(_v115_div_rows),
                hide_index=True,
                use_container_width=True,
                height=220,
            )

    with _v115_mid:
        with st.container(border=True):
            st.markdown(
                '<div class="v10-panel-title"><span>PAYROLL & COST CONTROL</span><small>Selected month</small></div>',
                unsafe_allow_html=True,
            )
            if can_view_salary(_current_role):
                _v115_pay_rows = pd.DataFrame([
                    {"Metric":"Gross Earned","Value":v5_money(_v115_gross)},
                    {"Metric":"Net Payable","Value":"Pending" if _v10_pay_blockers else v5_money(_v115_net)},
                    {"Metric":"OT Pay","Value":v5_money(_v115_ot_pay)},
                    {"Metric":"PF + ESIC","Value":v5_money(_v115_pf_esic)},
                    {"Metric":"Contractor Payable","Value":v5_money(_v115_contractor_cost)},
                    {"Metric":"Payroll Blockers","Value":f"{_v10_pay_blockers:,}"},
                ])
                st.dataframe(_v115_pay_rows, hide_index=True, use_container_width=True, height=220)
            else:
                st.info("Salary figures are restricted for this role.")

    with _v115_right:
        with st.container(border=True):
            st.markdown(
                '<div class="v10-panel-title"><span>OPERATIONS & HR RISK</span><small>Selected month</small></div>',
                unsafe_allow_html=True,
            )
            _v115_ops_rows = pd.DataFrame([
                {"Metric":"Corrugation Achievement","Value":f"{_v115_corr_achievement:.1f}%"},
                {"Metric":"Logged Waste","Value":f"{_v115_waste:,.2f} T"},
                {"Metric":"Breakdown","Value":f"{_v115_breakdown:,.2f} Hrs"},
                {"Metric":"Avg Conversion","Value":f"{_v115_conversion:.1f}%"},
                {"Metric":"Avg Yield","Value":f"{_v115_yield:.1f}%"},
                {"Metric":"Salary Master Gaps","Value":f"{salary_missing:,}"},
                {"Metric":"Employee Master Gaps","Value":f"{dept_pending:,}"},
                {"Metric":"Attendance HR Review","Value":f"{_v115_review_days:,}"},
            ])
            st.dataframe(_v115_ops_rows, hide_index=True, use_container_width=True, height=220)

    # Monthly attendance trend for the selected Payroll Month.
    _v10_trend_start = _v115_first
    _v10_trend_end = _v115_last
    _v10_trend_sql = """
        SELECT work_date, status, COUNT(*) AS employees
        FROM attendance
        WHERE work_date BETWEEN ? AND ?
    """
    _v10_trend_params = (_v10_trend_start.isoformat(), _v10_trend_end.isoformat())
'''

if anchor not in s:
    raise RuntimeError("Home attendance-trend anchor not found")
s = s.replace(anchor, insert, 1)

old_title = '''                '<div class="v10-panel-title"><span>ATTENDANCE TREND</span><small>Last 7 working dates in source</small></div>',
'''
new_title = '''                f'<div class="v10-panel-title"><span>ATTENDANCE TREND</span><small>{global_payroll_month.strftime("%b %Y")} · full month</small></div>',
'''
if old_title not in s:
    raise RuntimeError("Attendance trend title anchor not found")
s = s.replace(old_title, new_title, 1)

p.write_text(s, encoding="utf-8")
print("Applied V11.5 MD one-page monthly command centre")
