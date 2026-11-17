"""Employee 360 questions backed by scoped ERP records."""
from calendar import monthrange
from datetime import datetime, timedelta
from difflib import get_close_matches
import re

import pandas as pd
import streamlit as st


def reporting_period(question, selected, today):
    dates = re.findall(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})\b", question)
    if len(dates) > 1:
        raise ValueError("Enter one date or choose a reporting month.")
    if dates:
        raw = dates[0]
        iso = bool(re.match(r"^\d{4}-", raw))
        try:
            day = datetime.strptime(raw if iso else raw.replace("-", "/"), "%Y-%m-%d" if iso else "%d/%m/%Y").date()
        except ValueError as exc:
            raise ValueError("Enter a valid date as DD/MM/YYYY or YYYY-MM-DD.") from exc
        if day > today:
            raise ValueError("Choose today or an earlier date.")
        return day, day
    if re.search(r"\byesterday\b", question, re.I):
        day = today - timedelta(days=1)
        return day, day
    if re.search(r"\btoday\b", question, re.I):
        return today, today
    if re.search(r"\blast month\b", question, re.I):
        selected = today.replace(day=1) - timedelta(days=1)
    elif re.search(r"\bthis month\b", question, re.I):
        selected = today
    months = re.findall(r"\b\d{4}-(?:0[1-9]|1[0-2])\b(?!-\d)", question)
    if months:
        selected = datetime.strptime(months[0], "%Y-%m").date()
    if selected.replace(day=1) > today:
        raise ValueError("Choose the current month or an earlier reporting month.")
    end = selected.replace(day=monthrange(selected.year, selected.month)[1])
    return selected.replace(day=1), min(end, today)


def employee_sections(question):
    question = question.strip().lower()
    vocabulary = ("performance", "attendance", "overtime", "production", "profile", "salary", "warnings")

    def correct_word(match):
        word = match.group()
        candidates = get_close_matches(word, vocabulary, n=1, cutoff=0.82)
        return candidates[0] if candidates else word

    question = re.sub(r"[a-z]{5,}", correct_word, question)
    sections = set()
    filters = {
        "profile": r"\b(?:profile|details|overview|designation|department|status|joining|joined)\b",
        "attendance": r"\b(?:attendance|absen\w*|present|leave|ot|overtime|punch\w*|work(?:ing|ed) hours)\b",
        "work": r"\b(?:production|machines?|assignments?|work history|tonnage|output)\b",
        "payroll": r"\b(?:payroll|salary|pay|net pay|payslip|earnings)\b",
        "warnings": r"\b(?:warnings?|disciplin\w*)\b",
    }
    if re.search(r"\b(?:performance|perfomacance|summary|everything|360)\b", question) or not question:
        sections.update(("profile", "attendance", "work"))
    sections.update(name for name, pattern in filters.items() if re.search(pattern, question))
    if re.search(r"\b(?:everything|360)\b", question):
        sections.update(("payroll", "warnings"))
    if not sections:
        raise ValueError("Ask about the employee’s profile, attendance, overtime, machine assignments, payroll, or warning history.")
    return sections


def find_employee(read, value, divisions):
    return read(
        """SELECT employee_id,employee_name,division,department,designation,status,joining_date,last_working_date
           FROM employees WHERE division IN (?,?)
           AND (LOWER(TRIM(employee_id))=LOWER(?) OR LOWER(TRIM(employee_name))=LOWER(?))
           ORDER BY CASE WHEN LOWER(TRIM(employee_id))=LOWER(?) THEN 0 ELSE 1 END,employee_id""",
        (*divisions, value, value, value),
    )


def load_attendance(read, employee, start, end):
    rows = read(
        """SELECT work_date,shift,status,working_hours,ot_hours,review_required
           FROM attendance WHERE employee_id=? AND division=? AND work_date BETWEEN ? AND ?
           ORDER BY work_date,shift""",
        (employee.employee_id, employee.division, start.isoformat(), end.isoformat()),
    )
    pending = rows.status.eq("HR Review") | rows.review_required.eq(True)
    verified = rows.loc[~pending]
    counts = verified.status.value_counts()
    return rows, {
        "Attendance rows": len(rows),
        "Present / OD": int(counts.get("Present", 0) + counts.get("OD", 0)),
        "Half days": int(counts.get("Half Day", 0)),
        "Absent": int(counts.get("Absent", 0)),
        "Leave": int(verified.status.isin({"Leave", "CL", "SL", "EL", "LWP"}).sum()),
        "Overtime hours": round(float(pd.to_numeric(verified.ot_hours, errors="coerce").sum()), 2),
        "Pending HR review": int(pending.sum()),
    }


