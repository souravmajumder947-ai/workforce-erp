from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V10.9 FINAL PRODUCTION ACTIVATION"
if MARK in s:
    print("V10.9 final production activation already applied")
    raise SystemExit(0)

# Read production mode for the logged-in application and expose it to the sidebar.
auth_anchor = '''_current_user = st.session_state["auth_user"]
_current_role = str(_current_user.get("role", "Viewer"))
st.markdown('<div class="v104-app-quality-marker"></div>', unsafe_allow_html=True)
'''
auth_new = '''_current_user = st.session_state["auth_user"]
_current_role = str(_current_user.get("role", "Viewer"))
# V10.9 FINAL PRODUCTION ACTIVATION
_v109_production_mode = str(get_setting_value("production_mode", "SETUP") or "SETUP").upper()
_v109_production_live = _v109_production_mode == "LIVE"
st.markdown('<div class="v104-app-quality-marker"></div>', unsafe_allow_html=True)
'''
if auth_anchor not in s:
    raise RuntimeError("Authenticated-user anchor not found")
s = s.replace(auth_anchor, auth_new, 1)

# Sidebar badge reflects actual production state rather than always saying LIVE.
side_anchor = '''        <small><span class="v8-live-dot"></span> SMART HRMS · V10 LIVE</small>'''
side_new = '''        <small><span class="v8-live-dot"></span> SMART HRMS · {"PRODUCTION LIVE" if _v109_production_live else "SETUP MODE"}</small>'''
if side_anchor not in s:
    raise RuntimeError("Sidebar live badge anchor not found")
s = s.replace(side_anchor, side_new, 1)

# Add salary readiness before the final check list.
checks_anchor = '''            _v107_checks = [
                ("Database", _v107_db_ok, "Connected" if _v107_db_ok else "Connection issue"),
'''
salary_block = r'''            # Salary master must be complete before formal production activation.
            try:
                _v109_salary_missing = int(
                    read_df(
                        """SELECT COUNT(*) AS c
                           FROM employees
                           WHERE UPPER(TRIM(status))='ACTIVE'
                             AND COALESCE(monthly_salary,0) <= 0"""
                    ).iloc[0]["c"]
                )
            except Exception:
                _v109_salary_missing = _v107_active_employees

            _v107_checks = [
                ("Database", _v107_db_ok, "Connected" if _v107_db_ok else "Connection issue"),
'''
if checks_anchor not in s:
    raise RuntimeError("Readiness-check list anchor not found")
s = s.replace(checks_anchor, salary_block, 1)

# Insert salary check after Employee Master.
emp_check = '''                ("Employee Master", _v107_active_employees > 0, f"{_v107_active_employees:,} active employees"),
                ("HR Login", _v107_hr_users > 0, f"{_v107_hr_users:,} active HR user(s)"),
'''
emp_check_new = '''                ("Employee Master", _v107_active_employees > 0, f"{_v107_active_employees:,} active employees"),
                ("Salary Master", _v109_salary_missing == 0, f"{_v109_salary_missing:,} active employee(s) missing salary"),
                ("HR Login", _v107_hr_users > 0, f"{_v107_hr_users:,} active HR user(s)"),
'''
if emp_check not in s:
    raise RuntimeError("Employee/HR readiness anchors not found")
s = s.replace(emp_check, emp_check_new, 1)

# Add formal production activation immediately after the readiness summary message.
summary_anchor = '''            if _v107_ready == _v107_total:
                st.success("Production readiness checks are clear for the current database state.")
            else:
                st.info(
                    "The software is operational, but the live data/process is not fully handover-ready. "
                    "Complete every item marked ACTION before HR takes daily ownership."
                )

            _v107_b1, _v107_b2 = st.columns([1,1], gap="small")
'''
activation = r'''            if _v107_ready == _v107_total:
                st.success("Production readiness checks are clear for the current database state.")
            else:
                st.info(
                    "The software is operational, but the live data/process is not fully handover-ready. "
                    "Complete every item marked ACTION before HR takes daily ownership."
                )

            # Formal go-live switch. No override is allowed while a readiness check is ACTION.
            _v109_live_at = get_setting_value("production_live_at", "")
            _v109_live_by = get_setting_value("production_live_by", "")
            if _v109_production_live:
                st.markdown(
                    f"""
                    <div style="padding:14px 16px;margin:10px 0 12px;border-radius:12px;
                                border:1px solid rgba(46,211,154,.38);
                                background:linear-gradient(90deg,rgba(20,87,67,.48),rgba(9,35,32,.46))">
                      <div style="font-size:15px;font-weight:950;color:#69e5b4">● PRODUCTION LIVE</div>
                      <div style="font-size:9px;color:#9ab9ad;margin-top:5px">
                        Activated by {html.escape(str(_v109_live_by or "Owner/Admin"))}
                        {(" · " + html.escape(str(_v109_live_at))) if _v109_live_at else ""}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                _v109_confirm = st.checkbox(
                    "I confirm the production checks are complete and HR is approved to begin live daily work.",
                    key="v109_go_live_confirm"
                )
                _v109_can_activate = (_v107_ready == _v107_total) and _v109_confirm
                if st.button(
                    "START HRMS PRODUCTION LIVE",
                    type="primary",
                    key="v109_start_production_live",
                    use_container_width=True,
                    disabled=not _v109_can_activate,
                    help=(
                        "Enabled only after every production readiness check is READY."
                        if _v107_ready < _v107_total
                        else "Activates formal production mode for HR."
                    ),
                ):
                    _v109_now = datetime.now(IST).strftime("%d %b %Y · %H:%M:%S IST")
                    save_setting_value("production_mode", "LIVE")
                    save_setting_value("production_live_at", _v109_now)
                    save_setting_value("production_live_by", _current_user["username"])
                    record_audit_event(
                        _current_user["username"], "PRODUCTION_GO_LIVE", "System",
                        "Application", "Reliable HRMS V10",
                        f"Activated={_v109_now}; Checks={_v107_ready}/{_v107_total}"
                    )
                    st.success("HRMS Production Live activated.")
                    st.rerun()

            _v107_b1, _v107_b2 = st.columns([1,1], gap="small")
'''
if summary_anchor not in s:
    raise RuntimeError("Go-live summary anchor not found")
s = s.replace(summary_anchor, activation, 1)

# System information displays the actual mode.
system_line = '''            st.write("**Application:** Reliable Packaging HRMS V10 Production")
            st.write("**Database:** Neon PostgreSQL")
'''
system_new = '''            st.write("**Application:** Reliable Packaging HRMS V10 Production")
            st.write(f"**Production Mode:** {'LIVE' if _v109_production_live else 'SETUP'}")
            st.write("**Database:** Neon PostgreSQL")
'''
if system_line not in s:
    raise RuntimeError("System Information anchor not found")
s = s.replace(system_line, system_new, 1)

p.write_text(s, encoding="utf-8")
print("Applied V10.9 final production activation")
