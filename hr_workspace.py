"""HR's daily starting point and individual salary maintenance."""
from calendar import monthrange
from datetime import date
import math

import pandas as pd
import streamlit as st


def open_task(task, employee_id=None):
    st.session_state["hr_task_request"] = (task, employee_id)


def render_attendance_entry(context):
    read = context["read_df"]
    division = context["global_division"]
    if division == context["ALL_DIVISIONS"]:
        st.info("Select one Division in the sidebar to enter attendance.")
        return
    st.title("Attendance and leave entry")
    employees = read(
        """SELECT employee_id,employee_name,designation,joining_date,last_working_date,status
           FROM employees WHERE division=? AND UPPER(TRIM(department))<>'HR REVIEW'
           ORDER BY employee_name""", (division,),
    )
    if employees.empty:
        st.info("Add or confirm employee records first.")
        return
    labels = {row.employee_id: f"{row.employee_name} ({row.employee_id})" for row in employees.itertuples()}
    eid = st.selectbox("Employee attendance record", list(labels), format_func=labels.get)
    employee = employees.loc[employees.employee_id == eid].iloc[0]
    work_date = st.date_input("Attendance date", value=date.today(), max_value=date.today())
    shift = st.selectbox("Attendance shift", ["General", "A", "B"])
    key = (context["_current_user"]["username"], eid, division, work_date, shift)
    snapshot = st.session_state.get("hr_attendance_snapshot")
    if snapshot is None or snapshot[0] != key or st.button("Reload attendance record"):
        saved = read(
            "SELECT * FROM attendance WHERE employee_id=? AND work_date=? AND shift=?",
            (eid, work_date.isoformat(), shift),
        )
        previous = saved.iloc[0].to_dict() if not saved.empty else {}
        st.session_state["hr_attendance_snapshot"] = (key, previous)
    else:
        previous = snapshot[1]
    if previous and previous["division"] != division:
        st.error("This employee/date/shift already belongs to another division.")
        return
    statuses = ["Present", "OD", "Half Day", "Absent", "WO", "Holiday", "Leave", "CL", "SL", "EL", "LWP"]
    old_status = previous.get("status")
    with st.form(f"hr_daily_attendance_{eid}_{work_date}_{shift}"):
        status = st.selectbox("Final attendance status", statuses, index=statuses.index(old_status) if old_status in statuses else 0)
        hours = st.number_input("Verified working hours", min_value=0.0, max_value=24.0,
                                value=min(24.0, max(0.0, float(previous.get("working_hours") or 0))), step=0.25)
        reason = st.text_area("HR reason / leave approval")
        replace = st.checkbox("Replace the existing attendance record") if previous else True
        submit = st.form_submit_button("Save attendance or leave", type="primary")
    if not submit:
        return
    if not reason.strip() or not replace:
        st.error("Enter an HR reason and confirm replacement if a record already exists.")
        return
    joined = pd.to_datetime(employee.joining_date, errors="coerce")
    left = pd.to_datetime(employee.last_working_date, errors="coerce")
    if (pd.isna(joined) or work_date < joined.date() or (pd.notna(left) and work_date > left.date())
            or (employee.status != "Active" and pd.isna(left))):
        st.error("Check the employee's joining and leaving dates before entering attendance.")
        return
    worked = status in {"Present", "OD", "Half Day"}
    if not math.isfinite(hours) or (worked and hours <= 0) or (not worked and hours > 0):
        st.error("Enter verified hours for Present, OD or Half Day. Use zero hours for other statuses.")
        return
    ot = max(0.0, hours - context["get_setting_float"]("ot_threshold_hours", 12.0)) if worked else 0.0
    actor = context["_current_user"]["username"]
    conn = context["get_pg_conn"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO attendance(work_date,shift,employee_id,division,status,working_hours,ot_hours,
                   remark,review_required,reviewed_by,source_type,source_employee_name,updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,FALSE,%s,'HR manual entry',%s,CURRENT_TIMESTAMP)
                   ON CONFLICT(work_date,shift,employee_id) DO UPDATE SET
                   status=excluded.status,working_hours=excluded.working_hours,ot_hours=excluded.ot_hours,
                   remark=excluded.remark,review_required=FALSE,reviewed_by=excluded.reviewed_by,
                   source_issue='',updated_at=CURRENT_TIMESTAMP
                   WHERE attendance.division=excluded.division
                   AND attendance.updated_at IS NOT DISTINCT FROM %s""",
                (work_date.isoformat(), shift, eid, division, status, hours, ot, reason.strip(), actor,
                 employee.employee_name, previous.get("updated_at")),
            )
            if cur.rowcount != 1:
                raise ValueError("Attendance changed while you were editing. Reload the record before saving.")
            cur.execute(
                """INSERT INTO audit_log(actor,action,module,entity_type,entity_id,details)
                   VALUES (%s,'SAVE','HR Workspace','Attendance',%s,%s)""",
                (actor, eid, f"Date={work_date}; Shift={shift}; Status={status}"),
            )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        st.error(f"Attendance could not be saved: {exc}")
        return
    finally:
        conn.close()
    st.session_state.pop("hr_attendance_snapshot", None)
    st.success("Attendance saved. Payroll will use the updated record.")


def render_salary_editor(read, get_conn, division, all_divisions, actor):
    clause, params = ("", ()) if division == all_divisions else (" WHERE division=?", (division,))
    employees = read("SELECT * FROM employees" + clause + " ORDER BY employee_name", params)
    if employees.empty:
        st.info("Create an employee record first.")
        return
    labels = {row.employee_id: f"{row.employee_name} ({row.employee_id})" for row in employees.itertuples()}
    employee_id = st.selectbox("Employee salary record", list(labels), format_func=labels.get)
    snapshot_key = (actor, division, employee_id)
    snapshot = st.session_state.get("hr_salary_snapshot")
    reload_record = st.button("Reload salary record")
    if reload_record or snapshot is None or snapshot[0] != snapshot_key:
        employee = employees.loc[employees.employee_id == employee_id].iloc[0]
        version = snapshot[2] + 1 if snapshot else 0
        st.session_state["hr_salary_snapshot"] = (snapshot_key, employee, version)
    else:
        employee, version = snapshot[1:]
    with st.form(f"hr_salary_{employee_id}_{version}"):
        salary = st.number_input("Monthly salary (₹)", min_value=0.0,
                                 value=float(employee.monthly_salary or 0), step=100.0)
        c1, c2 = st.columns(2)
        pf = c1.checkbox("PF applicable", value=bool(employee.pf_applicable))
        esic = c2.checkbox("ESIC applicable", value=bool(employee.esic_applicable))
        uan = c1.text_input("UAN number", value=str(employee.uan_number or ""))
        esic_number = c2.text_input("ESIC number", value=str(employee.esic_number or ""))
        pan = c1.text_input("PAN number", value=str(employee.pan_number or ""))
        bank_name = c2.text_input("Bank name", value=str(employee.bank_name or ""))
        account = c1.text_input("Bank account", value=str(employee.bank_account or ""))
        ifsc = c2.text_input("IFSC code", value=str(employee.ifsc_code or ""))
        submitted = st.form_submit_button("Save salary and statutory details", type="primary")
    if submitted:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE employees SET monthly_salary=%s,pf_applicable=%s,esic_applicable=%s,
                       uan_number=%s,esic_number=%s,pan_number=%s,bank_name=%s,bank_account=%s,ifsc_code=%s
                       WHERE employee_id=%s AND division=%s
                       AND monthly_salary IS NOT DISTINCT FROM %s
                       AND pf_applicable IS NOT DISTINCT FROM %s AND esic_applicable IS NOT DISTINCT FROM %s
                       AND uan_number IS NOT DISTINCT FROM %s AND esic_number IS NOT DISTINCT FROM %s
                       AND pan_number IS NOT DISTINCT FROM %s AND bank_name IS NOT DISTINCT FROM %s
                       AND bank_account IS NOT DISTINCT FROM %s AND ifsc_code IS NOT DISTINCT FROM %s""",
                    (salary, pf, esic, uan.strip(), esic_number.strip(), pan.strip(), bank_name.strip(),
                     account.strip(), ifsc.strip().upper(), employee_id, employee.division,
                     float(employee.monthly_salary) if pd.notna(employee.monthly_salary) else None,
                     bool(employee.pf_applicable) if pd.notna(employee.pf_applicable) else None,
                     bool(employee.esic_applicable) if pd.notna(employee.esic_applicable) else None,
                     employee.uan_number, employee.esic_number, employee.pan_number,
                     employee.bank_name, employee.bank_account, employee.ifsc_code),
                )
                if cur.rowcount != 1:
                    raise ValueError("This employee's salary details changed. Reload before saving.")
                cur.execute(
                    """INSERT INTO audit_log(actor,action,module,entity_type,entity_id,details)
                       VALUES (%s,'UPDATE','HR Workspace','Employee',%s,'Salary and statutory details updated')""",
                    (actor, employee_id),
                )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            st.error(f"Salary details could not be saved: {exc}")
        else:
            st.session_state.pop("hr_salary_snapshot", None)
            st.success("Salary and statutory details saved.")
        finally:
            conn.close()


