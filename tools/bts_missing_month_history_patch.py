from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

old = '''        missing_attendance = read_df(
            """SELECT e.division,e.employee_id,e.employee_name,e.department,e.designation,e.shift
               FROM employees e
               LEFT JOIN attendance a
                 ON a.employee_id=e.employee_id
                AND a.work_date=?
               WHERE e.status='Active' AND a.id IS NULL """ + missing_clause + """
               ORDER BY e.division,e.employee_name""",
            (missing_reference_date.isoformat(),) + missing_params
        )
'''
new = '''        missing_attendance = read_df(
            """SELECT e.division,e.employee_id,e.employee_name,e.department,e.designation,e.shift
               FROM employees e
               LEFT JOIN attendance a
                 ON a.employee_id=e.employee_id
                AND a.work_date=?
               WHERE e.status='Active' AND a.id IS NULL """ + missing_clause + """
               ORDER BY e.division,e.employee_name""",
            (missing_reference_date.isoformat(),) + missing_params
        )

        # Help HR understand WHY an active employee is missing on the selected BTS date.
        # This is read-only analysis: it does not create or change attendance.
        missing_month_start = missing_reference_date.replace(day=1)
        history_clause, history_params = v5_division_clause(global_division, "a.")
        missing_month_history = read_df(
            """SELECT a.division,a.employee_id,
                      COUNT(DISTINCT a.work_date) AS month_days_found,
                      MAX(a.work_date) AS last_attendance_date
               FROM attendance a
               WHERE a.work_date BETWEEN ? AND ? """ + history_clause + """
               GROUP BY a.division,a.employee_id""",
            (missing_month_start.isoformat(), missing_reference_date.isoformat()) + history_params
        )
        if not missing_attendance.empty:
            if missing_month_history.empty:
                missing_attendance["month_days_found"] = 0
                missing_attendance["last_attendance_date"] = None
            else:
                missing_attendance = missing_attendance.merge(
                    missing_month_history,
                    on=["division", "employee_id"],
                    how="left"
                )
            missing_attendance["month_days_found"] = (
                pd.to_numeric(missing_attendance["month_days_found"], errors="coerce").fillna(0).astype(int)
            )
            missing_attendance["source_pattern"] = missing_attendance["month_days_found"].apply(
                lambda n: "Seen earlier this month" if int(n) > 0 else "No attendance row this month"
            )
            missing_attendance["last_attendance_display"] = pd.to_datetime(
                missing_attendance["last_attendance_date"], errors="coerce"
            ).dt.strftime("%d/%m/%Y").fillna("—")
'''
if old not in text:
    raise SystemExit('missing attendance query anchor not found')
text = text.replace(old, new, 1)

old = '''                st.info(
                    f"BTS source check for **{missing_reference_date.strftime('%d %b %Y')}** — {missing_division_text}. "
                    "These employees are active in Employee Master but have no attendance row from the current BTS/imported source for this date. "
                    "Do not mark them Absent in bulk without HR verification."
                )
                ma = missing_attendance.rename(columns={
                    "division":"Division","employee_id":"Employee ID","employee_name":"Employee Name",
                    "department":"Department","designation":"Designation","shift":"Shift"
                }).copy()
                ma.insert(0,"Select",False)
                ma["Date"] = global_work_date.strftime("%d/%m/%Y")
'''
new = '''                st.info(
                    f"BTS source check for **{missing_reference_date.strftime('%d %b %Y')}** — {missing_division_text}. "
                    "These employees are active in Employee Master but have no attendance row from the current BTS/imported source for this date. "
                    "Do not mark them Absent in bulk without HR verification."
                )
                seen_earlier_count = int((missing_attendance["source_pattern"] == "Seen earlier this month").sum())
                no_month_row_count = int((missing_attendance["source_pattern"] == "No attendance row this month").sum())
                st.caption(
                    f"Monthly source history: **{seen_earlier_count:,}** were seen on earlier date(s) this month; "
                    f"**{no_month_row_count:,}** have no attendance row anywhere in this month. "
                    "Use this only as an HR investigation aid — neither category is automatically Absent."
                )
                ma = missing_attendance.rename(columns={
                    "division":"Division","employee_id":"Employee ID","employee_name":"Employee Name",
                    "department":"Department","designation":"Designation","shift":"Shift",
                    "source_pattern":"Source Pattern","month_days_found":"Days Found This Month",
                    "last_attendance_display":"Last Attendance"
                }).copy()
                ma.insert(0,"Select",False)
                ma["Date"] = missing_reference_date.strftime("%d/%m/%Y")
                ma = ma.drop(columns=["last_attendance_date"], errors="ignore")
'''
if old not in text:
    raise SystemExit('missing BTS UI anchor not found')
text = text.replace(old, new, 1)

p.write_text(text, encoding='utf-8')
