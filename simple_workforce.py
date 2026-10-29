"""Daily workforce workflow. Existing authentication and master data stay authoritative."""
import json
from calendar import monthrange
from datetime import date, datetime

import pandas as pd
import streamlit as st


INACTIVE = {"INACTIVE", "LEFT", "RESIGNED", "TERMINATED"}
PAID = {"Present", "OD", "Half Day", "WO", "Holiday", "CL", "SL", "EL", "Leave"}


def employment_date(value):
    raw = str(value or '').strip()
    iso = len(raw) >= 10 and raw[:4].isdigit() and raw[4] == '-'
    return pd.to_datetime(value, errors='coerce', dayfirst=not iso)


def labour_amount(salary, day, status, ot_hours):
    daily = float(salary) / monthrange(day.year, day.month)[1]
    factor = 0.5 if status == "Half Day" else (1.0 if status in PAID else 0.0)
    return daily * factor + (daily / 12 * max(0.0, float(ot_hours)) if status in {"Present", "OD", "Half Day"} else 0.0)


def attrition_summary(employees, start, end):
    """Opening = immediately before period; closing = after last-day departures."""
    opening = closing = leavers = 0
    issues = []
    for employee in employees:
        if str(employee.get("department", "")).strip().upper() == "HR REVIEW":
            continue
        joined = employment_date(employee.get("joining_date"))
        left = pd.to_datetime(employee.get("last_working_date"), errors="coerce")
        inactive = str(employee.get("status", "")).strip().upper() in INACTIVE
        if pd.isna(joined) or (inactive and pd.isna(left)):
            issues.append(str(employee["employee_id"]))
            continue
        joined = joined.date()
        left = None if pd.isna(left) else left.date()
        if left and left < joined:
            issues.append(str(employee["employee_id"]))
            continue
        opening += int(joined < start and (left is None or left >= start))
        closing += int(joined <= end and (left is None or left > end))
        leavers += int(left is not None and start <= left <= end)
    average = (opening + closing) / 2
    rate = None if issues or average <= 0 else leavers / average * 100
    return {"opening": opening, "closing": closing, "leavers": leavers, "rate": rate, "issues": issues}


