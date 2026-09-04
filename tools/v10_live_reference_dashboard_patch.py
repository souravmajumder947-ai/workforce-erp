from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V10.0 LIVE REFERENCE DASHBOARD"
if MARK in s:
    print("V10 dashboard patch already applied")
    raise SystemExit(0)

# Product presentation.
s = s.replace(
    'page_title="Reliable Packaging HRMS V9.6 AI Command Centre"',
    'page_title="Reliable Packaging HRMS V10 Live Command Centre"',
    1
)

# Logged-in sidebar brand: dark native treatment instead of the white logo plate.
old_sidebar = '''st.sidebar.markdown(
    f"""
    <div class="v8-brand">
      <div class="v8-brand-plate">
        <img src="{LOGO_FULL_DATA_URI}" alt="Reliable Packaging">
      </div>
      <div class="v8-brand-meta">
        <span><span class="v8-live-dot"></span>HRMS LIVE</span>
        <span>V9.6 AI</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)'''
new_sidebar = '''st.sidebar.markdown(
    f"""
    <div class="v10-sidebrand">
      <img src="{LOGO_ICON_DATA_URI}" alt="Reliable Packaging">
      <div class="v10-sidebrand-copy">
        <b>RELIABLE PACKAGING</b>
        <strong>INDUSTRIES LIMITED</strong>
        <small><span class="v8-live-dot"></span> SMART HRMS · V10 LIVE</small>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)'''
if old_sidebar not in s:
    raise RuntimeError("Logged-in sidebar brand anchor not found")
s = s.replace(old_sidebar, new_sidebar, 1)

# Replace only the Home page. All operational modules remain untouched.
home_start = s.find('if page == "Home":')
mgmt_marker = '''# ============================================================
# MANAGEMENT — EXECUTIVE DASHBOARD
# ============================================================
elif page == "Management":'''
home_end = s.find(mgmt_marker, home_start)
if home_start < 0 or home_end < 0:
    raise RuntimeError("Home/Management page anchors not found")