def render_hr_workspace(context):
    if not context["can_edit_hr"](context["_current_role"]):
        st.error("HR workspace access is required.")
        return
    read = context["read_df"]
    division = context["global_division"]
    month = context["global_payroll_month"]
    start, end = month.replace(day=1), month.replace(day=monthrange(month.year, month.month)[1])
    clause, params = ("", ()) if division == context["ALL_DIVISIONS"] else (" AND division=?", (division,))
    st.title("HR entries")
    st.caption(f"{division} · {month:%B %Y}")
    success = st.session_state.pop("hr_workspace_success", None)
    if success:
        st.success(success)
    employees = read(
        """SELECT employee_id,employee_name,department,designation,division,status,monthly_salary,
                  joining_date,mobile_number,bank_account,pf_applicable,uan_number,esic_applicable,esic_number
           FROM employees WHERE 1=1""" + clause + " ORDER BY employee_name", params,
    )
    reviews = read(
        """SELECT COUNT(*) AS count FROM attendance
           WHERE (status='HR Review' OR review_required=TRUE) AND work_date BETWEEN ? AND ?""" + clause,
        (start.isoformat(), end.isoformat(), *params),
    )
    pending = int(reviews.iloc[0]["count"])
    active = employees.loc[employees.status.eq("Active")]
    unconfirmed = employees.department.fillna("").str.strip().str.upper().eq("HR REVIEW")
    missing_salary = active.monthly_salary.fillna(0).le(0)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active employees", len(active))
    c2.metric("Attendance to review", pending)
    c3.metric("Employees to confirm", int(unconfirmed.sum()))
    c4.metric("Missing salary", int(missing_salary.sum()))
    st.subheader("Employee and attendance entries")
    tasks = [
        ("Employee records", "Create, edit or upload employee identity, joining and contact details."),
        ("Salary and statutory details", "Maintain individual salary, PF, ESIC and bank details."),
        ("Upload attendance", "Preview a monthly or daily sheet and save verified rows."),
        ("Resolve attendance", "Confirm exceptions, incomplete punches and new employees."),
        ("Attendance and leave entry", "Record attendance, leave, holidays and overtime for a selected employee."),
        ("Payroll", "Review the salary calculation, deductions, adjustments and payroll records."),
        ("Joining and leaving", "Record joining and last working dates for attrition reporting."),
        ("Employee 360 and letters", "Open an employee profile, attendance history and warning-letter uploads."),
    ]
    with st.container(key="hr_entry_tasks"):
        columns = st.columns(3)
        for index, (label, caption) in enumerate(tasks):
            module = {
                "Employee records": "Employees", "Salary and statutory details": "Payroll",
                "Upload attendance": "Attendance", "Resolve attendance": "Attendance",
                "Attendance and leave entry": "Attendance", "Payroll": "Payroll",
                "Joining and leaving": "Employees", "Employee 360 and letters": "Employees",
                "Reports": "Reports",
            }[label]
            if not context["v5_module_allowed"](module):
                continue
            with columns[index % 3]:
                with st.container(border=True):
                    st.button(label, key=f"hr_task_{index}", width="stretch", on_click=open_task, args=(label,))
                    st.caption(caption)
    st.subheader("Employee records to complete")
    if employees.empty:
        st.info("Start with Employee records to add your first employee or upload a filled template.")
        return
    incomplete = employees.copy()
    incomplete["Needs HR action"] = incomplete.apply(
        lambda row: ", ".join(label for label, missing in [
            ("Confirm employee", str(row.department).strip().upper() == "HR REVIEW"),
            ("Joining date", pd.isna(pd.to_datetime(row.joining_date, errors="coerce"))),
            ("Salary", row.status == "Active" and (pd.isna(row.monthly_salary) or row.monthly_salary <= 0)),
            ("Bank account", not str(row.bank_account or "").strip()),
            ("UAN", row.pf_applicable and not str(row.uan_number or "").strip()),
            ("ESIC number", row.esic_applicable and not str(row.esic_number or "").strip()),
        ] if missing), axis=1,
    )
    incomplete = incomplete.loc[incomplete["Needs HR action"].ne("")]
    if incomplete.empty:
        st.info("No missing details found in these checks.")
    else:
        st.dataframe(incomplete[["employee_id", "employee_name", "division", "Needs HR action"]],
                     hide_index=True, width="stretch")
