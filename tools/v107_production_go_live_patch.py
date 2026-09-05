from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V10.7 PRODUCTION GO-LIVE HARDENING"
if MARK in s:
    print("V10.7 production hardening already applied")
    raise SystemExit(0)

# 1) Persistent audit log table.
settings_anchor = '''        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_settings(
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            )
        """)
'''
settings_new = settings_anchor + '''        # V10.7 PRODUCTION GO-LIVE HARDENING
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log(
                audit_id BIGSERIAL PRIMARY KEY,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                module TEXT NOT NULL,
                entity_type TEXT,
                entity_id TEXT,
                details TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor)"
        )
'''
if settings_anchor not in s:
    raise RuntimeError("app_settings migration anchor not found")
s = s.replace(settings_anchor, settings_new, 1)

# 2) Audit helper + safe Owner/Admin backup workbook.
helper_anchor = '''def get_app_users():
'''
helpers = '''# V10.7 PRODUCTION GO-LIVE HARDENING
def record_audit_event(actor, action, module, entity_type="", entity_id="", details=""):
    """Best-effort business audit. Audit logging must never break the user's action."""
    try:
        upsert(
            """
            INSERT INTO audit_log(actor, action, module, entity_type, entity_id, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(actor or "system"),
                str(action or ""),
                str(module or ""),
                str(entity_type or ""),
                str(entity_id or ""),
                str(details or "")[:4000],
            ),
        )
    except Exception:
        pass


def build_admin_backup_xlsx():
    """Create a point-in-time business-data backup. Credentials/session secrets are excluded."""
    export_specs = [
        ("Employees", "SELECT * FROM employees ORDER BY employee_id"),
        ("Attendance", "SELECT * FROM attendance ORDER BY work_date, division, employee_id"),
        ("Payroll Records", "SELECT * FROM payroll_records ORDER BY payroll_month, division, employee_id"),
        ("Payroll Adjustments", "SELECT * FROM payroll_adjustments ORDER BY payroll_month, division, employee_id"),
        ("Contractors", "SELECT * FROM contractors ORDER BY division, vendor_name"),
        ("Contractor Rates", "SELECT * FROM contractor_rates ORDER BY contractor_id, work_type"),
        ("Contractor Work", "SELECT * FROM contractor_work_entries ORDER BY work_date, contractor_id"),
        ("Departments", "SELECT * FROM departments ORDER BY department"),
        ("Machines", "SELECT * FROM machines ORDER BY machine"),
        ("Shift Targets", "SELECT * FROM machine_shift_targets ORDER BY machine, shift"),
        ("User Access", """
            SELECT u.username,u.full_name,u.role,u.is_active,p.page_name,p.can_access
            FROM app_users u
            LEFT JOIN app_user_permissions p ON p.user_id=u.user_id
            ORDER BY u.username,p.page_name
        """),
        ("App Settings", "SELECT * FROM app_settings ORDER BY setting_key"),
        ("Audit Log", "SELECT * FROM audit_log ORDER BY created_at DESC"),
    ]

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, query in export_specs:
            try:
                df = read_df(query)
            except Exception as exc:
                df = pd.DataFrame([{"Export Error": str(exc)}])
            df.to_excel(writer, index=False, sheet_name=sheet_name[:31])

        meta = pd.DataFrame([
            {"Field": "Application", "Value": "Reliable Packaging HRMS V10 Production"},
            {"Field": "Generated At IST", "Value": datetime.now(IST).strftime("%d %b %Y %H:%M:%S")},
            {"Field": "Note", "Value": "Password hashes and active session tokens are intentionally excluded."},
        ])
        meta.to_excel(writer, index=False, sheet_name="Backup Info")

    output.seek(0)
    return output.getvalue()


def get_app_users():
'''
if helper_anchor not in s:
    raise RuntimeError("get_app_users helper anchor not found")
s = s.replace(helper_anchor, helpers, 1)

# 3) Successful login audit (best effort).
login_return_anchor = '''    return {
        "user_id": int(row["user_id"]),
        "username": str(row["username"]),
        "full_name": str(row["full_name"]),
        "role": str(row["role"]),
    }


def _session_token_hash(token):
'''
login_return_new = '''    user_payload = {
        "user_id": int(row["user_id"]),
        "username": str(row["username"]),
        "full_name": str(row["full_name"]),
        "role": str(row["role"]),
    }
    record_audit_event(
        user_payload["username"], "LOGIN_SUCCESS", "Authentication",
        "User", user_payload["username"], f"Role={user_payload['role']}"
    )
    return user_payload


def _session_token_hash(token):
'''
if login_return_anchor not in s:
    raise RuntimeError("authenticate return anchor not found")
s = s.replace(login_return_anchor, login_return_new, 1)