home = r'''if page == "Home":
    # ============================================================
    # V10.0 LIVE REFERENCE DASHBOARD
    # A live implementation of the approved command-centre concept.
    # All metrics come from the existing HRMS database and selected context.
    # ============================================================
    st.markdown('<div class="v10-live-home-marker"></div>', unsafe_allow_html=True)

    employees = v5_active_employees(global_division)
    attendance = v5_attendance_for_date(global_work_date, global_division)
    payroll = (
        calculate_live_payroll(global_payroll_month, global_division)
        if can_view_salary(_current_role) else pd.DataFrame()
    )

    active_count = len(employees)
    _v10_status = attendance["status"].fillna("").astype(str) if not attendance.empty else pd.Series(dtype=str)
    present = int((_v10_status == "Present").sum()) if not attendance.empty else 0
    absent = int(_v10_status.isin(["Absent", "LWP"]).sum()) if not attendance.empty else 0
    on_leave = int(_v10_status.isin(["CL", "SL", "EL", "Leave"]).sum()) if not attendance.empty else 0
    weekly_off = int((_v10_status == "WO").sum()) if not attendance.empty else 0
    half_day = int((_v10_status == "Half Day").sum()) if not attendance.empty else 0
    review = int((_v10_status == "HR Review").sum()) if not attendance.empty else 0
    ot_hours = (
        float(pd.to_numeric(attendance.get("ot_hours", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        if not attendance.empty else 0.0
    )

    salary_available = 0
    salary_missing = 0
    dept_pending = 0
    if not employees.empty:
        _v10_salary_ok = (
            pd.to_numeric(employees.get("monthly_salary", 0), errors="coerce").fillna(0).gt(0)
            | pd.to_numeric(employees.get("gross_pay", 0), errors="coerce").fillna(0).gt(0)
        )
        salary_available = int(_v10_salary_ok.sum())
        salary_missing = int((~_v10_salary_ok).sum())
        _v10_dm = read_df("SELECT department FROM departments WHERE active='Yes'")
        _v10_dep_set = set(_v10_dm["department"].astype(str).tolist()) if not _v10_dm.empty else set()
        dept_pending = (
            int((~employees["department"].fillna("").astype(str).isin(_v10_dep_set)).sum())
            if _v10_dep_set else active_count
        )

    _v10_salary_ready = (salary_available / active_count * 100.0) if active_count else 0.0
    _v10_dept_ready = ((active_count - dept_pending) / active_count * 100.0) if active_count else 0.0
    _v10_att_rows = len(attendance)
    _v10_att_coverage = min(100.0, (_v10_att_rows / active_count * 100.0)) if active_count else 0.0
    _v10_review_rate = (review / max(_v10_att_rows, 1) * 100.0)
    _v10_pay_blockers = int(
        ((payroll["Missing Days"] > 0) | (payroll["HR Review"] > 0)).sum()
    ) if not payroll.empty else 0
    _v10_pay_ready = (
        max(0.0, 100.0 - (_v10_pay_blockers / max(len(payroll), 1) * 100.0))
        if not payroll.empty else 0.0
    )

    _v10_health = max(
        0.0,
        min(
            100.0,
            (_v10_att_coverage * 0.45)
            + (_v10_salary_ready * 0.22)
            + (_v10_dept_ready * 0.18)
            + (_v10_pay_ready * 0.15)
            - min(12.0, _v10_review_rate * 0.8),
        ),
    )
    if _v10_health >= 90:
        _v10_health_word, _v10_health_tone = "Excellent", "good"
    elif _v10_health >= 75:
        _v10_health_word, _v10_health_tone = "Good", "good"
    elif _v10_health >= 55:
        _v10_health_word, _v10_health_tone = "Attention", "warn"
    else:
        _v10_health_word, _v10_health_tone = "Action Required", "danger"

    # Functional top command bar.
    _v10_top1, _v10_top2, _v10_top3 = st.columns([1.45, 1.0, .72], gap="small")
    with _v10_top1:
        st.markdown(
            '<div class="v10-product-line"><b>Smart HRMS</b><span>People · Process · Performance · A Stronger Tomorrow</span></div>',
            unsafe_allow_html=True,
        )
    with _v10_top2:
        _v10_query = st.text_input(
            "Command Search",
            placeholder="Search employee or module...",
            key="v10_home_command_search",
            label_visibility="collapsed",
        )
    with _v10_top3:
        st.markdown(
            f"""
            <div class="v10-profile-mini">
              <span class="v10-profile-avatar">◉</span>
              <span><b>{html.escape(str(_current_user['full_name']))}</b><small>{html.escape(str(_current_role))} · {_v94_notification_total:,} alerts</small></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Command search is real, not decorative.
    if str(_v10_query or "").strip():
        _v10_q = str(_v10_query).strip()
        _v10_ql = _v10_q.lower()
        _v10_alias = {
            "Home": "home dashboard overview command centre",
            "Management": "management executive mis dashboard",
            "Employees": "employee master history employee 360",
            "Attendance": "attendance biometric punch hr review upload monthly",
            "Payroll": "payroll salary wages pf esic deduction net",
            "Contractors": "contractor thekedar vendor payment",
            "Operations": "operations production machine allocation",
            "Reports": "reports export excel pdf mis",
            "AI Tools": "ai assistant intelligence automation insights",
            "Master Centre": "master department machine settings",
            "User Management": "user permission access login role",
        }
        _v10_module_hits = [
            m for m in available_modules
            if _v10_ql in m.lower() or _v10_ql in _v10_alias.get(m, "")
        ][:3]
        _v10_emp_hits = pd.DataFrame()
        if "Employees" in available_modules and len(_v10_q) >= 2:
            _v10_like = f"%{_v10_q}%"
            _v10_sql = """
                SELECT employee_id, employee_name, department, designation, division
                FROM employees
                WHERE status='Active'
                  AND (
                    employee_id ILIKE ? OR employee_name ILIKE ?
                    OR department ILIKE ? OR designation ILIKE ?
                  )
            """
            _v10_params = (_v10_like, _v10_like, _v10_like, _v10_like)
            if global_division != ALL_DIVISIONS:
                _v10_sql += " AND division=?"
                _v10_params += (global_division,)
            _v10_sql += " ORDER BY employee_name, employee_id LIMIT 4"
            try:
                _v10_emp_hits = read_df(_v10_sql, _v10_params)
            except Exception:
                _v10_emp_hits = pd.DataFrame()

        if _v10_module_hits or not _v10_emp_hits.empty:
            with st.container(border=True):
                st.caption("Command Search results")
                _v10_search_cols = st.columns(max(1, min(4, len(_v10_module_hits) + len(_v10_emp_hits))), gap="small")
                _v10_idx = 0
                for _v10_mod in _v10_module_hits:
                    with _v10_search_cols[_v10_idx % len(_v10_search_cols)]:
                        if st.button(f"↗ {_v10_mod}", key=f"v10_cmd_mod_{_v10_idx}_{_v10_mod}", use_container_width=True):
                            st.session_state["_v83_nav_request"] = _v10_mod
                            st.rerun()
                    _v10_idx += 1
                for _, _v10_er in _v10_emp_hits.iterrows():
                    _v10_eid = str(_v10_er["employee_id"])
                    _v10_ename = str(_v10_er["employee_name"])
                    with _v10_search_cols[_v10_idx % len(_v10_search_cols)]:
                        if st.button(f"{_v10_eid} · {_v10_ename}", key=f"v10_cmd_emp_{_v10_eid}", use_container_width=True):
                            st.session_state["v55_open_employee"] = _v10_eid
                            st.session_state["_v83_nav_request"] = "Employees"
                            st.rerun()
                    _v10_idx += 1
        else:
            st.caption("No employee or module matched the command search.")

    # Building / brand hero. Uses the already embedded company HRMS artwork.
    _v10_live_now = datetime.now(IST)
    st.markdown(
        f"""
        <div class="v10-hero" style="background-image:
          linear-gradient(90deg,rgba(4,13,24,.90) 0%,rgba(4,13,24,.46) 48%,rgba(4,13,24,.88) 100%),
          url('{V82_LOGIN_HERO_DATA_URI}');">
          <div class="v10-hero-left">
            <div class="v10-hero-kicker">SUSTAINABLE · STRONGER · TOGETHER</div>
            <h2>People. Packaging.<br><span>Possibilities.</span></h2>
            <p>Reliable Packaging Industries Limited · live workforce intelligence</p>
            <div class="v10-hero-pills">
              <span>🏭 {html.escape(str(global_division))}</span>
              <span>📅 Working Date · {global_work_date.strftime('%d %b %Y')}</span>
              <span>₹ Payroll · {global_payroll_month.strftime('%b %Y')}</span>
              <span class="live"><i></i> LIVE DATABASE</span>
            </div>
          </div>
          <div class="v10-hero-quote">“ SMART PEOPLE<br>BUILD<br>GREAT COMPANIES ”</div>
          <div class="v10-clock-card">
            <small data-v10-date>{_v10_live_now.strftime('%A, %d %b %Y')}</small>
            <b data-v10-clock>{_v10_live_now.strftime('%H:%M:%S')}</b>
            <span>Asia/Kolkata · IST</span>
            <em>24H LIVE</em>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    components.html(
        """
        <script>
        (() => {
          const tick = () => {
            try {
              const d = new Date();
              const time = new Intl.DateTimeFormat("en-GB", {
                timeZone:"Asia/Kolkata", hour:"2-digit", minute:"2-digit",
                second:"2-digit", hour12:false
              }).format(d);
              const date = new Intl.DateTimeFormat("en-GB", {
                timeZone:"Asia/Kolkata", weekday:"long", day:"2-digit",
                month:"short", year:"numeric"
              }).format(d);
              const doc = window.parent.document;
              const t = doc.querySelector("[data-v10-clock]");
              const dt = doc.querySelector("[data-v10-date]");
              if (t) t.textContent = time;
              if (dt) dt.textContent = date;
            } catch(e) {}
          };
          tick();
          setInterval(tick, 1000);
        })();
        </script>
        """,
        height=0,
    )

    # Reference-style KPI rail, driven by live selected-date data.
    _v10_kpi_items = [
        ("👥", "Total Employees", f"{active_count:,}", "Active master", "blue"),
        ("●", "Present", f"{present:,}", f"{(present / active_count * 100):.1f}% of active" if active_count else "No active employees", "green"),
        ("●", "Absent / LWP", f"{absent:,}", "Selected working date", "red"),
        ("◒", "On Leave", f"{on_leave:,}", "CL · SL · EL · Leave", "amber"),
        ("◷", "On Duty (WO)", f"{weekly_off:,}", f"Half day {half_day:,}", "purple"),
        ("◴", "OT Hours", f"{ot_hours:,.2f}", "Selected working date", "cyan"),
    ]
    _v10_kpi_html = "".join(
        f"""
        <div class="v10-kpi {tone}">
          <div class="v10-kpi-icon">{icon}</div>
          <div><small>{html.escape(label)}</small><b>{value}</b><span>{html.escape(sub)}</span></div>
        </div>
        """
        for icon, label, value, sub, tone in _v10_kpi_items
    )
    st.markdown(f'<div class="v10-kpi-grid">{_v10_kpi_html}</div>', unsafe_allow_html=True)

    # 7-day attendance trend.
    _v10_trend_start = global_work_date - timedelta(days=6)
    _v10_trend_sql = """
        SELECT work_date, status, COUNT(*) AS employees
        FROM attendance
        WHERE work_date BETWEEN ? AND ?
    """
    _v10_trend_params = (_v10_trend_start.isoformat(), global_work_date.isoformat())
    if global_division != ALL_DIVISIONS:
        _v10_trend_sql += " AND division=?"
        _v10_trend_params += (global_division,)
    _v10_trend_sql += " GROUP BY work_date, status ORDER BY work_date"
    try:
        _v10_trend_raw = read_df(_v10_trend_sql, _v10_trend_params)
    except Exception:
        _v10_trend_raw = pd.DataFrame()

    if not _v10_trend_raw.empty:
        def _v10_bucket_status(v):
            v = str(v)
            if v == "Present":
                return "Present"
            if v in {"Absent", "LWP"}:
                return "Absent"
            if v in {"CL", "SL", "EL", "Leave", "Half Day"}:
                return "Leave"
            return None
        _v10_trend_raw["Trend"] = _v10_trend_raw["status"].map(_v10_bucket_status)
        _v10_trend_raw = _v10_trend_raw[_v10_trend_raw["Trend"].notna()].copy()
        _v10_trend_raw["work_date"] = pd.to_datetime(_v10_trend_raw["work_date"], errors="coerce")
        _v10_trend = (
            _v10_trend_raw.groupby(["work_date", "Trend"], as_index=False)["employees"].sum()
            if not _v10_trend_raw.empty else pd.DataFrame()
        )
    else:
        _v10_trend = pd.DataFrame()

    # Plant distribution inside the selected scope.
    _v10_div_counts = (
        employees.groupby("division").size().sort_values(ascending=False)
        if not employees.empty else pd.Series(dtype=int)
    )
    _v10_div_items = [(str(k), int(v)) for k, v in _v10_div_counts.items()]
    _v10_total_for_ring = sum(v for _, v in _v10_div_items)
    _v10_ring_colors = ["#3498ff", "#ff7a62", "#f35e9a"]
    if _v10_div_items:
        _v10_stops = []
        _v10_acc = 0.0
        for _v10_i, (_, _v10_n) in enumerate(_v10_div_items[:3]):
            _v10_next = _v10_acc + ((_v10_n / max(_v10_total_for_ring, 1)) * 100.0)
            _v10_stops.append(f"{_v10_ring_colors[_v10_i % 3]} {_v10_acc:.2f}% {_v10_next:.2f}%")
            _v10_acc = _v10_next
        if _v10_acc < 100:
            _v10_stops.append(f"#18314b {_v10_acc:.2f}% 100%")
        _v10_ring_gradient = "conic-gradient(" + ",".join(_v10_stops) + ")"
    else:
        _v10_ring_gradient = "conic-gradient(#18314b 0 100%)"

    _v10_row1, _v10_row2, _v10_row3 = st.columns([.85, 1.35, .95], gap="small")

    with _v10_row1:
        with st.container(border=True):
            st.markdown(
                f"""
                <div class="v10-panel-title"><span>✦ AI WORKFORCE HEALTH SCORE</span><small>Live controls</small></div>
                <div class="v10-health-wrap">
                  <div class="v10-health-ring" style="--v10score:{_v10_health:.1f};">
                    <div><b>{_v10_health:.0f}</b><small>/100</small></div>
                  </div>
                  <div class="v10-health-copy">
                    <small>Overall Status</small>
                    <b class="{_v10_health_tone}">● {_v10_health_word}</b>
                    <span>Attendance coverage {_v10_att_coverage:.1f}%</span>
                    <span>Salary readiness {_v10_salary_ready:.1f}%</span>
                    <span>Payroll readiness {_v10_pay_ready:.1f}%</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if "AI Tools" in available_modules:
                if st.button("View AI Insights →", use_container_width=True, key="v10_health_ai"):
                    st.session_state["_v83_nav_request"] = "AI Tools"
                    st.rerun()

    with _v10_row2:
        with st.container(border=True):
            st.markdown(
                '<div class="v10-panel-title"><span>ATTENDANCE TREND</span><small>Last 7 working dates in source</small></div>',
                unsafe_allow_html=True,
            )
            if _v10_trend.empty:
                st.info("No attendance trend data is available for this period.")
            else:
                _v10_line = (
                    alt.Chart(_v10_trend)
                    .mark_line(point=alt.OverlayMarkDef(size=45), strokeWidth=2.2)
                    .encode(
                        x=alt.X("work_date:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0)),
                        y=alt.Y("employees:Q", title=None),
                        color=alt.Color(
                            "Trend:N",
                            title=None,
                            scale=alt.Scale(
                                domain=["Present", "Absent", "Leave"],
                                range=["#2ed39a", "#ff5d73", "#f5b83d"],
                            ),
                        ),
                        tooltip=[
                            alt.Tooltip("work_date:T", title="Date", format="%d %b %Y"),
                            alt.Tooltip("Trend:N", title="Status"),
                            alt.Tooltip("employees:Q", title="Employees"),
                        ],
                    )
                    .properties(height=205)
                    .configure_view(strokeOpacity=0)
                    .configure_axis(
                        gridColor="#17324d", gridOpacity=.45, domain=False,
                        labelColor="#89a0b6", tickColor="#284968",
                    )
                    .configure_legend(labelColor="#b7c8d9", symbolType="stroke")
                )
                st.altair_chart(_v10_line, use_container_width=True)

    with _v10_row3:
        with st.container(border=True):
            st.markdown(
                f'<div class="v10-panel-title"><span>PLANT WISE EMPLOYEES</span><small>Total · {_v10_total_for_ring:,}</small></div>',
                unsafe_allow_html=True,
            )
            _v10_plant_rows = ""
            for _v10_i, (_v10_div, _v10_n) in enumerate(_v10_div_items[:3]):
                _v10_pct = (_v10_n / max(_v10_total_for_ring, 1) * 100.0)
                _v10_plant_rows += (
                    f'<div class="v10-plant-row"><i style="background:{_v10_ring_colors[_v10_i % 3]}"></i>'
                    f'<span>{html.escape(_v10_div)}</span><b>{_v10_n:,}</b><small>{_v10_pct:.1f}%</small></div>'
                )
            if not _v10_plant_rows:
                _v10_plant_rows = '<div class="v10-empty">No active employee data in this scope.</div>'
            st.markdown(
                f"""
                <div class="v10-plant-wrap">
                  <div class="v10-plant-list">{_v10_plant_rows}</div>
                  <div class="v10-plant-ring" style="background:{_v10_ring_gradient};">
                    <div><b>{_v10_total_for_ring:,}</b><small>Employees</small></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # AI priority alerts.
    _v10_alerts = []
    if _v94_upload_pending:
        _v10_alerts.append(("Attendance Not Loaded", f"No source rows for {global_work_date.strftime('%d %b %Y')}", "High", "Attendance"))
    if _v94_missing:
        _v10_alerts.append(("Missing Attendance", f"{_v94_missing:,} active employee(s) need source verification", "High", "Attendance"))
    if _v94_review:
        _v10_alerts.append(("HR Review Pending", f"{_v94_review:,} attendance review row(s)", "High", "Attendance"))
    if _v94_master_pending:
        _v10_alerts.append(("Employee Master Incomplete", f"{_v94_master_pending:,} record(s) pending", "Medium", "Employees"))
    if _v94_payroll_pending and "Payroll" in available_modules:
        _v10_alerts.append(("Payroll Not Finalized", f"{global_payroll_month.strftime('%b %Y')} is not fully closed", "Medium", "Payroll"))
    if salary_missing:
        _v10_alerts.append(("Salary Master Gap", f"{salary_missing:,} employee(s) have no salary value", "Medium", "Employees"))
    if not _v10_alerts:
        _v10_alerts.append(("All Clear", "No priority HR exception in the selected context", "Low", "Home"))

    # Real recent DB activity: attendance, payroll, contractor transactions.
    _v10_activity = []
    try:
        _v10_a_sql = """
            SELECT division, MAX(updated_at) AS event_time, MAX(work_date) AS ref
            FROM attendance WHERE updated_at IS NOT NULL
        """
        _v10_a_params = ()
        if global_division != ALL_DIVISIONS:
            _v10_a_sql += " AND division=?"
            _v10_a_params = (global_division,)
        _v10_a_sql += " GROUP BY division ORDER BY MAX(updated_at) DESC LIMIT 2"
        _v10_a = read_df(_v10_a_sql, _v10_a_params)
        for _, _r in _v10_a.iterrows():
            _v10_activity.append(("Attendance database updated", str(_r["division"]), _r["event_time"], "◉"))
    except Exception:
        pass
    try:
        _v10_p_sql = """
            SELECT division, MAX(finalized_at) AS event_time, MAX(payroll_month) AS ref
            FROM payroll_records WHERE finalized_at IS NOT NULL
        """
        _v10_p_params = ()
        if global_division != ALL_DIVISIONS:
            _v10_p_sql += " AND division=?"
            _v10_p_params = (global_division,)
        _v10_p_sql += " GROUP BY division ORDER BY MAX(finalized_at) DESC LIMIT 2"
        _v10_p = read_df(_v10_p_sql, _v10_p_params)
        for _, _r in _v10_p.iterrows():
            _v10_activity.append(("Payroll finalized", str(_r["division"]), _r["event_time"], "₹"))
    except Exception:
        pass
    try:
        _v10_c_sql = """
            SELECT division, MAX(created_at) AS event_time
            FROM contractor_work_entries WHERE created_at IS NOT NULL
        """
        _v10_c_params = ()
        if global_division != ALL_DIVISIONS:
            _v10_c_sql += " AND division=?"
            _v10_c_params = (global_division,)
        _v10_c_sql += " GROUP BY division ORDER BY MAX(created_at) DESC LIMIT 2"
        _v10_c = read_df(_v10_c_sql, _v10_c_params)
        for _, _r in _v10_c.iterrows():
            _v10_activity.append(("Contractor work entry", str(_r["division"]), _r["event_time"], "▣"))
    except Exception:
        pass

    def _v10_activity_key(item):
        try:
            return pd.Timestamp(item[2]).value
        except Exception:
            return 0
    _v10_activity = sorted(_v10_activity, key=_v10_activity_key, reverse=True)[:5]

    _v10_lower1, _v10_lower2, _v10_lower3 = st.columns([1.0, 1.0, 1.05], gap="small")

    with _v10_lower1:
        with st.container(border=True):
            st.markdown(
                f'<div class="v10-panel-title"><span>✦ AI PRIORITY ALERTS</span><small>View all · {len(_v10_alerts)}</small></div>',
                unsafe_allow_html=True,
            )
            _v10_alert_html = ""
            for _v10_i, (_v10_title, _v10_detail, _v10_level, _v10_target) in enumerate(_v10_alerts[:5]):
                _v10_alert_html += (
                    f'<div class="v10-alert-row"><span class="v10-alert-icon">{"!" if _v10_level=="High" else "•"}</span>'
                    f'<div><b>{html.escape(_v10_title)}</b><small>{html.escape(_v10_detail)}</small></div>'
                    f'<em class="{_v10_level.lower()}">{_v10_level}</em></div>'
                )
            st.markdown(_v10_alert_html, unsafe_allow_html=True)
            _v10_first_target = next((x[3] for x in _v10_alerts if x[3] in available_modules and x[3] != "Home"), None)
            if _v10_first_target and st.button(f"Open {_v10_first_target} →", key="v10_alert_open", use_container_width=True):
                st.session_state["_v83_nav_request"] = _v10_first_target
                st.rerun()

    with _v10_lower2:
        with st.container(border=True):
            st.markdown(
                '<div class="v10-panel-title"><span>⌖ OUR LOCATIONS</span><small><i class="v10-live-dot"></i> Live master</small></div>',
                unsafe_allow_html=True,
            )
            _v10_location_rows = ""
            for _v10_i, _v10_loc in enumerate(DIVISIONS):
                _v10_n = int(_v10_div_counts.get(_v10_loc, 0)) if not _v10_div_counts.empty else 0
                _v10_location_rows += (
                    f'<div class="v10-location-row"><i class="loc{_v10_i+1}"></i>'
                    f'<div><b>{html.escape(_v10_loc)}</b><small>{_v10_n:,} active in selected scope</small></div>'
                    f'<span>{"ACTIVE" if _v10_n else "—"}</span></div>'
                )
            st.markdown(
                f"""
                <div class="v10-location-card">
                  <div class="v10-india-orbit">🇮🇳<span>3 LOCATIONS</span><i></i><i></i><i></i></div>
                  <div class="v10-location-list">{_v10_location_rows}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with _v10_lower3:
        with st.container(border=True):
            st.markdown(
                '<div class="v10-panel-title"><span>RECENT ACTIVITY</span><small>Database timestamps · 24H</small></div>',
                unsafe_allow_html=True,
            )
            if not _v10_activity:
                st.info("No recent transaction timestamp is available in this scope.")
            else:
                _v10_activity_html = ""
                for _v10_title, _v10_div, _v10_ts, _v10_icon in _v10_activity:
                    try:
                        _v10_time_text = pd.to_datetime(_v10_ts).strftime("%d %b · %H:%M")
                    except Exception:
                        _v10_time_text = "—"
                    _v10_activity_html += (
                        f'<div class="v10-activity-row"><span>{_v10_icon}</span>'
                        f'<div><b>{html.escape(_v10_title)}</b><small>{html.escape(_v10_div)}</small></div>'
                        f'<em>{_v10_time_text}</em></div>'
                    )
                st.markdown(_v10_activity_html, unsafe_allow_html=True)

    # Reference-style bottom utility rail, fully functional.
    _v10_u1, _v10_u2, _v10_u3, _v10_u4, _v10_u5 = st.columns(5, gap="small")
    _v10_utils = [
        (_v10_u1, "✦", "AI Assistant", "Ask anything about HR data", "AI Tools", "v10_util_ai"),
        (_v10_u2, "⚙", "Automation Hub", "Readiness & repetitive-work routing", "AI Tools", "v10_util_auto"),
        (_v10_u3, "▥", "Smart Reports", "Interactive MIS & insights", "Reports", "v10_util_reports"),
        (_v10_u4, "⇩", "Data Export", "Excel / PDF / report exports", "Reports", "v10_util_export"),
        (_v10_u5, "♥", "System Health", "Database and HR controls", "Management", "v10_util_health"),
    ]
    for _v10_col, _v10_icon, _v10_title, _v10_sub, _v10_target, _v10_key in _v10_utils:
        with _v10_col:
            st.markdown(
                f'<div class="v10-util-label"><span>{_v10_icon}</span><div><b>{_v10_title}</b><small>{_v10_sub}</small></div></div>',
                unsafe_allow_html=True,
            )
            if _v10_target in available_modules and st.button("Open", key=_v10_key, use_container_width=True):
                st.session_state["_v83_nav_request"] = _v10_target
                st.rerun()

    st.markdown(
        '<div class="v10-home-footer"><span>🌿 Reliable Packaging Industries Limited · Smart Manufacturing · Workforce · Payroll · Operations</span>'
        '<span>Built in India 🇮🇳 · Created by Sourav Majumder · Together We Build a Better Tomorrow</span></div>',
        unsafe_allow_html=True,
    )

''' + mgmt_marker