class SimpleWorkforce:
    def __init__(self, context):
        self.c = context
        self.user = context["_current_user"]
        self.role = context["_current_role"]
        self.division = context["global_division"]

    def read(self, sql, params=()):
        return self.c["read_df"](sql, params)

    def scope(self, column="division"):
        if self.division == self.c["ALL_DIVISIONS"]:
            return "", ()
        return " AND " + column + "=?", (self.division,)

    def write(self, action):
        conn = self.c["get_pg_conn"]()
        try:
            with conn.cursor() as cur:
                action(cur)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def ensure_schema(self):
        def create(cur):
            cur.execute("SELECT pg_advisory_xact_lock(205029)")
            cur.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS last_working_date DATE")
            cur.execute("""CREATE TABLE IF NOT EXISTS workforce_daily_output (
                id BIGSERIAL PRIMARY KEY, work_date DATE NOT NULL, division TEXT NOT NULL,
                shift TEXT NOT NULL, machine TEXT NOT NULL REFERENCES machines(machine),
                output_ton NUMERIC(16,4) NOT NULL CHECK(output_ton>=0),
                employee_ids TEXT NOT NULL DEFAULT '[]', contractor_headcount INTEGER NOT NULL DEFAULT 0,
                contractor_cost NUMERIC(16,2) NOT NULL DEFAULT 0, remark TEXT,
                entered_by TEXT, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(work_date,division,shift,machine))""")
        self.write(create)

    def period(self):
        month = self.c["global_payroll_month"]
        start = month.replace(day=1)
        end = month.replace(day=monthrange(month.year, month.month)[1])
        return start, end

    def home(self):
        st.title("Home · MD Dashboard")
        start, end = self.period()
        st.caption(f"Reliable Packaging Industries Limited · {self.division} · {start:%B %Y}")
        st.caption("Created by Sourav Majumder")
        selected_day = st.date_input("Dashboard date", value=max(start, min(date.today(), end)),
            min_value=start, max_value=end, key=f"md_dashboard_day_{start:%Y%m}")
        allowed = self.c["v5_module_allowed"]
        clause, params = self.scope()
        if allowed("Attendance") or allowed("Reports"):
            attendance = self.read("""SELECT work_date,employee_id,status,ot_hours,review_required
                FROM attendance WHERE work_date BETWEEN ? AND ?""" + clause,
                (start.isoformat(),end.isoformat()) + params)
            st.subheader(f"Attendance · {selected_day:%d %b %Y}")
            if attendance.empty:
                st.info("No attendance uploaded for this month and division.")
            else:
                attendance['day'] = pd.to_datetime(attendance.work_date, errors='coerce').dt.date
                daily = attendance[attendance.day==selected_day]
                statuses = daily.status.value_counts()
                present = int(statuses.get('Present',0)+statuses.get('OD',0))
                leave = int(sum(statuses.get(s,0) for s in ['Leave','CL','SL','EL','LWP']))
                a,b,c,d = st.columns(4)
                a.metric('Present / OD rows', present)
                b.metric('Absent rows', int(statuses.get('Absent',0)))
                c.metric('Leave rows', leave)
                d.metric('Weekly off / Holiday rows', int(statuses.get('WO',0)+statuses.get('Holiday',0)))
                a,b,c,d = st.columns(4)
                a.metric('Half-day rows', int(statuses.get('Half Day',0)))
                b.metric('Employees recorded', daily.employee_id.nunique())
                c.metric('OT hours', f"{pd.to_numeric(daily.ot_hours,errors='coerce').fillna(0).sum():.2f}")
                pending = attendance.status.eq('HR Review') | attendance.review_required.fillna(False)
                d.metric('Pending HR rows · month', int(pending.sum()))
                st.caption('Daily counts are attendance rows per shift. Employees recorded counts each employee once. Missing source attendance is not automatically marked absent.')
                if daily.empty:
                    st.info('No attendance recorded on the selected dashboard date. Choose a date with uploaded attendance.')
                with st.expander('Monthly attendance trend'):
                    trend = attendance.groupby(['day','status']).size().unstack(fill_value=0)
                    st.bar_chart(trend)
        if allowed('Operations') or allowed('Reports'):
            st.subheader(f"Production & manpower · {selected_day:%d %b %Y}")
            output = self.read("""SELECT o.division,o.shift,o.machine,o.output_ton,o.employee_ids,o.contractor_headcount,
                COALESCE(t.standard_manpower,m.standard_manpower) AS standard_manpower,
                COALESCE(t.target_ton,m.target_ton) AS target_ton
                FROM workforce_daily_output o JOIN machines m ON m.machine=o.machine
                LEFT JOIN machine_shift_targets t ON t.machine=o.machine AND t.shift=o.shift
                WHERE o.work_date=?""" + self.scope('o.division')[0] + ' ORDER BY o.division,o.machine,o.shift',
                (selected_day,) + params)
            if output.empty:
                st.info('No simple production entries for this day. Existing detailed production remains under Settings → Detailed Reports.')
            else:
                output['Manpower'] = output.employee_ids.map(lambda x:len(json.loads(x))) + pd.to_numeric(output.contractor_headcount)
                output['Standard'] = pd.to_numeric(output.standard_manpower,errors='coerce').fillna(0)
                output['Gap'] = output['Manpower'] - output['Standard']
                output['Tons'] = pd.to_numeric(output.output_ton)
                output['Target (tons)'] = pd.to_numeric(output.target_ton,errors='coerce').fillna(0)
                output['Output per person (tons)'] = output.Tons / output.Manpower.where(output.Manpower>0)
                display = output.rename(columns={'division':'Division','machine':'Machine','shift':'Shift'})
                st.dataframe(display[['Division','Machine','Shift','Manpower','Standard','Gap','Tons','Target (tons)','Output per person (tons)']],
                    hide_index=True,use_container_width=True,
                    column_config={'Tons':st.column_config.NumberColumn(format='%.2f'),
                        'Output per person (tons)':st.column_config.NumberColumn(format='%.2f')})
                st.caption('Gap = actual manpower minus machine/shift standard. Targets and standards are read from your masters. Machine stages are kept separate to avoid adding the same material twice.')
        if allowed('Reports'):
            self.reports(heading=False)
        st.subheader('Company locations')
        locations = pd.DataFrame([
            {'Plant':'Greater Noida Plant','lat':28.451388100864982,'lon':77.57350512760937},
            {'Plant':'Dhaulana Glass Plant','lat':28.630672782505492,'lon':77.67451944283206},
            {'Plant':'D-63 Head Office','lat':28.612209897948606,'lon':77.38038405421369},
        ])
        st.map(locations)
        st.caption('Greater Noida Plant · Dhaulana Glass Plant · D-63 Head Office')

    def attendance(self):
        st.title("Attendance upload")
        st.caption("Choose the plant, upload the sheet, then save. Issues go to HR Review automatically.")
        if self.division == self.c["ALL_DIVISIONS"]:
            st.info("Select one Division in the sidebar to upload attendance.")
            return
        upload = st.file_uploader("Attendance sheet", type=["xls", "xlsx", "csv"], key="simple_att_file")
        if not upload:
            return
        try:
            parser = self.c["import_dhaulana_attendance_excel"] if self.division == "Dhaulana Glass Plant" else self.c["import_standard_attendance_excel"]
            upload.seek(0)
            if self.division == "Dhaulana Glass Plant":
                _, preview = parser(upload, dry_run=True)
            else:
                _, preview = parser(upload, self.division, dry_run=True)
            records = self.c["_validate_and_enrich_attendance_records"](preview.to_dict("records"))
            preview = pd.DataFrame(records)
            if set(preview["division"].astype(str)) != {self.division}:
                st.error("The sheet belongs to a different division. Choose that division before saving.")
                return
            duplicate = preview.duplicated(["work_date", "shift", "employee_id"], keep=False)
            review = preview["status"].eq("HR Review")
            a, b, c = st.columns(3)
            a.metric("Attendance rows", len(preview))
            b.metric("Employees", preview["employee_id"].nunique())
            c.metric("Needs HR review", int(review.sum()))
            st.info(f"Period: {preview['work_date'].min()} to {preview['work_date'].max()}. No rows are skipped because an employee is currently inactive.")
            st.dataframe(preview.groupby("status").size().rename("Rows").reset_index(), hide_index=True, use_container_width=True)
            if duplicate.any():
                st.error("Duplicate employee/date/shift rows found. Correct these rows before saving.")
                st.dataframe(preview.loc[duplicate], hide_index=True)
                return
            existing = self.read("SELECT employee_id,work_date,shift,status FROM attendance WHERE division=? AND work_date BETWEEN ? AND ?", (self.division, preview.work_date.min(), preview.work_date.max()))
            source_keys = set(zip(preview.employee_id.astype(str), preview.work_date.astype(str), preview['shift'].astype(str)))
            collisions = sum((str(r.employee_id), str(r.work_date)[:10], str(r.shift)) in source_keys for r in existing.itertuples())
            if collisions:
                st.warning(f"{collisions} rows already exist. Uploading again will replace those matching rows, including previous HR corrections.")
            if not self.c["can_edit_hr"](self.role):
                st.info("HR or Admin access is required to save attendance.")
                return
            with st.form("simple_att_save"):
                overwrite = st.checkbox("Replace the matching existing rows", disabled=not bool(collisions))
                submitted = st.form_submit_button("Save attendance", type="primary")
            if submitted:
                if collisions and not overwrite:
                    st.error("Tick Replace matching rows if you want to import this sheet again.")
                    return
                saved = self.c["_bulk_upsert_attendance"](records, "Simple attendance upload", replace_scope=False)
                st.success(f"Saved {saved:,} rows. Open HR Review to resolve the flagged entries.")
        except Exception as exc:
            st.error(f"Attendance could not be saved: {exc}")

    def review(self):
        st.title("HR Review")
        start, end = self.period()
        st.caption(f"{start:%d %b %Y} to {end:%d %b %Y}. Check the issue, choose the final status and add a reason.")
        master_clause, master_params = self.scope()
        pending = self.read("SELECT employee_id,employee_name,division,designation FROM employees WHERE UPPER(TRIM(department))='HR REVIEW'" + master_clause, master_params)
        if not pending.empty and self.c["can_edit_hr"](self.role):
            with st.expander(f"Confirm new employees ({len(pending)})", expanded=True):
                st.caption("Confirm identity and employment details once. Then resolve their attendance below.")
                labels = dict(zip(pending.employee_id, pending.employee_name))
                eid = st.selectbox("New employee", list(labels), format_func=lambda x: f"{labels[x]} ({x})")
                employee = pending[pending.employee_id==eid].iloc[0]
                departments = self.read("SELECT DISTINCT department FROM departments WHERE UPPER(TRIM(department))<>'HR REVIEW' ORDER BY department")
                if not departments.empty:
                    with st.form("simple_confirm_employee"):
                        name = st.text_input("Confirmed employee name", value=str(employee.employee_name))
                        department = st.selectbox("Department", departments.department.tolist())
                        designation = st.text_input("Designation", value=str(employee.designation or "Employee"))
                        salary = st.number_input("Monthly salary (₹)", min_value=0.0, step=100.0)
                        joining = st.date_input("Actual joining date", value=None)
                        confirm = st.checkbox("HR has verified this employee and their salary")
                        submitted = st.form_submit_button("Confirm employee", type="primary")
                    if submitted:
                        if not confirm or not name.strip() or not joining or joining>date.today() or salary<=0:
                            st.error("Complete the name, joining date, salary and HR confirmation.")
                        else:
                            def confirm_master(cur):
                                cur.execute("UPDATE employees SET employee_name=%s,department=%s,designation=%s,monthly_salary=%s,joining_date=%s WHERE employee_id=%s AND division=%s AND UPPER(TRIM(department))='HR REVIEW'", (name.strip(),department,designation,salary,joining.isoformat(),eid,employee.division))
                                if cur.rowcount!=1:
                                    raise ValueError("Employee was already confirmed. Reload the page.")
                            self.write(confirm_master)
                            st.rerun()
                else:
                    st.info("Admin must add a department in Settings before confirming employees.")
        clause, params = self.scope("a.division")
        rows = self.read("""SELECT a.id,a.work_date,a.employee_id,
            COALESCE(e.employee_name,a.source_employee_name,a.employee_id) AS employee_name,
            a.division,a.shift,a.time_in,a.time_out,a.working_hours,a.raw_status,
            COALESCE(NULLIF(a.source_issue,''),'Incomplete punch or attendance exception') AS issue,
            a.status,a.remark,COALESCE(e.department,'HR Review') AS department,e.joining_date,e.last_working_date
            FROM attendance a LEFT JOIN employees e ON e.employee_id=a.employee_id
            WHERE (a.status='HR Review' OR a.review_required=TRUE)
            AND a.work_date BETWEEN ? AND ?""" + clause + " ORDER BY a.work_date,a.employee_id", (start.isoformat(), end.isoformat()) + params)
        if rows.empty:
            st.success("No attendance issues for this month and division.")
            return
        st.metric("Rows needing HR action", len(rows))
        if not self.c["can_edit_hr"](self.role):
            st.dataframe(rows, hide_index=True)
            return
        choices = rows.employee_id.drop_duplicates().tolist()
        employee = st.selectbox("Employee", ["All employees"] + choices)
        if employee != "All employees":
            rows = rows[rows.employee_id == employee].copy()
        rows = rows.copy()
        rows.insert(0, "Resolve", False)
        rows["Final status"] = "Present"
        rows["HR reason"] = ""
        rows["Final hours"] = pd.to_numeric(rows.working_hours, errors="coerce").fillna(0.0)
        editable = {"Resolve", "Final status", "HR reason", "Final hours"}
        with st.form("simple_hr_resolution"):
            edited = st.data_editor(rows, hide_index=True, use_container_width=True,
                disabled=[c for c in rows.columns if c not in editable],
                column_config={"id": None, "department": None, "joining_date": None, "last_working_date": None,
                    "division": None, "shift": None, "working_hours": None, "status": None, "remark": None,
                    "work_date": st.column_config.TextColumn("Date"),
                    "employee_id": st.column_config.TextColumn("Employee ID"),
                    "employee_name": st.column_config.TextColumn("Employee"),
                    "time_in": st.column_config.TextColumn("In"),
                    "time_out": st.column_config.TextColumn("Out"),
                    "raw_status": st.column_config.TextColumn("Sheet status"),
                    "issue": st.column_config.TextColumn("What HR needs to check"),
                    "Final status": st.column_config.SelectboxColumn(options=["Present", "OD", "Half Day", "Absent", "WO", "Holiday", "CL", "SL", "EL", "LWP"], required=True),
                    "Final hours": st.column_config.NumberColumn(min_value=0.0, max_value=24.0, step=0.25)}, key="simple_hr_editor")
            submitted = st.form_submit_button("Save selected HR decisions", type="primary")
        if not submitted:
            return
        selected = edited[edited.Resolve.fillna(False)].copy()
        if selected.empty:
            st.error("Tick Resolve for the rows you have checked.")
            return
        if selected['HR reason'].fillna('').str.strip().eq('').any():
            st.error("Add an HR reason for each selected row.")
            return
        if selected.department.astype(str).str.upper().eq("HR REVIEW").any():
            st.error("An employee is awaiting master confirmation. Complete their department and salary under Settings → Employee Master, then resolve attendance here.")
            return
        def save(cur):
            for _, row in selected.iterrows():
                hours = float(row["Final hours"])
                status = row["Final status"]
                if status not in PAID | {"Absent", "LWP"} or not 0 <= hours <= 24:
                    raise ValueError("Invalid status or hours")
                joined = employment_date(row.joining_date)
                left = employment_date(row.last_working_date)
                work_day = pd.Timestamp(row.work_date).date()
                if status in PAID and ((not pd.isna(joined) and work_day < joined.date()) or (not pd.isna(left) and work_day > left.date())):
                    raise ValueError("Paid attendance is outside this employee's employment dates. Check Joining & Leaving first.")
                cur.execute("""UPDATE attendance SET status=%s,working_hours=%s,ot_hours=%s,
                    review_required=FALSE,source_issue='',remark=%s,updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s AND division=%s AND (status='HR Review' OR review_required=TRUE)""",
                    (status, hours, max(0.0, hours-12) if status in {"Present", "OD", "Half Day"} else 0,
                     f"{row['remark'] or ''} | HR {self.user['username']}: {row['HR reason']}", int(row.id), row.division))
                if cur.rowcount != 1:
                    raise ValueError("A row changed after this page loaded. Reload HR Review and try again.")
        try:
            self.write(save)
            st.success(f"Resolved {len(selected)} attendance rows. Reload this page to see the remaining issues.")
        except Exception as exc:
            st.error(f"No selected changes saved: {exc}")

    def production(self):
        st.title("Production & manpower")
        st.caption("One entry per date, shift and machine. Select the employees who worked and enter output in tons.")
        if self.division == self.c["ALL_DIVISIONS"]:
            st.info("Select one Division in the sidebar.")
            return
        machines = self.read("SELECT machine FROM machines WHERE active=TRUE ORDER BY machine")
        if machines.empty:
            st.info("Add machines in Settings first.")
            return
        day = st.date_input("Production date", value=date.today(), key="simple_production_date")
        shift = st.selectbox("Shift", ["A", "B", "General"])
        machine = st.selectbox("Machine", machines.machine.tolist())
        employees = self.read("""SELECT a.employee_id,e.employee_name,a.status,a.working_hours,a.ot_hours
            FROM attendance a JOIN employees e ON e.employee_id=a.employee_id
            WHERE a.division=? AND a.work_date=? AND a.shift=? AND a.status IN ('Present','OD','Half Day')
            AND COALESCE(a.review_required,FALSE)=FALSE AND UPPER(e.department)<>'HR REVIEW'
            ORDER BY e.employee_name""", (self.division, day.isoformat(), shift))
        labels = {str(r.employee_id): f"{r.employee_name} ({r.employee_id})" for r in employees.itertuples()}
        saved = self.read("SELECT * FROM workforce_daily_output WHERE division=? AND work_date=? AND shift=? AND machine=?", (self.division, day.isoformat(), shift, machine))
        previous = saved.iloc[0].to_dict() if not saved.empty else {}
        old_ids = json.loads(previous.get("employee_ids", "[]"))
        if any(eid not in labels for eid in old_ids):
            st.warning("Previously assigned employees now have missing or unresolved attendance. Resolve attendance before replacing this entry.")
            return
        with st.form("simple_production_form"):
            tons = st.number_input("Production (tons)", min_value=0.0, value=float(previous.get("output_ton", 0)), step=0.1, format="%.4f")
            assigned = st.multiselect("Employees on this machine", list(labels), default=old_ids, format_func=lambda eid: labels[eid])
            contractors = st.number_input("Contractor manpower", min_value=0, value=int(previous.get("contractor_headcount", 0)))
            contractor_cost = st.number_input("Total contractor labour cost for this shift (₹)", min_value=0.0, value=float(previous.get("contractor_cost", 0)), step=100.0)
            note = st.text_input("Remarks", value=str(previous.get("remark") or ""))
            submit = st.form_submit_button("Save production & manpower", type="primary")
        if not submit:
            return
        if self.role not in self.c["FULL_CONTROL_ROLES"] and not (self.c["_backend_allowed"] & {"Production Entry", "Manpower Allocation"}):
            st.error("Your role does not have production edit access.")
            return
        if not assigned and contractors == 0:
            st.error("Select employees or enter contractor manpower.")
            return
        if (contractors > 0 and contractor_cost <= 0) or (contractors == 0 and contractor_cost > 0):
            st.error("Enter both contractor manpower and its total labour cost, or leave both at zero.")
            return
        def save(cur):
            cur.execute("SELECT pg_advisory_xact_lock(205030)")
            if assigned:
                cur.execute("""SELECT a.employee_id FROM attendance a JOIN employees e ON e.employee_id=a.employee_id
                    WHERE a.division=%s AND a.work_date=%s AND a.shift=%s AND a.employee_id=ANY(%s)
                    AND a.status IN ('Present','OD','Half Day') AND COALESCE(a.review_required,FALSE)=FALSE
                    AND UPPER(e.department)<>'HR REVIEW' FOR SHARE OF a,e""", (self.division,day,shift,assigned))
                verified = {str(r[0]) for r in cur.fetchall()}
                if verified != set(assigned):
                    raise ValueError("An employee's attendance has changed. Reload and select verified employees again.")
            cur.execute("SELECT employee_ids FROM workforce_daily_output WHERE division=%s AND work_date=%s AND shift=%s AND machine<>%s", (self.division, day, shift, machine))
            already = set(e for r in cur.fetchall() for e in json.loads(r[0]))
            if already.intersection(assigned):
                raise ValueError("These employees are assigned to another machine in the same shift: " + ', '.join(sorted(already.intersection(assigned))))
            cur.execute("""INSERT INTO workforce_daily_output(work_date,division,shift,machine,output_ton,employee_ids,
                contractor_headcount,contractor_cost,remark,entered_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(work_date,division,shift,machine) DO UPDATE SET output_ton=excluded.output_ton,
                employee_ids=excluded.employee_ids,contractor_headcount=excluded.contractor_headcount,
                contractor_cost=excluded.contractor_cost,remark=excluded.remark,entered_by=excluded.entered_by,updated_at=CURRENT_TIMESTAMP""",
                (day, self.division, shift, machine, tons, json.dumps(assigned), contractors, contractor_cost, note, self.user['username']))
        try:
            self.write(save)
            st.success("Production and manpower saved. Open Cost & Attrition to see the result.")
        except Exception as exc:
            st.error(f"Production was not saved: {exc}")

    def reports(self, heading=True):
        if heading:
            st.title("Cost & attrition")
        start, end = self.period()
        st.caption(f"{start:%B %Y} · {self.division}")
        st.subheader("Manpower cost per ton")
        st.caption("Current salary master wages + single OT after 12 hours + entered contractor labour cost, divided by machine output. Material, power and employer contributions are excluded. Historical salary revisions are not reconstructed.")
        if self.c["can_view_salary"](self.role):
            clause, params = self.scope()
            output = self.read("SELECT * FROM workforce_daily_output WHERE work_date BETWEEN ? AND ?" + clause, (start, end) + params)
            if output.empty:
                st.info("Save production and manpower entries to see cost per ton. Earlier detailed production remains in the original Reports under Settings.")
            else:
                att = self.read("""SELECT a.employee_id,a.work_date,a.shift,a.division,a.status,a.review_required,a.ot_hours,
                    e.monthly_salary,e.department FROM attendance a LEFT JOIN employees e ON e.employee_id=a.employee_id
                    WHERE a.work_date BETWEEN ? AND ?""" + self.scope('a.division')[0], (start.isoformat(), end.isoformat()) + params)
                lookup = {(str(r.employee_id), str(r.work_date)[:10], str(r.shift), str(r.division)): r for r in att.itertuples()}
                summary = []
                for r in output.itertuples():
                    total = float(r.contractor_cost)
                    problems = []
                    ids = json.loads(r.employee_ids)
                    for eid in ids:
                        a = lookup.get((eid, str(r.work_date)[:10], r.shift, r.division))
                        if a is None or a.status not in {'Present','OD','Half Day'} or a.review_required or pd.isna(a.monthly_salary) or float(a.monthly_salary) <= 0 or str(a.department).upper() == 'HR REVIEW':
                            problems.append(eid)
                        else:
                            total += labour_amount(a.monthly_salary, pd.Timestamp(r.work_date).date(), a.status, a.ot_hours)
                    summary.append({'Date': r.work_date, 'Division': r.division, 'Shift': r.shift, 'Machine': r.machine,
                        'Manpower': len(ids)+int(r.contractor_headcount), 'Tons': float(r.output_ton),
                        'Labour cost (₹)': None if problems else total,
                        'Cost/ton (₹)': total/float(r.output_ton) if not problems and float(r.output_ton)>0 else None,
                        'Action': 'Check attendance/salary: '+', '.join(problems) if problems else ('Enter output' if float(r.output_ton)<=0 else 'Complete')})
                report = pd.DataFrame(summary)
                totals = []
                for (division,machine), group in report.groupby(['Division','Machine']):
                    valid = group['Labour cost (₹)'].notna().all()
                    tons = float(group.Tons.sum())
                    cost = float(group['Labour cost (₹)'].sum()) if valid else None
                    totals.append({'Division': division, 'Machine': machine, 'Manpower shifts': int(group.Manpower.sum()),
                        'Tons': tons, 'Labour cost (₹)': cost, 'Cost/ton (₹)': cost/tons if valid and tons>0 else None,
                        'Action': 'Complete' if valid and tons>0 else 'Check daily entries'})
                formats = {'Labour cost (₹)': st.column_config.NumberColumn(format='₹%.2f'), 'Cost/ton (₹)': st.column_config.NumberColumn(format='₹%.2f')}
                st.dataframe(pd.DataFrame(totals), hide_index=True, use_container_width=True, column_config=formats)
                with st.expander('Daily cost details'):
                    st.dataframe(report, hide_index=True, use_container_width=True, column_config=formats)
                st.caption("Machine/stage output is shown separately to avoid counting the same material more than once. Manpower is shift headcount, not unique monthly employees.")
                st.download_button('Download cost report', report.to_csv(index=False).encode(), 'manpower_cost.csv', 'text/csv')
        else:
            st.info("Salary access is required to view labour costs.")
        st.subheader("Monthly manpower attrition")
        clause, params = self.scope()
        employees = self.read("SELECT employee_id,department,joining_date,last_working_date,status FROM employees WHERE 1=1" + clause, params)
        result = attrition_summary(employees.to_dict('records'), start, end)
        if result['issues']:
            st.warning(f"Complete joining / last working dates for {len(result['issues'])} employee(s) in Settings → Joining & Leaving. Attrition is unavailable until these dates are complete.")
            with st.expander('Employees needing dates'):
                st.write(', '.join(result['issues']))
        else:
            a,b,c,d = st.columns(4)
            a.metric('Opening headcount', result['opening'])
            b.metric('Closing headcount', result['closing'])
            c.metric('Employees left', result['leavers'])
            d.metric('Attrition', 'N/A' if result['rate'] is None else f"{result['rate']:.2f}%")
        st.caption('Attrition = employees with last working date in the month ÷ average opening and closing headcount × 100. Temporary HR Review masters are excluded. This measures all recorded departures, not only voluntary resignations.')

    def lifecycle(self):
        st.title("Joining & leaving dates")
        st.caption("HR records the actual joining date and last working date. Attendance uploads do not change employment status.")
        if not self.c["can_edit_hr"](self.role):
            st.error('HR or Admin access is required.')
            return
        clause, params = self.scope()
        employees = self.read('SELECT employee_id,employee_name,joining_date,last_working_date,status FROM employees WHERE 1=1'+clause+' ORDER BY employee_name', params)
        if employees.empty:
            st.info('No employees in this division.')
            return
        mapping = {r.employee_id: f'{r.employee_name} ({r.employee_id})' for r in employees.itertuples()}
        eid = st.selectbox('Employee', list(mapping), format_func=lambda x: mapping[x])
        row = employees[employees.employee_id==eid].iloc[0]
        joined = employment_date(row.joining_date)
        left = pd.to_datetime(row.last_working_date, errors='coerce')
        with st.form('simple_dates'):
            join = st.date_input('Joining date', value=None if pd.isna(joined) else joined.date())
            leave = st.date_input('Last working date (blank if still employed)', value=None if pd.isna(left) else left.date())
            submit = st.form_submit_button('Save dates', type='primary')
        if submit:
            if not join or (leave and leave < join) or (leave and leave > date.today()):
                st.error('Enter a joining date and a valid last working date. Future departures cannot be recorded here.')
                return
            inactive = str(row.status).upper() in INACTIVE
            if inactive and not leave:
                st.error('This employee is inactive. Enter their actual last working date. Reactivation remains an Admin action in Employee Master.')
                return
            def save(cur):
                if leave:
                    cur.execute("UPDATE employees SET joining_date=%s,last_working_date=%s,status='Left' WHERE employee_id=%s", (join.isoformat(),leave,eid))
                else:
                    cur.execute('UPDATE employees SET joining_date=%s,last_working_date=NULL WHERE employee_id=%s', (join.isoformat(),eid))
            self.write(save)
            st.success('Employment dates saved. Attrition will recalculate automatically.')

    def render(self, page):
        self.ensure_schema()
        {'Simple Home': self.home, 'Simple Attendance': self.attendance, 'Simple HR Review': self.review,
         'Simple Production': self.production, 'Simple Reports': self.reports,
         'Simple Lifecycle': self.lifecycle}[page]()