def load_work(read, employee, start, end):
    start_text, end_text = start.isoformat(), end.isoformat()
    return read(
        """WITH daily AS (
               SELECT o.work_date::text AS work_date,o.shift,o.machine,'Assigned' AS role,
                      o.output_ton AS machine_output_tons,'Daily Production' AS source
               FROM workforce_daily_output o
               WHERE o.division=? AND o.work_date::text BETWEEN ? AND ?
               AND jsonb_exists(o.employee_ids::jsonb, ?)
           ), detailed AS (
               SELECT ma.work_date::text AS work_date,ma.shift,ma.machine,ma.role,
                      p.production_ton AS machine_output_tons,'Detailed Allocation' AS source
               FROM manpower_allocation ma
               LEFT JOIN production p
                 ON p.work_date=ma.work_date AND p.shift=ma.shift AND p.machine=ma.machine
               WHERE ma.employee_id=? AND ma.work_date::text BETWEEN ? AND ?
               AND EXISTS (
                   SELECT 1 FROM attendance a WHERE a.employee_id=ma.employee_id AND a.division=?
                   AND a.work_date::text=ma.work_date::text AND a.shift=ma.shift
               )
           )
           SELECT * FROM daily
           UNION ALL
           SELECT d.* FROM detailed d WHERE NOT EXISTS (
               SELECT 1 FROM daily o WHERE (o.work_date,o.shift,o.machine)=(d.work_date,d.shift,d.machine)
           )
           ORDER BY work_date DESC,shift,machine""",
        (employee.division, start_text, end_text, employee.employee_id, employee.employee_id,
         start_text, end_text, employee.division),
    )


def render_employee_answer(read, employee, sections, start, end, can_payroll, can_warnings):
    st.subheader(f"{employee.employee_name} · {employee.employee_id}")
    st.caption(f"{employee.division} · {start:%d %b} to {end:%d %b %Y}")
    if "profile" in sections:
        st.markdown("**Employee profile**")
        st.text(f"{employee.designation} · {employee.department} · {employee.status}")
        st.text(f"Joined: {employee.joining_date or 'Date missing'}")
        if employee.last_working_date:
            st.text(f"Last working date: {employee.last_working_date}")
        st.caption("Source: Employee Master")
    if "attendance" in sections:
        st.markdown("**Attendance and overtime**")
        rows, facts = load_attendance(read, employee, start, end)
        if rows.empty:
            st.info("No attendance records are available for this period.")
        else:
            st.dataframe(pd.DataFrame([facts]), hide_index=True, width="stretch")
            with st.expander("Daily attendance records"):
                st.dataframe(rows, hide_index=True, width="stretch")
        st.caption("Source: Attendance and HR Review. Counts are attendance rows by shift.")
    if "work" in sections:
        st.markdown("**Machine assignments and output**")
        rows = load_work(read, employee, start, end)
        if rows.empty:
            st.info("No machine assignments are recorded in this period.")
        else:
            st.text(f"{len(rows)} records across {rows.machine.nunique()} machines.")
            st.dataframe(rows, hide_index=True, width="stretch")
        st.caption("Sources: Daily Production, Manpower Allocation. Output is for the machine and shift.")
    if "payroll" in sections:
        st.markdown("**Recorded payroll**")
        if can_payroll:
            st.caption(f"Payroll month: {start:%B %Y}")
            rows = read(
                """SELECT payroll_month,paid_days,ot_hours,gross_earned,ot_pay,net_payable,payroll_status
                   FROM payroll_records WHERE employee_id=? AND division=? AND payroll_month=?""",
                (employee.employee_id, employee.division, start.strftime("%Y-%m")),
            )
            if rows.empty:
                st.info("No payroll record has been saved for this month.")
            else:
                st.dataframe(rows.round(2), hide_index=True, width="stretch")
            st.caption("Source: Saved Payroll Records")
        else:
            st.info("This account does not have payroll access.")
    if "warnings" in sections:
        st.markdown("**Warning letter history**")
        if can_warnings:
            rows = read(
                """SELECT issue_date,subject,warning_type,reference_no,reason,required_action
                   FROM employee_warning_letters WHERE employee_id=? AND issue_date BETWEEN ? AND ?
                   ORDER BY issue_date DESC,warning_id DESC""",
                (employee.employee_id, start, end),
            )
            if rows.empty:
                st.info("No warning letters are recorded in this period.")
            else:
                st.dataframe(rows, hide_index=True, width="stretch")
            st.caption("Source: Employee 360° → Warning Letters")
        else:
            st.info("This account does not have warning-letter access.")


def render_employee_questions(read, today, username, divisions, can_payroll, can_warnings):
    key = f"jarvis_employee_request_{username}"
    with st.form(f"jarvis_employee_questions_{username}"):
        identity = st.text_input("Employee ID or full name", max_chars=100)
        selected = st.date_input("Employee reporting month", value=today, max_value=today,
                                 help="Pick any date in the month to review.")
        question = st.text_input("Ask about this employee", max_chars=250,
                                 placeholder="Show performance, attendance and machine assignments")
        submitted = st.form_submit_button("Ask JARVIS about employee", type="primary")
    if submitted:
        st.session_state.pop(key, None)
        if not identity.strip():
            st.info("Enter the employee ID or full name.")
            return
        try:
            start, end = reporting_period(question, selected, today)
            sections = employee_sections(question)
        except ValueError as exc:
            st.info(str(exc))
            return
        st.session_state[key] = (identity.strip(), sections, start, end)
    request = st.session_state.get(key)
    if not request:
        return
    identity, sections, start, end = request
    matches = find_employee(read, identity, divisions)
    if matches.empty:
        st.info("No matching employee in Greater Noida Plant or Sector 63 Head Office.")
        return
    exact_id = matches.employee_id.astype(str).str.strip().str.casefold().eq(identity.casefold())
    if exact_id.any():
        matches = matches.loc[exact_id]
    if len(matches) != 1:
        st.info("Multiple employees have that name. Enter the employee ID to select the correct record.")
        return
    render_employee_answer(read, next(matches.itertuples(index=False)), sections, start, end,
                           can_payroll, can_warnings)
