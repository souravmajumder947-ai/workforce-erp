"""Read-only MD reports from the ERP's existing attendance and production data."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import BytesIO
import re

import pandas as pd
import streamlit as st

from simple_workforce import attrition_summary, production_cost_rows, is_post_exit_attendance_placeholder


DIVISIONS = {
    "Greater Noida Plant": "Greater Noida Plant",
    "D-63 Head Office": "Sector 63 Head Office",
    "Dhaulana Glass Plant": "Dhaulana Glass Plant",
}
LEAVE_STATUSES = {"Leave", "CL", "SL", "EL", "LWP"}
QUESTION_EXAMPLES = (
    "Give me today’s MIS",
    "Show pending HR reviews at Greater Noida",
    "Why did cost per ton change yesterday?",
    "Show attrition this month",
    "Prepare tomorrow’s review briefing",
)

JARVIS_STYLE = """
<style>
body .st-key-jarvis_launch .stButton[data-testid="stButton"] > button {
    --jarvis-edge: #64e8f7;
    position: relative;
    isolation: isolate;
    min-height: 70px !important;
    height: auto !important;
    padding: .85rem 3.1rem .85rem 4.4rem !important;
    justify-content: flex-start !important;
    text-align: left !important;
    border: 1px solid #4cd7f3 !important;
    border-radius: 16px !important;
    background:
        radial-gradient(ellipse at 10% 55%, #10496b 0%, transparent 48%),
        linear-gradient(110deg, #082940 0%, #153057 57%, #262957 100%) !important;
    color: #f3fcff !important;
    box-shadow: inset 0 0 22px #53daff22, 0 5px 22px #1dd9ff32 !important;
}
body .st-key-jarvis_launch .stButton[data-testid="stButton"] > button p {
    color: #f3fcff !important;
    font-size: clamp(1.02rem, 2vw, 1.28rem) !important;
    font-weight: 800 !important;
    letter-spacing: .025em !important;
    line-height: 1.25 !important;
}
body .st-key-jarvis_launch .stButton[data-testid="stButton"] > button::before {
    content: "";
    position: absolute;
    left: .95rem;
    top: 50%;
    width: 2.35rem;
    height: 2.35rem;
    transform: translateY(-50%);
    border-radius: 50%;
    pointer-events: none;
    background:
        radial-gradient(circle, #eaffff 0% 9%, #4ce9ff 11% 21%, #164967 23% 37%,
            transparent 39% 55%, #74f2ffbd 57% 62%, transparent 65%),
        conic-gradient(from 45deg, #68edff, transparent 22%, #547cff 50%, transparent 73%, #68edff);
    box-shadow: 0 0 18px #5be9ff66;
}
body .st-key-jarvis_launch .stButton[data-testid="stButton"] > button::after {
    content: "";
    position: absolute;
    right: 1.25rem;
    top: 50%;
    width: .55rem;
    height: .55rem;
    border-right: 2px solid var(--jarvis-edge);
    border-bottom: 2px solid var(--jarvis-edge);
    transform: translateY(-70%) rotate(45deg);
    pointer-events: none;
    opacity: 1;
}
body .st-key-jarvis_launch .stButton[data-testid="stButton"] > button:not(:disabled):hover {
    border-color: #b3f7ff !important;
    background:
        radial-gradient(ellipse at 10% 55%, #145e82 0%, transparent 55%),
        linear-gradient(110deg, #10364a 0%, #1a3e68 57%, #333064 100%) !important;
    box-shadow: inset 0 0 24px #53daff2e, 0 7px 25px #1dd9ff54 !important;
}
body .st-key-jarvis_launch .stButton[data-testid="stButton"] > button:focus-visible {
    outline: 3px solid #b4f8ff;
    outline-offset: 3px;
}
.st-key-jarvis_workspace {
    border: 1px solid #4cd7f355;
    border-radius: 14px;
    padding: .85rem 1rem;
}
@media (prefers-reduced-motion: reduce) {
    body .st-key-jarvis_launch .stButton[data-testid="stButton"] > button {
        transition: none !important;
        transform: none !important;
    }
}
</style>
"""


@dataclass(frozen=True)
class Request:
    intent: str
    day: date
    divisions: tuple[str, ...]


def interpret_question(question, selected_day, today):
    prompt = question.casefold().strip()
    if not prompt:
        raise ValueError("Enter an ERP question.")
    noida = bool(re.search(r"\b(?:greater noida|noida plant)\b", prompt))
    office = bool(re.search(r"\b(?:head office|(?:sector|sec|d)\s*-?\s*63)\b", prompt))
    glass = bool(re.search(r"\b(?:dhaulana|glass plant)\b", prompt))
    divisions = tuple(d for d,wanted in zip(DIVISIONS,(noida,office,glass)) if wanted) or tuple(DIVISIONS)

    if re.search(r"\b(?:payroll|employee salary|warning letters?|bank details|delete|approve|send|update)\b", prompt):
        raise ValueError("This assistant answers reporting questions about attendance, HR review, production, labour cost and attrition.")
    if re.search(r"\b(?:yesterday|today)\b", prompt) and re.search(r"\b(?:last month|this month)\b", prompt):
        raise ValueError("Choose a daily or monthly period for the question.")
    if re.search(r"\b(?:meeting|briefing|brief|review meeting)\b", prompt):
        intent = "briefing"
    elif re.search(r"\battrition\b", prompt):
        intent = "attrition_hr" if re.search(r"\b(?:pending|hr review|hr cases?)\b", prompt) else "attrition"
    elif re.search(r"\b(?:cost(?:\s*(?:/|per)\s*ton(?:ne)?)?|labour|labor)\b", prompt) and (
        re.search(r"\b(?:why|change[ds]?|compar\w+|ris[eo]|rose|fell|increas\w+|decreas\w+|vs)\b", prompt)
    ):
        intent = "compare_cost"
    elif re.search(r"\b(?:hr reviews?|hr cases?|pending hr|exceptions?)\b", prompt):
        intent = "hr" if re.search(r"\b(?:today|yesterday)\b|\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4}", prompt) else "hr_month"
    elif re.search(r"\b(?:mis|report|attendance|manpower|production|tonnage|cost|overview|summary)\b", prompt):
        intent = "mis"
    else:
        raise ValueError("Ask for a daily MIS, pending HR reviews, cost-per-ton comparison, monthly attrition or a review briefing.")

    day = selected_day
    if re.search(r"\byesterday\b", prompt):
        day = today - timedelta(days=1)
    elif re.search(r"\btoday\b", prompt):
        day = today
    if intent in {"attrition", "attrition_hr"} and "this month" in prompt:
        day = today
    if "last month" in prompt:
        if intent not in {"attrition", "attrition_hr"}:
            raise ValueError("Last month is supported for attrition. Choose a date for daily reports or cost comparisons.")
        day = today.replace(day=1) - timedelta(days=1)
    dates = re.findall(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})\b", prompt)
    if len(dates) > 1:
        raise ValueError("Use one report date. Cost comparisons use the previous day.")
    if dates:
        date_format = "%Y-%m-%d" if re.match(r"^\d{4}-", dates[0]) else "%d/%m/%Y"
        value = dates[0] if date_format == "%Y-%m-%d" else dates[0].replace("-", "/")
        try:
            day = datetime.strptime(value, date_format).date()
        except ValueError as exc:
            raise ValueError("Enter a valid date using DD/MM/YYYY or YYYY-MM-DD.") from exc
    if day > today or (intent != "briefing" and re.search(r"\btomorrow\b", prompt)):
        raise ValueError("Select today or a past date for ERP figures.")
    return Request(intent, day, divisions)


def attendance_rows(read, day, divisions):
    placeholders = ",".join("?" for _ in divisions)
    rows = read(
        """SELECT a.employee_id,a.work_date,a.shift,a.division,a.status,a.review_required,a.ot_hours,
                  e.monthly_salary,e.department,a.raw_status,a.time_in,a.time_out,a.working_hours,
                  COALESCE(NULLIF(a.source_issue,''),'Incomplete punch or attendance exception') AS issue,
                  e.status AS employment_status,e.division AS master_division,
                  e.joining_date::text AS joining_date,e.last_working_date::text AS last_working_date
           FROM attendance a LEFT JOIN employees e ON e.employee_id=a.employee_id
           WHERE a.work_date=? AND a.division IN (""" + placeholders + ")",
        (day.isoformat(), *divisions),
    )
    if not rows.empty:
        rows = rows.loc[[not is_post_exit_attendance_placeholder(r) for r in rows.itertuples(index=False)]].copy()
    return rows


def attendance_summary(attendance, divisions):
    summary = []
    for division in divisions:
        rows = attendance[attendance.division == division]
        pending = rows.status.eq("HR Review") | rows.review_required.eq(True)
        verified = rows.loc[~pending]
        summary.append({
            "Location": DIVISIONS[division],
            "Attendance rows": len(rows),
            "Present / OD": int(verified.status.isin({"Present", "OD"}).sum()),
            "Half day": int(verified.status.eq("Half Day").sum()),
            "Absent": int(verified.status.eq("Absent").sum()),
            "Leave": int(verified.status.isin(LEAVE_STATUSES).sum()),
            "Weekly off / Holiday": int(verified.status.isin({"WO", "Holiday"}).sum()),
            "OT hours": round(float(pd.to_numeric(verified.ot_hours, errors="coerce").sum()), 2),
            "Pending HR review": int(pending.sum()),
            "Attendance coverage": "Recorded" if len(rows) else "No attendance recorded",
        })
    return pd.DataFrame(summary)


def daily_mis(read, day, divisions):
    attendance = attendance_rows(read, day, divisions)
    placeholders = ",".join("?" for _ in divisions)
    output = read(
        """SELECT o.work_date,o.division,o.shift,o.machine,o.output_ton,o.employee_ids,
                  o.contractor_headcount,o.contractor_cost,COALESCE(t.target_ton,m.target_ton) AS target_ton
           FROM workforce_daily_output o
           LEFT JOIN machines m ON m.machine=o.machine
           LEFT JOIN machine_shift_targets t ON t.machine=o.machine AND t.shift=o.shift
           WHERE o.work_date=? AND o.division IN (""" + placeholders + ")"
        + " ORDER BY o.division,o.machine,o.shift",
        (day, *divisions),
    )
    production = pd.DataFrame()
    if not output.empty:
        production = production_cost_rows(output, attendance)
        production["Contractor cost (₹)"] = output.contractor_cost.astype(float).to_numpy()
        targets = pd.to_numeric(output.target_ton, errors="coerce")
        production["Target (tons)"] = targets.where(targets.gt(0)).to_numpy()
        production["Variance (tons)"] = (production["Tons"] - production["Target (tons)"]).round(2)
        production["Target achieved (%)"] = (100 * production["Tons"] / production["Target (tons)"]).round(1)
        production["Division"] = production["Division"].map(DIVISIONS)
        production = production.drop(columns=["Date"]).rename(columns={"Division": "Location"})
        # Employee codes in the operational report's diagnostic messages are not needed in an MD export.
        production["Action"] = production["Action"].replace(
            r"^Check attendance/salary:.*$", "Check attendance and salary in Cost & Attrition", regex=True,
        )
    return attendance_summary(attendance, divisions), production


def compare_cost(read, day, divisions):
    previous = day - timedelta(days=1)
    _, current = daily_mis(read, day, divisions)
    _, earlier = daily_mis(read, previous, divisions)
    if current.empty or earlier.empty:
        return pd.DataFrame()
    keys = ["Location", "Machine", "Shift"]
    joined = current.merge(earlier, how="inner", on=keys, suffixes=(" current", " previous"))
    joined = joined.dropna(subset=["Cost/ton (₹) current", "Cost/ton (₹) previous"])
    result = joined[keys].copy()
    for name in ("Cost/ton (₹)", "Tons", "Labour cost (₹)", "Contractor cost (₹)"):
        result[f"Current {name}"] = joined[f"{name} current"]
        result[f"Previous {name}"] = joined[f"{name} previous"]
        result[f"Change in {name}"] = joined[f"{name} current"] - joined[f"{name} previous"]
    return result.round(2)


def attrition_rows(read, day, divisions):
    start = day.replace(day=1)
    result = []
    for division in divisions:
        employees = read(
            """SELECT employee_id,department,joining_date,last_working_date,status
               FROM employees WHERE division=?""", (division,),
        )
        metrics = attrition_summary(employees.to_dict("records"), start, day)
        issues = len(metrics["issues"])
        result.append({
            "Location": DIVISIONS[division],
            "Opening headcount": None if issues else metrics["opening"],
            "Closing headcount": None if issues else metrics["closing"],
            "Employees who left": None if issues else metrics["leavers"],
            "Attrition (%)": None if metrics["rate"] is None else round(metrics["rate"], 2),
            "Employees with missing or invalid employment dates": issues,
        })
    return pd.DataFrame(result)


def monthly_hr_rows(read, day, divisions):
    placeholders = ",".join("?" for _ in divisions)
    rows = read(
        """SELECT a.work_date,a.division,a.raw_status,a.time_in,a.time_out,a.working_hours,a.ot_hours,
                  COALESCE(NULLIF(a.source_issue,''),'Incomplete punch or attendance exception') AS issue,
                  e.status AS employment_status,e.division AS master_division,
                  e.joining_date::text AS joining_date,e.last_working_date::text AS last_working_date
           FROM attendance a LEFT JOIN employees e ON e.employee_id=a.employee_id
           WHERE a.work_date BETWEEN ? AND ? AND (a.status='HR Review' OR a.review_required=TRUE)
           AND a.division IN (""" + placeholders + ")",
        (day.replace(day=1).isoformat(), day.isoformat(), *divisions),
    )
    by_division = {}
    for r in rows.itertuples(index=False):
        if not is_post_exit_attendance_placeholder(r):
            by_division[r.division] = by_division.get(r.division,0)+1
    return pd.DataFrame([{"Location": DIVISIONS[d], "Pending HR review": int(by_division.get(d, 0))} for d in divisions])


def mis_excel(day, attendance, production):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        notes = pd.DataFrame([
            ("Daily MIS", day.strftime("%d %b %Y")),
            ("Attendance", "Attendance rows are counted by shift. Blank uploads are shown as no attendance recorded."),
            ("Production", "Source: Daily Production & Manpower entries. Tonnage is kept separate by machine and shift."),
            ("Labour cost", "Source: Cost & Attrition. Blank costs indicate incomplete data or zero output."),
        ], columns=["Item", "Details"])
        notes.to_excel(writer, sheet_name="Report information", index=False)
        attendance.to_excel(writer, sheet_name="Attendance", index=False)
        if production.empty:
            production = pd.DataFrame({"Production": ["No daily production entries recorded for this scope."]})
        production.to_excel(writer, sheet_name="Production and cost", index=False)
        for sheet in writer.sheets.values():
            sheet.freeze_panes = "B2"
            for col in sheet.columns:
                for cell in col:
                    if sheet.title == "Production and cost" and cell.data_type == "n":
                        if col[0].value in {"Tons", "Target (tons)", "Variance (tons)"}:
                            cell.number_format = "#,##0"
                        elif col[0].value in {"Labour cost (₹)", "Contractor cost (₹)", "Cost/ton (₹)"}:
                            cell.number_format = "#,##0.00"
                    if cell.data_type == "f":
                        cell.data_type = "s"
                max_width = 100 if sheet.title == "Report information" else 52
                sheet.column_dimensions[col[0].column_letter].width = min(
                    max_width, max(13, max(len(str(cell.value or "")) for cell in col) + 2),
                )
    return buffer.getvalue()


def render_response(read, request):
    st.caption(f"ERP figures through {request.day:%d %b %Y} · " + ", ".join(DIVISIONS[d] for d in request.divisions))
    if request.intent in {"attrition", "attrition_hr"}:
        st.markdown("**Monthly attrition**")
        st.caption(f"{request.day.replace(day=1):%d %b} to {request.day:%d %b %Y} · Source: Cost & Attrition and employee joining/leaving dates")
        st.dataframe(attrition_rows(read, request.day, request.divisions), hide_index=True, width="stretch")
        if request.intent == "attrition_hr":
            st.markdown("**Pending HR review this month**")
            st.dataframe(monthly_hr_rows(read, request.day, request.divisions), hide_index=True, width="stretch")
        return
    if request.intent == "compare_cost":
        st.markdown("**Labour cost per ton comparison**")
        previous = request.day - timedelta(days=1)
        st.caption(f"{request.day:%d %b %Y} versus {previous:%d %b %Y} · Source: Cost & Attrition")
        comparison = compare_cost(read, request.day, request.divisions)
        if comparison.empty:
            st.info("No matching machine and shift has a complete cost per ton on both dates.")
        else:
            st.caption("Compare output tons, total labour cost and contractor cost for each matching machine and shift.")
            biggest = comparison["Change in Cost/ton (₹)"].abs().idxmax()
            row = comparison.loc[biggest]
            st.text(
                f"{row['Location']} · {row['Machine']} · Shift {row['Shift']}: "
                f"cost per ton ₹{row['Previous Cost/ton (₹)']:,.2f} → ₹{row['Current Cost/ton (₹)']:,.2f}. "
                f"Output {row['Previous Tons']:,.2f} → {row['Current Tons']:,.2f} t. "
                f"Labour cost ₹{row['Previous Labour cost (₹)']:,.2f} → ₹{row['Current Labour cost (₹)']:,.2f}."
            )
            st.dataframe(comparison, hide_index=True, width="stretch")
        return
    if request.intent == "hr_month":
        st.markdown("**Pending HR review this month**")
        st.dataframe(monthly_hr_rows(read, request.day, request.divisions),hide_index=True,width="stretch")
        return
    if request.intent == "hr":
        attendance = attendance_summary(attendance_rows(read, request.day, request.divisions), request.divisions)
        st.markdown("**Pending HR review**")
        st.caption("Source: Attendance and HR Review")
        st.dataframe(attendance[["Location", "Pending HR review", "Attendance coverage"]],
                     hide_index=True, width="stretch")
        return
    attendance, production = daily_mis(read, request.day, request.divisions)
    if request.intent == "briefing":
        st.markdown("**MD review briefing**")
        for row in attendance.to_dict("records"):
            location = row["Location"]
            st.text(f"{location}: {row['Pending HR review']} pending HR review rows. Attendance: {row['Attendance coverage'].lower()}.")
        if not production.empty:
            count = int(production.Action.ne("Complete").sum())
            st.text(f"{count} machine-shift entries need an output, attendance or salary check.")
    else:
        st.markdown("**Daily MIS**")
    st.caption("Attendance counts are shift rows. Sources: Attendance, Daily Production & Manpower, Cost & Attrition.")
    st.dataframe(attendance, hide_index=True, width="stretch", key="md_assistant_attendance")
    if production.empty:
        st.info("No daily production entries for this date and scope.")
    else:
        locations_without_output = [DIVISIONS[d] for d in request.divisions if DIVISIONS[d] not in production["Location"].values]
        if locations_without_output:
            st.info("No daily production entries for " + ", ".join(locations_without_output) + ".")
        st.caption("Tonnage is shown by machine and shift. The same material can pass through multiple stages.")
        config = {name: st.column_config.NumberColumn(format="%.2f")
                  for name in ("Labour cost (₹)", "Contractor cost (₹)", "Cost/ton (₹)")}
        config.update({name: st.column_config.NumberColumn(format="%.0f")
                       for name in ("Tons", "Target (tons)", "Variance (tons)")})
        st.dataframe(production, hide_index=True, width="stretch", column_config=config, key="md_assistant_production")
    st.download_button("Download MIS Excel", mis_excel(request.day, attendance, production),
                       file_name=f"Workforce_MIS_{request.day.isoformat()}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore")


def render_md_assistant(read, today, username):
    st.caption("Greater Noida Plant and Sector 63 Head Office")
    selected_day = st.date_input("MIS report date", value=today, max_value=today, key="md_assistant_date")
    state_key = f"md_assistant_request_{username}"
    if st.button("Generate Daily MIS", type="primary"):
        st.session_state[state_key] = Request("mis", selected_day, tuple(DIVISIONS))
    with st.form("md_assistant_question_form"):
        question = st.text_input("Ask MD Assistant", max_chars=250, placeholder="Why did cost per ton change yesterday?")
        submitted = st.form_submit_button("Ask")
    st.caption("Try " + " · ".join(QUESTION_EXAMPLES))
    if submitted:
        try:
            st.session_state[state_key] = interpret_question(question, selected_day, today)
        except ValueError as exc:
            st.session_state.pop(state_key, None)
            st.info(str(exc))
    request = st.session_state.get(state_key)
    if request:
        render_response(read, request)


def render_jarvis_launcher(read, today, username, *, reports_access, employee_access, payroll_access, warning_access, selected_month=None, selected_division=None):
    state_key = f"jarvis_open_{username}"
    is_open = st.session_state.get(state_key, False)

    def toggle():
        st.session_state[state_key] = not st.session_state.get(state_key, False)

    st.html(JARVIS_STYLE)
    with st.container(key="jarvis_launch"):
        st.button(
            "Close JARVIS" if is_open else "JARVIS · MD Assistant",
            key=f"jarvis_launcher_{username}", width="stretch", on_click=toggle,
        )
        if not is_open:
            st.caption("Ask about attendance, production, labour cost or employee records.")
    if is_open:
        with st.container(key="jarvis_workspace"):
            if not (reports_access or employee_access):
                st.info("Ask your ERP admin for Reports or Employee Master access to use JARVIS.")
                return

            from jarvis_employee import employee_sections, find_employee, render_employee_answer, reporting_period

            from calendar import monthrange
            default_day = min(today, selected_month.replace(day=monthrange(selected_month.year,selected_month.month)[1])) if selected_month else today
            scope = (selected_division,) if selected_division in DIVISIONS else tuple(DIVISIONS)
            selected = st.date_input("Reporting date", value=default_day, max_value=today, key=f"jarvis_date_{username}_{default_day}")
            st.caption("Default reporting scope: " + ", ".join(DIVISIONS[d] for d in scope))
            answer_key = f"jarvis_answer_{username}"
            if reports_access:
                briefing, mis = st.columns(2)
                if briefing.button("What needs attention?", key=f"jarvis_briefing_{username}"):
                    st.session_state[answer_key] = ("report", Request("briefing", selected, scope))
                if mis.button("Generate Daily MIS", key=f"jarvis_mis_{username}"):
                    st.session_state[answer_key] = ("report", Request("mis", selected, scope))
            with st.form(f"jarvis_ask_{username}"):
                question = st.text_input("Ask JARVIS", max_chars=250,
                                         placeholder="Employee: Sourav Majumder | performance 2026-10")
                submitted = st.form_submit_button("Ask JARVIS", type="primary")
            if reports_access:
                st.caption("Try “Show pending HR reviews at Greater Noida” or “Show attrition this month”.")
            if employee_access:
                st.caption("For an employee, use Employee: full name or ID | question. The reporting date selects the month unless you specify one.")
            if submitted:
                st.session_state.pop(answer_key, None)
                try:
                    if not question.strip():
                        raise ValueError("Enter a question for JARVIS.")
                    if question.strip().lower().startswith("employee:") or not reports_access:
                        if not employee_access:
                            raise ValueError("This account does not have Employee Master access.")
                        identity, separator, prompt = question.strip().removeprefix("Employee:").partition("|")
                        identity = re.sub(r"^employee:\s*", "", identity, flags=re.I).strip()
                        if not identity or not separator:
                            raise ValueError("Use Employee: full name or ID | question.")
                        start, end = reporting_period(prompt, selected, today)
                        st.session_state[answer_key] = ("employee", (identity, employee_sections(prompt), start, end))
                    else:
                        request = interpret_question(question, selected, today)
                        if not re.search(r"\b(?:greater noida|noida plant|head office|dhaulana|glass plant|(?:sector|sec|d)\s*-?\s*63)\b", question, re.I):
                            request = Request(request.intent,request.day,scope)
                        st.session_state[answer_key] = ("report", request)
                except ValueError as exc:
                    st.info(str(exc))
            answer = st.session_state.get(answer_key)
            if not answer:
                return
            kind, request = answer
            if kind == "report" and reports_access:
                render_response(read, request)
            elif kind == "employee" and employee_access:
                identity, sections, start, end = request
                matches = find_employee(read, identity, tuple(DIVISIONS))
                if matches.empty:
                    st.info("No matching employee in the ERP divisions.")
                    return
                exact = matches.employee_id.astype(str).str.strip().str.casefold().eq(identity.casefold())
                if exact.any():
                    matches = matches.loc[exact]
                if len(matches) != 1:
                    st.info("Multiple employees match. Use the employee ID.")
                    return
                render_employee_answer(read, next(matches.itertuples(index=False)), sections, start, end,
                                       payroll_access, warning_access)