# 4) Key business-action audit events.
replacements = [
(
'''                        conn.commit();cur.close();st.success("Attendance corrections saved.");st.rerun()''',
'''                        conn.commit();cur.close()
                        record_audit_event(
                            _current_user["username"], "ATTENDANCE_CORRECTION_SAVE", "Attendance",
                            "AttendanceDate", global_work_date.isoformat(),
                            f"Division={global_division}; Rows={len(edited)}"
                        )
                        st.success("Attendance corrections saved.");st.rerun()'''
),
(
'''                    save_payroll_adjustment(global_payroll_month,adj_div,emp_id,values,_current_user["username"])
                    st.success("Payroll adjustment saved.");st.rerun()''',
'''                    save_payroll_adjustment(global_payroll_month,adj_div,emp_id,values,_current_user["username"])
                    record_audit_event(
                        _current_user["username"], "PAYROLL_ADJUSTMENT_SAVE", "Payroll",
                        "Employee", emp_id,
                        f"Month={global_payroll_month.strftime('%Y-%m')}; Division={adj_div}"
                    )
                    st.success("Payroll adjustment saved.");st.rerun()'''
),
(
'''                        count=finalize_payroll(global_payroll_month,final_div,live,_current_user["username"])
                        st.success(f"{count} payroll records finalized.");st.rerun()''',
'''                        count=finalize_payroll(global_payroll_month,final_div,live,_current_user["username"])
                        record_audit_event(
                            _current_user["username"], "PAYROLL_FINALIZE", "Payroll",
                            "Division", final_div,
                            f"Month={global_payroll_month.strftime('%Y-%m')}; Records={count}"
                        )
                        st.success(f"{count} payroll records finalized.");st.rerun()'''
),
(
'''                    st.success("User created.")
                    st.rerun()''',
'''                    record_audit_event(
                        _current_user["username"], "USER_CREATE", "User Management",
                        "User", username.strip().lower(), f"Role={role}"
                    )
                    st.success("User created.")
                    st.rerun()'''
),
(
'''                    save_user_permissions(uid,backend_pages)
                    st.success("User access updated.")
                    st.rerun()''',
'''                    save_user_permissions(uid,backend_pages)
                    record_audit_event(
                        _current_user["username"], "USER_ACCESS_UPDATE", "User Management",
                        "User", selected_user,
                        f"Role={edit_role}; Active={active}; Modules={','.join(sorted(modules))}"
                    )
                    st.success("User access updated.")
                    st.rerun()'''
),
(
'''                    upsert("DELETE FROM app_users WHERE user_id=?", (delete_uid,))
                    st.success(f"User '{delete_target}' deleted permanently.")
                    st.rerun()''',
'''                    upsert("DELETE FROM app_users WHERE user_id=?", (delete_uid,))
                    record_audit_event(
                        _current_user["username"], "USER_DELETE", "User Management",
                        "User", delete_target, f"PreviousRole={delete_role}"
                    )
                    st.success(f"User '{delete_target}' deleted permanently.")
                    st.rerun()'''
),
]
for old, new in replacements:
    if old not in s:
        raise RuntimeError("Expected business-action anchor not found")
    s = s.replace(old, new, 1)

# Attendance import has three success branches; audit once immediately before rerun.
import_anchor = '''                            else:
                                st.success(
                                    f"{saved:,} attendance rows processed for **{actual}** "
                                    "from all valid dates in the workbook."
                                )
                            st.rerun()
'''
import_new = '''                            else:
                                st.success(
                                    f"{saved:,} attendance rows processed for **{actual}** "
                                    "from all valid dates in the workbook."
                                )
                            record_audit_event(
                                _current_user["username"], "ATTENDANCE_IMPORT", "Attendance",
                                "Division", actual,
                                f"Rows={saved}; ReplaceExisting={bool(replace_existing_scope)}"
                            )
                            st.rerun()
'''
if import_anchor not in s:
    raise RuntimeError("Attendance import success anchor not found")
s = s.replace(import_anchor, import_new, 1)

