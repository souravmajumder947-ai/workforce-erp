from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

old1 = '''    total_emp=len(emp_all)
    present=int((att["status"]=="Present").sum()) if not att.empty else 0
    attendance_pct=(present/total_emp*100) if total_emp else 0
    net=float(pay["Net Payable"].sum()) if not pay.empty else 0
'''
new1 = '''    total_emp=len(emp_all)
    att_status = att["status"].fillna("").astype(str).str.strip() if not att.empty else pd.Series(dtype=str)
    present = int((att_status == "Present").sum())
    half_day = int((att_status == "Half Day").sum())
    paid_off = int(att_status.isin(["WO","Holiday","Leave","CL","SL","EL"]).sum())
    absent_today = int(att_status.isin(["Absent","LWP"]).sum())
    review_today = int((att_status == "HR Review").sum())
    attendance_records = int(att["employee_id"].astype(str).nunique()) if not att.empty else 0
    # Management coverage treats approved weekly off / paid leave as covered days.
    # This avoids showing a misleading near-zero attendance percentage on Sundays/holidays.
    covered_today = present + (0.5 * half_day) + paid_off
    attendance_pct=(covered_today/total_emp*100) if total_emp else 0
    net=float(pay["Net Payable"].sum()) if not pay.empty else 0
'''
if old1 not in text:
    raise SystemExit('Management KPI block not found')
text = text.replace(old1, new1, 1)

old2 = '''        ("Attendance",f"{attendance_pct:.1f}%","Present / active","good" if attendance_pct>=85 else "warn"),
'''
new2 = '''        ("Attendance Coverage",f"{attendance_pct:.1f}%",f"Present {present:,} · WO/Leave {paid_off:,} · Review {review_today:,}","good" if attendance_pct>=85 else "warn"),
'''
if old2 not in text:
    raise SystemExit('Attendance KPI card line not found')
text = text.replace(old2, new2, 1)

old3 = '''    div_rows=[]
    for div in DIVISIONS:
        e=v5_active_employees(div)
        a=v5_attendance_for_date(global_work_date,div)
        p=calculate_live_payroll(global_payroll_month,div) if can_view_salary(_current_role) else pd.DataFrame()
        latest=read_df("SELECT MAX(work_date) AS latest FROM attendance WHERE division=?",(div,))
        latest_value = latest.iloc[0]["latest"] if not latest.empty and latest.iloc[0]["latest"] else "Not uploaded"
        div_rows.append({
            "Division":div,
            "Employees":len(e),
            "Present":int((a["status"]=="Present").sum()) if not a.empty else 0,
            "Absent/LWP":int(a["status"].isin(["Absent","LWP"]).sum()) if not a.empty else 0,
            "HR Review":int((a["status"]=="HR Review").sum()) if not a.empty else 0,
            "Latest Attendance":latest_value,
            "Gross Earned":float(p["Gross Earned"].sum()) if not p.empty else 0,
            "Net Payable":float(p["Net Payable"].sum()) if not p.empty else 0,
            "Payroll Exceptions":int(((p["HR Review"]>0)|(p["Missing Days"]>0)).sum()) if not p.empty else 0,
        })
'''
new3 = '''    div_rows=[]
    for div in DIVISIONS:
        e=v5_active_employees(div)
        a=v5_attendance_for_date(global_work_date,div)
        p=calculate_live_payroll(global_payroll_month,div) if can_view_salary(_current_role) else pd.DataFrame()
        latest=read_df("SELECT MAX(work_date) AS latest FROM attendance WHERE division=?",(div,))
        latest_value = latest.iloc[0]["latest"] if not latest.empty and latest.iloc[0]["latest"] else "Not uploaded"
        a_status = a["status"].fillna("").astype(str).str.strip() if not a.empty else pd.Series(dtype=str)
        a_present = int((a_status == "Present").sum())
        a_half = int((a_status == "Half Day").sum())
        a_off = int(a_status.isin(["WO","Holiday","Leave","CL","SL","EL"]).sum())
        a_absent = int(a_status.isin(["Absent","LWP"]).sum())
        a_review = int((a_status == "HR Review").sum())
        a_records = int(a["employee_id"].astype(str).nunique()) if not a.empty else 0
        a_missing = max(len(e) - a_records, 0)
        a_coverage = ((a_present + 0.5*a_half + a_off) / len(e) * 100.0) if len(e) else 0.0
        div_rows.append({
            "Division":div,
            "Employees":len(e),
            "Records":a_records,
            "Present":a_present,
            "Half Day":a_half,
            "WO/Leave":a_off,
            "Absent/LWP":a_absent,
            "HR Review":a_review,
            "Missing":a_missing,
            "Coverage %":a_coverage,
            "Latest Attendance":latest_value,
            "Gross Earned":float(p["Gross Earned"].sum()) if not p.empty else 0,
            "Net Payable":float(p["Net Payable"].sum()) if not p.empty else 0,
            "Payroll Exceptions":int(((p["HR Review"]>0)|(p["Missing Days"]>0)).sum()) if not p.empty else 0,
        })
'''
if old3 not in text:
    raise SystemExit('Management division block not found')
text = text.replace(old3, new3, 1)

old4 = '''                    "Gross Earned":st.column_config.NumberColumn("Gross Earned",format="₹%.2f"),
                    "Net Payable":st.column_config.NumberColumn("Net Payable",format="₹%.2f"),
'''
new4 = '''                    "Coverage %":st.column_config.NumberColumn("Coverage %",format="%.1f%%"),
                    "Gross Earned":st.column_config.NumberColumn("Gross Earned",format="₹%.2f"),
                    "Net Payable":st.column_config.NumberColumn("Net Payable",format="₹%.2f"),
'''
if old4 not in text:
    raise SystemExit('Management division column config not found')
text = text.replace(old4, new4, 1)

p.write_text(text, encoding='utf-8')
print('Management attendance dashboard patch applied')
