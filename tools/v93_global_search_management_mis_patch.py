from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

# ------------------------------------------------------------
# V9.3 GLOBAL SEARCH
# ------------------------------------------------------------
if '# V9.3 GLOBAL SEARCH' not in text:
    anchor = '''global_payroll_month = st.sidebar.selectbox(
    "Payroll Month", _month_opts,
    index=next(
        (i for i,d in enumerate(_month_opts)
         if d.year==date.today().year and d.month==date.today().month),
        0
    ),
    format_func=lambda d:d.strftime("%b %Y"),
    key="v5_global_payroll_month",
)

'''
    insert = '''global_payroll_month = st.sidebar.selectbox(
    "Payroll Month", _month_opts,
    index=next(
        (i for i,d in enumerate(_month_opts)
         if d.year==date.today().year and d.month==date.today().month),
        0
    ),
    format_func=lambda d:d.strftime("%b %Y"),
    key="v5_global_payroll_month",
)

# V9.3 GLOBAL SEARCH
# Fast read-only search across modules and the active Employee Master.
st.sidebar.markdown('<div class="v5-sidebar-label">Global Search</div>', unsafe_allow_html=True)
_v93_search = st.sidebar.text_input(
    "Global Search",
    placeholder="Employee ID, name, report, module...",
    key="v93_global_search",
    label_visibility="collapsed",
)
_v93_search_q = str(_v93_search or "").strip()
if len(_v93_search_q) >= 2:
    _v93_q_lower = _v93_search_q.lower()
    _v93_aliases = {
        "Home": "home dashboard start overview",
        "Management": "management executive mis dashboard kpi overview",
        "Employees": "employee staff person directory history employee 360",
        "Attendance": "attendance biometric punch hr review daily register monthly summary",
        "Payroll": "payroll salary pf esic wages deduction net payable",
        "Contractors": "contractor thekedar vendor payment work cost",
        "Operations": "operations production machine manpower allocation target waste",
        "Reports": "reports mis export summary analytics report",
        "AI Tools": "ai tools analysis smart assistant insight",
        "Master Centre": "master centre employee master department machine settings",
        "User Management": "user management login permission access role",
    }
    _v93_module_hits = [
        _m for _m in available_modules
        if _v93_q_lower in _m.lower()
        or _v93_q_lower in _v93_aliases.get(_m, "")
    ]
    if _v93_module_hits:
        st.sidebar.caption("Quick navigation")
        for _v93_module in _v93_module_hits[:4]:
            if st.sidebar.button(
                f"↗ {_v93_module}",
                key=f"v93_search_module_{_v93_module}",
                use_container_width=True,
            ):
                st.session_state["_v83_nav_request"] = _v93_module
                st.rerun()

    if "Employees" in available_modules:
        _v93_like = f"%{_v93_search_q}%"
        _v93_emp_sql = """
            SELECT employee_id, employee_name, department, designation, division
            FROM employees
            WHERE status='Active'
              AND (
                    employee_id ILIKE ? OR employee_name ILIKE ?
                    OR department ILIKE ? OR designation ILIKE ?
                  )
        """
        _v93_emp_params = (_v93_like, _v93_like, _v93_like, _v93_like)
        if global_division != ALL_DIVISIONS:
            _v93_emp_sql += " AND division=?"
            _v93_emp_params += (global_division,)
        _v93_emp_sql += " ORDER BY employee_name, employee_id LIMIT 6"
        try:
            _v93_emp_hits = read_df(_v93_emp_sql, _v93_emp_params)
        except Exception:
            _v93_emp_hits = pd.DataFrame()
        if not _v93_emp_hits.empty:
            st.sidebar.caption("Employees")
            for _, _v93_emp in _v93_emp_hits.iterrows():
                _v93_eid = str(_v93_emp.get("employee_id", "")).strip()
                _v93_ename = str(_v93_emp.get("employee_name", "")).strip()
                if st.sidebar.button(
                    f"{_v93_eid} · {_v93_ename}",
                    key=f"v93_search_emp_{_v93_eid}",
                    use_container_width=True,
                ):
                    st.session_state["v55_open_employee"] = _v93_eid
                    st.session_state["_v83_nav_request"] = "Employees"
                    st.rerun()
        elif not _v93_module_hits:
            st.sidebar.caption("No active employee or module matched this search.")

'''
    if anchor not in text:
        raise SystemExit('Global search anchor not found')
    text = text.replace(anchor, insert, 1)