# 5) Production Go-Live Centre inside Owner/Admin User Management.
system_anchor = '''        with st.container(border=True):
            v5_panel("System Information","Live architecture.")
'''
go_live = r'''        with st.container(border=True):
            v5_panel(
                "Production Go-Live Centre",
                "Owner/Admin readiness checks, audit history and protected business-data backup."
            )

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

            try:
                _v107_latest_att = read_df(
                    "SELECT MAX(work_date) AS d, COUNT(*) AS rows FROM attendance"
                )
                _v107_latest_date = (
                    str(_v107_latest_att.iloc[0]["d"])
                    if not _v107_latest_att.empty and _v107_latest_att.iloc[0]["d"] else "No attendance yet"
                )
            except Exception:
                _v107_latest_date = "Unavailable"

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

            _v107_checks = [
                ("Database", _v107_db_ok, "Connected" if _v107_db_ok else "Connection issue"),
                ("Employee Master", _v107_active_employees > 0, f"{_v107_active_employees:,} active employees"),
                ("HR Login", _v107_hr_users > 0, f"{_v107_hr_users:,} active HR user(s)"),
                ("Attendance Source", _v107_latest_date not in {"No attendance yet","Unavailable"}, f"Latest: {_v107_latest_date}"),
                ("Master Exceptions", _v107_master_pending == 0, f"{_v107_master_pending:,} pending"),
                ("HR Review Queue", _v107_reviews == 0, f"{_v107_reviews:,} review row(s)"),
            ]
            _v107_ready = sum(1 for _, ok, _ in _v107_checks if ok)
            _v107_total = len(_v107_checks)

            st.progress(
                _v107_ready / _v107_total,
                text=f"Go-live readiness · {_v107_ready}/{_v107_total} production checks passed"
            )

            _v107_cols = st.columns(3, gap="small")
            for _v107_i, (_v107_name, _v107_ok, _v107_detail) in enumerate(_v107_checks):
                with _v107_cols[_v107_i % 3]:
                    st.markdown(
                        f"""
                        <div style="padding:12px 13px;border:1px solid #203149;border-radius:11px;
                                    background:#0d1724;min-height:78px;margin-bottom:8px">
                          <div style="font-size:9px;color:#8298ad;font-weight:800">{html.escape(_v107_name)}</div>
                          <div style="font-size:14px;color:{'#65e3ad' if _v107_ok else '#ffc766'};
                                      font-weight:900;margin-top:5px">
                            {'✓ READY' if _v107_ok else '• ACTION'}
                          </div>
                          <div style="font-size:8px;color:#71889f;margin-top:4px">{html.escape(_v107_detail)}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            if _v107_ready == _v107_total:
                st.success("Production readiness checks are clear for the current database state.")
            else:
                st.info(
                    "The software is operational, but complete the items marked ACTION before handing daily ownership to HR."
                )

            _v107_b1, _v107_b2 = st.columns([1,1], gap="small")
            with _v107_b1:
                if st.button(
                    "Prepare Production Backup",
                    key="v107_prepare_backup",
                    use_container_width=True,
                    help="Creates an Owner/Admin-only Excel backup. Password hashes and session tokens are excluded."
                ):
                    with st.spinner("Preparing protected business-data backup..."):
                        st.session_state["_v107_backup_bytes"] = build_admin_backup_xlsx()
                        st.session_state["_v107_backup_name"] = (
                            "Reliable_HRMS_Backup_" + datetime.now(IST).strftime("%Y%m%d_%H%M%S") + ".xlsx"
                        )
                        record_audit_event(
                            _current_user["username"], "BACKUP_PREPARE", "System",
                            "Database", "business-data", "Owner/Admin Excel backup generated"
                        )
                    st.success("Backup prepared. Download it below.")

            with _v107_b2:
                _v107_backup_bytes = st.session_state.get("_v107_backup_bytes")
                if _v107_backup_bytes:
                    st.download_button(
                        "Download Production Backup",
                        data=_v107_backup_bytes,
                        file_name=st.session_state.get("_v107_backup_name", "Reliable_HRMS_Backup.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="v107_download_backup",
                        use_container_width=True,
                    )
                else:
                    st.button(
                        "Download Production Backup",
                        key="v107_download_backup_disabled",
                        use_container_width=True,
                        disabled=True,
                        help="Prepare the backup first.",
                    )

            st.caption(
                f"Active users: {_v107_active_users:,}. Backup excludes password hashes and browser session tokens."
            )

            _v107_audit = read_df(
                """SELECT created_at, actor, action, module, entity_type, entity_id, details
                   FROM audit_log ORDER BY created_at DESC LIMIT 40"""
            )
            if not _v107_audit.empty:
                _v107_audit["created_at"] = _v107_audit["created_at"].apply(_to_ist_display)
                st.markdown("#### Recent Audit Trail")
                st.dataframe(
                    _v107_audit.rename(columns={
                        "created_at":"Time (IST)","actor":"User","action":"Action",
                        "module":"Module","entity_type":"Type","entity_id":"Reference","details":"Details"
                    }),
                    hide_index=True,
                    use_container_width=True,
                    height=280,
                )
            else:
                st.caption("Audit trail will populate as users perform production actions.")

''' + system_anchor
if system_anchor not in s:
    raise RuntimeError("System Information anchor not found")
s = s.replace(system_anchor, go_live, 1)

# Correct outdated system-information product label.
s = s.replace(
    'st.write("**Application:** Reliable Packaging HRMS V9 Ultra Glass Live Interface")',
    'st.write("**Application:** Reliable Packaging HRMS V10 Production")',
    1,
)

p.write_text(s, encoding="utf-8")
print("Applied V10.7 production go-live hardening")