s = s[:home_start] + home + s[home_end + len(mgmt_marker):]

# V10 home + sidebar CSS appended last so it wins over older presentation layers.
s += r'''

# ============================================================
# V10.0 LIVE REFERENCE DASHBOARD — FINAL VISUAL LAYER
# ============================================================
st.markdown("""
<style>
/* Full command-centre home */
body:has(.v10-live-home-marker) header[data-testid="stHeader"]{
  height:0!important;min-height:0!important;background:transparent!important;
}
body:has(.v10-live-home-marker) .block-container{
  padding-top:.45rem!important;
  padding-bottom:1rem!important;
  max-width:1900px!important;
}

/* Logged-in sidebar brand */
.v10-sidebrand{
  display:grid;grid-template-columns:48px minmax(0,1fr);gap:10px;align-items:center;
  margin:5px 0 13px;padding:10px 8px 13px;
  border-bottom:1px solid rgba(79,134,191,.18);
}
.v10-sidebrand img{
  width:45px;height:52px;object-fit:contain;filter:drop-shadow(0 0 12px rgba(255,83,49,.20));
}
.v10-sidebrand-copy b,.v10-sidebrand-copy strong{display:block;line-height:1.05}
.v10-sidebrand-copy b{font-size:11px;color:#fff;letter-spacing:.4px}
.v10-sidebrand-copy strong{font-size:11px;color:#ff633f;margin-top:3px}
.v10-sidebrand-copy small{display:block;margin-top:8px;color:#7fd8ff;font-size:7.8px;font-weight:850;letter-spacing:.75px}
.v10-sidebrand-copy .v8-live-dot{display:inline-block}

/* Sidebar closer to the reference control rail */
section[data-testid="stSidebar"]{
  width:245px!important;min-width:245px!important;
  background:
    radial-gradient(circle at 0 0,rgba(38,112,190,.08),transparent 22%),
    linear-gradient(180deg,#06111e 0%,#071321 55%,#06101b 100%)!important;
  border-right:1px solid rgba(58,112,168,.23)!important;
}
section[data-testid="stSidebar"]>div{width:245px!important}
section[data-testid="stSidebar"] div[role="radiogroup"]>label{
  border-radius:9px!important;margin:2px 0!important;min-height:39px!important;
}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:has(input:checked){
  background:linear-gradient(90deg,rgba(22,106,218,.74),rgba(16,77,145,.72))!important;
  box-shadow:0 0 18px rgba(41,139,255,.16),inset 0 0 0 1px rgba(96,183,255,.30)!important;
}

/* Internal product bar */
.v10-product-line{
  height:41px;display:flex;align-items:center;gap:12px;padding:0 4px;
  color:#a8bfd6;font-size:11px;
}
.v10-product-line b{
  color:#73cbff;font-size:12px;padding-right:11px;border-right:1px solid rgba(99,153,208,.32);
}
.v10-product-line span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.v10-profile-mini{
  height:41px;display:flex;align-items:center;justify-content:flex-end;gap:8px;
  padding:0 5px;color:#eaf5ff;
}
.v10-profile-avatar{
  width:31px;height:31px;border-radius:50%;display:grid;place-items:center;
  background:linear-gradient(145deg,#315dd6,#6b55e5);
  border:1px solid rgba(133,188,255,.35);box-shadow:0 0 16px rgba(61,124,255,.15)
}
.v10-profile-mini b,.v10-profile-mini small{display:block;line-height:1.15}
.v10-profile-mini b{font-size:10px}.v10-profile-mini small{font-size:8px;color:#8fa7bc;margin-top:3px}

/* Compact top search */
body:has(.v10-live-home-marker) [data-testid="stTextInput"] input{
  min-height:39px!important;border-radius:10px!important;
  background:#0a1a2c!important;border:1px solid #21405f!important;
}

/* Hero */
.v10-hero{
  min-height:205px;border:1px solid rgba(52,151,245,.30);border-radius:17px;
  background-size:cover;background-position:center 37%;
  position:relative;overflow:hidden;margin:5px 0 10px;
  box-shadow:0 18px 44px rgba(0,0,0,.22),inset 0 0 70px rgba(0,11,25,.28);
}
.v10-hero:before{
  content:"";position:absolute;inset:0;pointer-events:none;
  background:
    linear-gradient(180deg,rgba(60,189,255,.05),transparent 32%),
    linear-gradient(90deg,rgba(4,12,22,.28),transparent 50%,rgba(4,12,22,.20));
}
.v10-hero:after{
  content:"";position:absolute;left:-18%;top:0;width:18%;height:1px;
  background:linear-gradient(90deg,transparent,#61d5ff,transparent);
  box-shadow:0 0 16px #4ccaff;animation:v10HeroScan 7s linear infinite;
}
@keyframes v10HeroScan{to{left:118%}}
.v10-hero-left{position:absolute;z-index:2;left:24px;top:23px;max-width:650px}
.v10-hero-kicker{font-size:9px;font-weight:950;letter-spacing:1.6px;color:#d7f1ff}
.v10-hero h2{
  margin:8px 0 3px!important;font-size:29px!important;line-height:1.02!important;
  text-shadow:0 4px 18px rgba(0,0,0,.45)
}
.v10-hero h2 span{color:#70d2ff}
.v10-hero p{font-size:10px!important;color:#b6c9dc!important;margin:7px 0!important}
.v10-hero-pills{display:flex;gap:6px;flex-wrap:wrap;margin-top:11px}
.v10-hero-pills span{
  padding:5px 8px;border-radius:999px;background:rgba(5,18,32,.72);
  border:1px solid rgba(88,157,221,.22);color:#a9bed1;font-size:8px;font-weight:700;
  backdrop-filter:blur(8px)
}
.v10-hero-pills .live{color:#7ee8c2}.v10-hero-pills .live i{
  display:inline-block;width:6px;height:6px;border-radius:50%;background:#26d79b;margin-right:5px;
  box-shadow:0 0 10px #26d79b;animation:v96PulseDot 1.8s infinite;
}
.v10-hero-quote{
  position:absolute;z-index:2;right:230px;top:28px;text-align:center;
  font-size:10px;line-height:1.55;letter-spacing:1.5px;color:#b7c9db;
  text-shadow:0 2px 12px rgba(0,0,0,.55)
}
.v10-clock-card{
  position:absolute;z-index:2;right:14px;top:13px;width:185px;min-height:150px;
  border:1px solid rgba(71,186,255,.52);border-radius:14px;padding:13px 14px;
  background:linear-gradient(145deg,rgba(9,29,50,.86),rgba(7,18,32,.82));
  backdrop-filter:blur(15px);box-shadow:0 0 22px rgba(34,147,255,.12)
}
.v10-clock-card small,.v10-clock-card span,.v10-clock-card em{display:block}
.v10-clock-card small{font-size:9px;color:#c4d6e8}
.v10-clock-card b{display:block;font-size:27px;color:#9fd2ff;letter-spacing:1.5px;margin-top:6px}
.v10-clock-card span{font-size:8px;color:#8ea6bc;margin-top:4px}
.v10-clock-card em{
  margin-top:16px;font-style:normal;font-size:8px;font-weight:900;letter-spacing:1px;color:#79e6c0
}

/* KPI rail */
.v10-kpi-grid{
  display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin:8px 0 10px;
}
.v10-kpi{
  min-height:78px;display:flex;align-items:center;gap:10px;padding:11px 12px;
  border-radius:13px;border:1px solid rgba(54,132,206,.38);
  background:linear-gradient(145deg,#0c1c2d,#091625);
  box-shadow:0 10px 25px rgba(0,0,0,.14);position:relative;overflow:hidden
}
.v10-kpi:after{content:"";position:absolute;inset:auto 0 0;height:1px;background:linear-gradient(90deg,transparent,rgba(83,194,255,.40),transparent)}
.v10-kpi-icon{
  width:40px;height:40px;border-radius:11px;display:grid;place-items:center;font-size:16px;
  background:rgba(39,119,225,.18);border:1px solid rgba(72,158,255,.24)
}
.v10-kpi.green .v10-kpi-icon{background:rgba(34,197,94,.15);color:#51e19a}
.v10-kpi.red .v10-kpi-icon{background:rgba(239,83,80,.14);color:#ff7180}
.v10-kpi.amber .v10-kpi-icon{background:rgba(245,184,61,.14);color:#ffc861}
.v10-kpi.purple .v10-kpi-icon{background:rgba(155,81,224,.16);color:#ba82ff}
.v10-kpi.cyan .v10-kpi-icon{background:rgba(45,203,230,.14);color:#62ddff}
.v10-kpi small,.v10-kpi b,.v10-kpi span{display:block}
.v10-kpi small{font-size:8.5px;color:#b4c7d9}.v10-kpi b{font-size:20px;color:#fff;margin-top:1px}
.v10-kpi span{font-size:7.5px;color:#7691aa;margin-top:2px}

/* Main dashboard panels */
body:has(.v10-live-home-marker) div[data-testid="stVerticalBlockBorderWrapper"]{
  background:linear-gradient(155deg,#0a1928,#08131f)!important;
  border:1px solid rgba(52,124,190,.34)!important;
  border-radius:14px!important;
  box-shadow:0 14px 32px rgba(0,0,0,.16)!important;
}
.v10-panel-title{
  display:flex;justify-content:space-between;align-items:center;margin:-2px 0 8px;
  color:#d9f2ff;font-size:9.5px;font-weight:900;letter-spacing:.4px
}
.v10-panel-title small{font-size:7.5px;color:#7290aa;font-weight:650}
.v10-health-wrap{display:flex;align-items:center;gap:16px;min-height:190px;padding:5px}
.v10-health-ring{
  --v10p:calc(var(--v10score)*1%);width:124px;height:124px;border-radius:50%;
  display:grid;place-items:center;position:relative;flex:0 0 auto;
  background:conic-gradient(#2ed39a 0 var(--v10p),#17324a var(--v10p) 100%);
  box-shadow:0 0 28px rgba(46,211,154,.13)
}
.v10-health-ring:before{
  content:"";position:absolute;inset:10px;border-radius:50%;background:#091726;border:1px solid rgba(77,139,199,.20)
}
.v10-health-ring div{position:relative;z-index:1;text-align:center}.v10-health-ring b{font-size:29px;color:#fff}.v10-health-ring small{color:#7d9ab2}
.v10-health-copy small,.v10-health-copy b,.v10-health-copy span{display:block}
.v10-health-copy small{font-size:8px;color:#8da6bd}.v10-health-copy b{font-size:15px;margin:4px 0 8px}.v10-health-copy b.good{color:#2ed39a}.v10-health-copy b.warn{color:#f5b83d}.v10-health-copy b.danger{color:#ff6375}
.v10-health-copy span{font-size:8px;color:#8aa2b8;margin:4px 0}

.v10-plant-wrap{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:208px}
.v10-plant-list{flex:1;min-width:0}
.v10-plant-row{
  display:grid;grid-template-columns:8px minmax(0,1fr) auto auto;gap:7px;align-items:center;
  padding:7px 0;border-bottom:1px solid rgba(57,102,148,.14)
}
.v10-plant-row i{width:7px;height:7px;border-radius:50%}
.v10-plant-row span{font-size:8.5px;color:#c2d2e1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.v10-plant-row b{font-size:9px;color:#fff}.v10-plant-row small{font-size:7px;color:#6f8ca5}
.v10-plant-ring{
  width:116px;height:116px;border-radius:50%;display:grid;place-items:center;position:relative;flex:0 0 auto
}
.v10-plant-ring:before{content:"";position:absolute;inset:23px;border-radius:50%;background:#091625;border:1px solid rgba(73,129,186,.20)}
.v10-plant-ring div{position:relative;z-index:1;text-align:center}.v10-plant-ring b{display:block;font-size:18px;color:#fff}.v10-plant-ring small{font-size:7px;color:#7f9bb4}
.v10-empty{font-size:9px;color:#7890a8}

/* Alerts */
.v10-alert-row,.v10-activity-row{
  display:grid;align-items:center;gap:9px;padding:8px 5px;border-bottom:1px solid rgba(55,101,146,.14)
}
.v10-alert-row{grid-template-columns:27px minmax(0,1fr) 55px}
.v10-alert-icon{
  width:25px;height:25px;border-radius:8px;display:grid;place-items:center;
  background:rgba(239,83,80,.14);color:#ff7784;font-weight:900;font-size:10px
}
.v10-alert-row b,.v10-alert-row small{display:block}.v10-alert-row b{font-size:8.7px;color:#eaf4fc}.v10-alert-row small{font-size:7.2px;color:#7f97ad;margin-top:2px}
.v10-alert-row em{font-style:normal;text-align:center;border-radius:6px;padding:4px 5px;font-size:7px;font-weight:900}
.v10-alert-row em.high{background:rgba(239,83,80,.12);color:#ff7381}.v10-alert-row em.medium{background:rgba(245,184,61,.12);color:#ffc95f}.v10-alert-row em.low{background:rgba(34,197,94,.12);color:#64dda0}

/* Locations */
.v10-location-card{display:grid;grid-template-columns:.72fr 1.28fr;gap:14px;align-items:center;min-height:202px}
.v10-india-orbit{
  min-height:150px;border-radius:15px;display:flex;align-items:center;justify-content:center;flex-direction:column;
  font-size:53px;position:relative;
  background:radial-gradient(circle,rgba(40,126,210,.17),rgba(5,18,30,.15) 58%,transparent 60%);
  border:1px solid rgba(54,126,192,.16)
}
.v10-india-orbit span{font-size:7px;font-weight:900;letter-spacing:1.2px;color:#7fcdf7;margin-top:3px}
.v10-india-orbit i{position:absolute;width:7px;height:7px;border-radius:50%;box-shadow:0 0 12px currentColor;animation:v96PulseDot 1.8s infinite}
.v10-india-orbit i:nth-of-type(1){left:53%;top:42%;background:#ff5969;color:#ff5969}
.v10-india-orbit i:nth-of-type(2){left:45%;top:54%;background:#2fd6ff;color:#2fd6ff;animation-delay:.3s}
.v10-india-orbit i:nth-of-type(3){left:49%;top:65%;background:#27d89d;color:#27d89d;animation-delay:.6s}
.v10-location-row{
  display:grid;grid-template-columns:8px minmax(0,1fr) auto;gap:8px;align-items:center;padding:8px 0;
  border-bottom:1px solid rgba(55,101,146,.15)
}
.v10-location-row>i{width:7px;height:7px;border-radius:50%}.v10-location-row>i.loc1{background:#2ed39a}.v10-location-row>i.loc2{background:#3498ff}.v10-location-row>i.loc3{background:#ff665f}
.v10-location-row b,.v10-location-row small{display:block}.v10-location-row b{font-size:8.5px;color:#e8f2fb}.v10-location-row small{font-size:7px;color:#7790a7}
.v10-location-row span{font-size:6.7px;color:#5ee3ad;font-weight:900}

/* Activity */
.v10-activity-row{grid-template-columns:28px minmax(0,1fr) 78px}
.v10-activity-row>span{
  width:25px;height:25px;border-radius:8px;display:grid;place-items:center;
  background:rgba(34,197,154,.12);color:#5fe0b2;font-size:10px
}
.v10-activity-row b,.v10-activity-row small{display:block}.v10-activity-row b{font-size:8.7px;color:#e7f1fa}.v10-activity-row small{font-size:7px;color:#7890a7}
.v10-activity-row em{font-style:normal;font-size:7px;color:#7890a7;text-align:right}

/* Bottom utility rail */
.v10-util-label{
  min-height:58px;display:flex;align-items:center;gap:9px;padding:8px 10px;
  border:1px solid rgba(52,120,188,.25);border-radius:11px;
  background:linear-gradient(145deg,#0b1928,#081522)
}
.v10-util-label>span{
  width:31px;height:31px;border-radius:9px;display:grid;place-items:center;
  background:linear-gradient(145deg,rgba(73,75,216,.35),rgba(32,118,202,.24));color:#a3b8ff;font-size:13px
}
.v10-util-label b,.v10-util-label small{display:block}.v10-util-label b{font-size:8.5px;color:#eaf3fc}.v10-util-label small{font-size:6.8px;color:#758ea5;margin-top:2px}

.v10-home-footer{
  display:flex;justify-content:space-between;align-items:center;gap:15px;
  margin-top:12px;padding:10px 3px;border-top:1px solid rgba(54,100,146,.22);
  color:#778fa6;font-size:7.5px
}

/* Altair inside V10 dashboard */
body:has(.v10-live-home-marker) [data-testid="stVegaLiteChart"]{
  background:transparent!important;
}

/* Keep all rows useful on typical laptop/desktop widths */
@media(max-width:1450px){
  .v10-kpi-grid{grid-template-columns:repeat(3,1fr)}
  .v10-hero-quote{display:none}
}
@media(max-width:1050px){
  .v10-kpi-grid{grid-template-columns:repeat(2,1fr)}
  .v10-clock-card{width:165px}
  .v10-hero-left{max-width:520px}
}
@media(max-width:760px){
  .v10-kpi-grid{grid-template-columns:1fr}
  .v10-clock-card{position:relative;right:auto;top:auto;margin:150px 12px 12px;width:auto}
  .v10-hero{min-height:340px}
  .v10-home-footer{display:block}
  section[data-testid="stSidebar"]{width:220px!important;min-width:220px!important}
  section[data-testid="stSidebar"]>div{width:220px!important}
}
</style>
""", unsafe_allow_html=True)
'''

p.write_text(s, encoding="utf-8")
print("Applied V10 live reference dashboard")
