from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V10.8 STRICT PRODUCTION READINESS"
if MARK in s:
    print("V10.8 strict readiness already applied")
    raise SystemExit(0)

# Replace the current 6-check readiness logic with stricter production checks.
start = s.index('            try:\n                _v107_db_ok = bool(int(read_df("SELECT 1 AS ok").iloc[0]["ok"]) == 1)')
end = s.index('            st.progress(\n', start)
old = s[start:end]

new = r'''            # V10.8 STRICT PRODUCTION READINESS
            try:
                _v107_db_ok = bool(int(read_df("SELECT 1 AS ok").iloc[0]["ok"]) == 1)
            except Exception:
                _v107_db_ok = False

            try:
                _v107_active_employees = int(
                    read_df("SELECT COUNT(*) AS c FROM employees WHERE UPPER(TRIM(status))='ACTIVE'").iloc[0]["c"]
                )
            except Exception:
                _v107_active_employees = 0

            try:
                _v107_hr_users = int(
                    read_df("SELECT COUNT(*) AS c FROM app_users WHERE is_active=TRUE AND role='HR'").iloc[0]["c"]
                )
                _v107_active_users = int(
                    read_df("SELECT COUNT(*) AS c FROM app_users WHERE is_active=TRUE").iloc[0]["c"]
                )
            except Exception:
                _v107_hr_users = 0
                _v107_active_users = 0

            # Attendance freshness is measured against today's IST date, not just
            # whether any old attendance exists in the database.
            _v108_today = datetime.now(IST).date()
            _v108_latest_dt = None
            try:
                _v107_latest_att = read_df(
                    "SELECT MAX(work_date) AS d, COUNT(*) AS rows FROM attendance"
                )
                if not _v107_latest_att.empty and _v107_latest_att.iloc[0]["d"]:
                    _v108_latest_dt = pd.to_datetime(
                        _v107_latest_att.iloc[0]["d"], errors="coerce"
                    )
                    if not pd.isna(_v108_latest_dt):
                        _v108_latest_dt = _v108_latest_dt.date()
                _v107_latest_date = (
                    _v108_latest_dt.isoformat() if _v108_latest_dt else "No attendance yet"
                )
            except Exception:
                _v107_latest_date = "Unavailable"
                _v108_latest_dt = None

            if _v108_latest_dt:
                _v108_att_lag = max(0, (_v108_today - _v108_latest_dt).days)
            else:
                _v108_att_lag = 9999
            _v108_att_fresh = _v108_att_lag <= 2

            try:
                _v107_reviews = int(
                    read_df(
                        """SELECT COUNT(*) AS c FROM attendance
                           WHERE status='HR Review' OR review_required=TRUE"""
                    ).iloc[0]["c"]
                )
            except Exception:
                _v107_reviews = 0

            try:
                _v107_master_pending = int(
                    read_df(
                        """SELECT COUNT(*) AS c FROM employees
                           WHERE UPPER(TRIM(status))='ACTIVE'
                             AND LOWER(TRIM(COALESCE(department,'')))='hr review'"""
                    ).iloc[0]["c"]
                )
            except Exception:
                _v107_master_pending = 0

            # Active employees who have no row on the latest attendance date are
            # not automatically absent; they are a source-completeness action item.
            _v108_missing_source = 0
            if _v108_latest_dt:
                try:
                    _v108_missing_source = int(
                        read_df(
                            """SELECT COUNT(*) AS c
                               FROM employees e
                               WHERE UPPER(TRIM(e.status))='ACTIVE'
                                 AND NOT EXISTS (
                                     SELECT 1 FROM attendance a
                                     WHERE a.employee_id=e.employee_id
                                       AND a.work_date=?
                                 )""",
                            (_v108_latest_dt.isoformat(),),
                        ).iloc[0]["c"]
                    )
                except Exception:
                    _v108_missing_source = 0

            # Every division containing active employees should have attendance
            # represented and reasonably current.
            _v108_division_coverage_ok = True
            _v108_division_detail = "No active divisions"
            try:
                _v108_div = read_df(
                    """SELECT e.division,
                              COUNT(*) AS active_employees,
                              MAX(a.work_date) AS latest_attendance
                       FROM employees e
                       LEFT JOIN attendance a ON a.employee_id=e.employee_id
                       WHERE UPPER(TRIM(e.status))='ACTIVE'
                       GROUP BY e.division
                       ORDER BY e.division"""
                )
                _v108_division_states = []
                if not _v108_div.empty:
                    for _, _r in _v108_div.iterrows():
                        _dname = _clean_text(_r.get("division")) or "Unassigned"
                        _dlatest = pd.to_datetime(_r.get("latest_attendance"), errors="coerce")
                        if pd.isna(_dlatest):
                            _ok = False
                            _label = "no attendance"
                        else:
                            _ddate = _dlatest.date()
                            _lag = max(0, (_v108_today - _ddate).days)
                            _ok = _lag <= 2
                            _label = _ddate.isoformat()
                        if not _ok:
                            _v108_division_coverage_ok = False
                        _v108_division_states.append(f"{_dname}: {_label}")
                    _v108_division_detail = " | ".join(_v108_division_states)
            except Exception:
                _v108_division_coverage_ok = False
                _v108_division_detail = "Unable to verify division coverage"

            # Backup is a real production prerequisite. It becomes READY after the
            # Owner/Admin prepares at least one protected backup.
            try:
                _v108_backup = read_df(
                    """SELECT MAX(created_at) AS last_backup
                       FROM audit_log WHERE action='BACKUP_PREPARE'"""
                )
                _v108_backup_dt = (
                    _v108_backup.iloc[0]["last_backup"]
                    if not _v108_backup.empty else None
                )
                _v108_backup_ready = _v108_backup_dt is not None and not pd.isna(_v108_backup_dt)
                _v108_backup_detail = (
                    f"Prepared: {_to_ist_display(_v108_backup_dt)}"
                    if _v108_backup_ready else "No production backup prepared yet"
                )
            except Exception:
                _v108_backup_ready = False
                _v108_backup_detail = "Backup history unavailable"

            _v107_checks = [
                ("Database", _v107_db_ok, "Connected" if _v107_db_ok else "Connection issue"),
                ("Employee Master", _v107_active_employees > 0, f"{_v107_active_employees:,} active employees"),
                ("HR Login", _v107_hr_users > 0, f"{_v107_hr_users:,} active HR user(s)"),
                (
                    "Attendance Freshness",
                    _v108_att_fresh,
                    (
                        f"Latest {_v107_latest_date} · {_v108_att_lag} day(s) behind"
                        if _v108_latest_dt else _v107_latest_date
                    ),
                ),
                ("Division Coverage", _v108_division_coverage_ok, _v108_division_detail),
                (
                    "Missing From Source",
                    _v108_missing_source == 0,
                    f"{_v108_missing_source:,} active employee(s) missing on latest attendance date"
                ),
                ("Master Exceptions", _v107_master_pending == 0, f"{_v107_master_pending:,} pending"),
                ("HR Review Queue", _v107_reviews == 0, f"{_v107_reviews:,} review row(s)"),
                ("Production Backup", _v108_backup_ready, _v108_backup_detail),
            ]
            _v107_ready = sum(1 for _, ok, _ in _v107_checks if ok)
            _v107_total = len(_v107_checks)

'''
s = s[:start] + new + s[end:]

# After preparing a backup, rerun so the readiness check immediately changes to READY
# while the prepared bytes remain in session state for the download button.
backup_anchor = '''                    st.success("Backup prepared. Download it below.")
'''
backup_new = '''                    st.success("Backup prepared. Download it below.")
                    st.rerun()
'''
if backup_anchor not in s:
    raise RuntimeError("Backup success anchor not found")
s = s.replace(backup_anchor, backup_new, 1)

# Make the message explicitly distinguish software-operational from data-ready.
old_msg = '''                st.info(
                    "The software is operational, but complete the items marked ACTION before handing daily ownership to HR."
                )
'''
new_msg = '''                st.info(
                    "The software is operational, but the live data/process is not fully handover-ready. "
                    "Complete every item marked ACTION before HR takes daily ownership."
                )
'''
if old_msg not in s:
    raise RuntimeError("Readiness info message anchor not found")
s = s.replace(old_msg, new_msg, 1)

p.write_text(s, encoding="utf-8")
print("Applied V10.8 strict production readiness")