# ------------------------------------------------------------
# V9.3 MANAGEMENT MIS CENTRE
# ------------------------------------------------------------
if '# V9.3 MANAGEMENT MIS CENTRE' not in text:
    anchor = '''    contractor = contractor_month_summary(global_payroll_month)
    if global_division not in (ALL_DIVISIONS,"Greater Noida Plant"):
        contractor = contractor.iloc[0:0]
'''
    insert = '''    contractor = contractor_month_summary(global_payroll_month)
    if global_division not in (ALL_DIVISIONS,"Greater Noida Plant"):
        contractor = contractor.iloc[0:0]

    # V9.3 MANAGEMENT MIS CENTRE
    # A modern report hub inspired by mature ERP navigation patterns, while
    # keeping Reliable HRMS modules and permissions as the source of truth.
    st.markdown("### Management MIS Centre")
    st.caption(
        "One-click management access to workforce, payroll, contractor, production and analytical views. "
        "The selected Division, Working Date and Payroll Month remain your live context."
    )

    def _v93_mis_card(_icon, _title, _subtitle, _module, _key):
        st.markdown(
            f"""
            <div style="min-height:118px;border:1px solid #22344a;border-radius:16px;"
                 "padding:16px;background:linear-gradient(145deg,#0c1725,#101f31);margin-bottom:8px;">
                <div style="font-size:22px;margin-bottom:8px;">{_icon}</div>
                <div style="font-size:15px;font-weight:800;color:#f5f8fc;">{html.escape(_title)}</div>
                <div style="font-size:11px;color:#8fa4ba;margin-top:5px;line-height:1.35;">{html.escape(_subtitle)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if _module in available_modules:
            if st.button(f"Open {_title}", key=_key, use_container_width=True):
                st.session_state["_v83_nav_request"] = _module
                st.session_state["v93_last_mis"] = _title
                st.rerun()
        else:
            st.caption("Access restricted for this user role.")

    _mis1, _mis2, _mis3, _mis4 = st.columns(4)
    with _mis1:
        _v93_mis_card("◷", "Daily Attendance MIS", "Daily register, present/absent, WO, half day and HR exceptions.", "Attendance", "v93_mis_daily_att")
    with _mis2:
        _v93_mis_card("▦", "Monthly Attendance MIS", "Monthly attendance pattern, missing punches and employee history.", "Attendance", "v93_mis_month_att")
    with _mis3:
        _v93_mis_card("₹", "Payroll Cost MIS", "Salary, paid days, OT, deductions, PF/ESIC and net payable.", "Payroll", "v93_mis_payroll")
    with _mis4:
        _v93_mis_card("👥", "Employee 360", "Open employee history, master details, attendance and salary context.", "Employees", "v93_mis_emp360")

    _mis5, _mis6, _mis7, _mis8 = st.columns(4)
    with _mis5:
        _v93_mis_card("🏗", "Operations MIS", "Production, machine manpower, targets, waste and operational performance.", "Operations", "v93_mis_ops")
    with _mis6:
        _v93_mis_card("🧾", "Contractor Cost MIS", "Vendor/thekedar work, quantity, rate and contractor cost visibility.", "Contractors", "v93_mis_contractor")
    with _mis7:
        _v93_mis_card("▤", "Executive Reports", "Management reports, exports and consolidated summaries.", "Reports", "v93_mis_reports")
    with _mis8:
        _v93_mis_card("✦", "AI Management Insights", "Use AI-assisted analysis on workforce and operational questions.", "AI Tools", "v93_mis_ai")

    st.markdown("---")
'''
    if anchor not in text:
        raise SystemExit('Management MIS anchor not found')
    text = text.replace(anchor, insert, 1)

p.write_text(text, encoding='utf-8')
