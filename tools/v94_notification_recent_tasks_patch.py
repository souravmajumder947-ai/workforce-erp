from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

anchor = '''st.sidebar.markdown(
    f"""
    <div class="v8-user-card">'''

insert = r'''# ============================================================
# V9.4 — NOTIFICATION CENTRE + RECENT MENU + TASK MONITORING
# Read-only operational intelligence. No attendance/master/payroll rows are changed here.
# ============================================================

def _v94_scalar(sql, params=()):
    try:
        _df = read_df(sql, params)
        if _df.empty:
            return 0
        return int(pd.to_numeric(_df.iloc[0, 0], errors="coerce") or 0)
    except Exception:
        return 0

# Remember recently visited modules for this signed-in browser session.
_v94_recent = list(st.session_state.get("v94_recent_modules", []))
if not _v94_recent or _v94_recent[0] != page:
    _v94_recent = [page] + [m for m in _v94_recent if m != page]
    st.session_state["v94_recent_modules"] = _v94_recent[:6]

_v94_month_start = global_work_date.replace(day=1)
_v94_emp_clause = "" if global_division == ALL_DIVISIONS else " AND e.division=?"
_v94_att_clause = "" if global_division == ALL_DIVISIONS else " AND a.division=?"
_v94_plain_clause = "" if global_division == ALL_DIVISIONS else " AND division=?"
_v94_div_params = () if global_division == ALL_DIVISIONS else (global_division,)

_v94_active = _v94_scalar(
    "SELECT COUNT(*) FROM employees e WHERE e.status='Active'" + _v94_emp_clause,
    _v94_div_params,
)
_v94_att_records = _v94_scalar(
    "SELECT COUNT(*) FROM attendance a WHERE a.work_date=?" + _v94_att_clause,
    (global_work_date,) + _v94_div_params,
)
_v94_review = _v94_scalar(
    "SELECT COUNT(*) FROM attendance a WHERE a.review_required=TRUE AND a.work_date BETWEEN ? AND ?" + _v94_att_clause,
    (_v94_month_start, global_work_date) + _v94_div_params,
)
_v94_master_pending = _v94_scalar(
    "SELECT COUNT(*) FROM employees e WHERE e.status='Active' AND LOWER(TRIM(COALESCE(e.department,'')))='hr review'" + _v94_emp_clause,
    _v94_div_params,
)

# Missing attendance is meaningful only after at least one source row exists for the selected date.
_v94_missing = 0
if _v94_att_records > 0:
    _v94_missing = _v94_scalar(
        """SELECT COUNT(*)
           FROM employees e
           LEFT JOIN attendance a
             ON a.employee_id=e.employee_id AND a.work_date=?
           WHERE e.status='Active' AND a.id IS NULL""" + _v94_emp_clause,
        (global_work_date,) + _v94_div_params,
    )

_v94_payroll_pending = 0
if can_view_salary(_current_role) and _v94_active > 0:
    _v94_finalized = _v94_scalar(
        "SELECT COUNT(*) FROM payroll_records WHERE payroll_month=?" + _v94_plain_clause,
        (_month_key(global_payroll_month),) + _v94_div_params,
    )
    _v94_payroll_pending = 1 if _v94_finalized < _v94_active else 0

_v94_upload_pending = 1 if (_v94_active > 0 and _v94_att_records == 0) else 0
_v94_notification_total = (
    _v94_review + _v94_missing + _v94_master_pending + _v94_payroll_pending + _v94_upload_pending
)

st.sidebar.markdown('<div class="v5-sidebar-label">Notifications</div>', unsafe_allow_html=True)
with st.sidebar.expander(f"🔔 Notification Centre  ·  {_v94_notification_total:,}", expanded=False):
    if _v94_notification_total == 0:
        st.success("No current operational alerts for this context.")
    else:
        if _v94_upload_pending:
            st.warning(f"Attendance not loaded for {global_work_date.strftime('%d %b %Y')}.")
        if _v94_review:
            st.write(f"**{_v94_review:,}** attendance HR Review row(s) this month.")
        if _v94_missing:
            st.write(f"**{_v94_missing:,}** active employee(s) missing attendance on {global_work_date.strftime('%d %b %Y')}.")
        if _v94_master_pending:
            st.write(f"**{_v94_master_pending:,}** Employee Master record(s) awaiting HR confirmation.")
        if _v94_payroll_pending:
            st.write(f"**Payroll:** {global_payroll_month.strftime('%b %Y')} is not fully finalized for this context.")

st.sidebar.markdown('<div class="v5-sidebar-label">Recent</div>', unsafe_allow_html=True)
_v94_recent_targets = [m for m in _v94_recent if m != page and m in available_modules][:4]
if not _v94_recent_targets:
    st.sidebar.caption("Your recently opened modules will appear here.")
else:
    for _v94_i, _v94_module in enumerate(_v94_recent_targets):
        if st.sidebar.button(
            f"↩  {_v94_module}",
            key=f"v94_recent_{_v94_i}_{_v94_module}",
            use_container_width=True,
        ):
            st.session_state["_v83_nav_request"] = _v94_module
            st.rerun()

st.sidebar.markdown('<div class="v5-sidebar-label">Task Monitoring</div>', unsafe_allow_html=True)
_v94_tasks = []
if _v94_upload_pending:
    _v94_tasks.append(("Attendance upload", f"No attendance rows on {global_work_date.strftime('%d %b')}", "Attendance"))
if _v94_review:
    _v94_tasks.append(("HR Review", f"{_v94_review:,} attendance exception(s)", "Attendance"))
if _v94_missing:
    _v94_tasks.append(("Missing attendance", f"{_v94_missing:,} active employee(s)", "Attendance"))
if _v94_master_pending:
    _v94_tasks.append(("Employee Master", f"{_v94_master_pending:,} record(s) pending", "Employees"))
if _v94_payroll_pending and "Payroll" in available_modules:
    _v94_tasks.append(("Payroll", f"{global_payroll_month.strftime('%b %Y')} not fully finalized", "Payroll"))

if not _v94_tasks:
    st.sidebar.success("✓ No pending tasks in the selected context.")
else:
    for _v94_i, (_v94_title, _v94_detail, _v94_target) in enumerate(_v94_tasks[:5]):
        st.sidebar.caption(f"• **{_v94_title}** — {_v94_detail}")
    _v94_task_targets = []
    for _, _, _v94_target in _v94_tasks:
        if _v94_target in available_modules and _v94_target not in _v94_task_targets:
            _v94_task_targets.append(_v94_target)
    for _v94_i, _v94_target in enumerate(_v94_task_targets[:3]):
        if st.sidebar.button(
            f"Open {_v94_target}",
            key=f"v94_task_open_{_v94_i}_{_v94_target}",
            use_container_width=True,
        ):
            st.session_state["_v83_nav_request"] = _v94_target
            st.rerun()

'''

if anchor not in text:
    raise SystemExit('V9.4 insertion anchor not found')

text = text.replace(anchor, insert + anchor, 1)
p.write_text(text, encoding='utf-8')
