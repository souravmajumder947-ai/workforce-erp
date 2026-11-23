"""Daily workforce workflow. Existing authentication and master data stay authoritative."""
import hashlib
import json
from decimal import Decimal, InvalidOperation
from calendar import monthrange
from datetime import date

import pandas as pd
import streamlit as st


INACTIVE = {"INACTIVE", "LEFT", "RESIGNED", "TERMINATED"}
PAID = {"Present", "OD", "Half Day", "WO", "Holiday", "CL", "SL", "EL", "Leave"}
WORKED = {"Present", "OD", "Half Day"}


def employment_date(value):
    raw = str(value).strip()
    iso = len(raw) >= 10 and raw[:4].isdigit() and raw[4] == '-'
    return pd.to_datetime(value, errors='coerce', dayfirst=not iso)



def current_attendance_review_reason(row):
    source_issue = str(row.issue)
    if source_issue.startswith("Division mismatch"):
        return source_issue
    work_day = employment_date(row.work_date)
    joined = employment_date(row.joining_date)
    left = employment_date(row.last_working_date)
    master_exists = pd.notna(row.employment_status)
    master_pending = not master_exists or str(row.department).strip().upper() == "HR REVIEW"
    inactive = str(row.employment_status).strip().upper() in INACTIVE

    if master_exists and pd.notna(row.master_division) and row.master_division != row.division:
        reason = f"Division mismatch: master={row.master_division}; file={row.division}"
    elif pd.notna(left) and work_day > left:
        reason = f"Attendance after last working date ({left:%d %b %Y})"
    elif pd.notna(joined) and work_day < joined:
        reason = f"Attendance before joining date ({joined:%d %b %Y})"
    elif master_pending:
        reason = "Employee ID awaiting HR Master confirmation"
    elif inactive and pd.isna(left):
        reason = "Inactive employee missing last working date"
    elif pd.isna(joined):
        reason = "Employee Master missing a verified joining date"
    elif source_issue == "Employee ID awaiting HR Master confirmation" or source_issue.startswith("Employee currently inactive:"):
        reason = "Employment details verified in Employee Master; check sheet status and punches"
    else:
        return source_issue
    if "Punch check:" in source_issue and source_issue != reason:
        return f"{reason} · {source_issue}"
    return reason


def is_post_exit_attendance_placeholder(row):
    """Keep imported off-day placeholders visible without requiring an HR decision."""
    if str(row.employment_status).strip().upper() not in INACTIVE:
        return False
    if pd.isna(row.master_division) or row.master_division != row.division:
        return False
    if str(row.issue).startswith("Division mismatch") or "Punch check:" in str(row.issue):
        return False
    if str(row.raw_status).strip().upper() not in {"AA", "A", "ABSENT", "WO", "W/O", "OFF"}:
        return False
    no_punch = {"", "00:00", "00:00:00"}
    if any(pd.notna(punch) and str(punch).strip() not in no_punch for punch in (row.time_in, row.time_out)):
        return False
    if pd.to_numeric(row.working_hours, errors="coerce") != 0 or pd.to_numeric(row.ot_hours, errors="coerce") != 0:
        return False
    work_day = employment_date(row.work_date)
    last_day = employment_date(row.last_working_date)
    joined = employment_date(row.joining_date)
    return bool(pd.notna(last_day) and work_day > last_day and (pd.isna(joined) or joined <= last_day))


def review_csv(frame):
    """Prevent imported text from becoming a spreadsheet formula."""
    def safe_cell(value):
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + value
        return value
    return frame.map(safe_cell).to_csv(index=False).encode("utf-8-sig")


def labour_amount(salary, day, status, ot_hours):
    daily = float(salary) / monthrange(day.year, day.month)[1]
    factor = 0.5 if status == "Half Day" else (1.0 if status in PAID else 0.0)
    return daily * factor + (daily / 12 * max(0.0, float(ot_hours)) if status in {"Present", "OD", "Half Day"} else 0.0)


def production_cost_rows(output, att):
    """Use the same shift labour cost rules in both reports."""
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
    return pd.DataFrame(summary)


def attrition_summary(employees, start, end):
    """Opening = immediately before period; closing = after last-day departures."""
    opening = closing = leavers = 0
    issues = []
    for employee in employees:
        if str(employee.get("department", "")).strip().upper() == "HR REVIEW":
            continue
        joined = employment_date(employee.get("joining_date"))
        left = employment_date(employee.get("last_working_date"))
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

    def period(self):
        month = self.c["global_payroll_month"]
        start = month.replace(day=1)
        end = month.replace(day=monthrange(month.year, month.month)[1])
        return start, end

    def home_production(self, selected_day):
        clause, params = self.scope("o.division")
        st.subheader(f"Production & manpower · {selected_day:%d %b %Y}")
        output = self.read("""SELECT o.division,o.shift,o.machine,o.output_ton,o.employee_ids,o.contractor_headcount,
            COALESCE(t.standard_manpower,m.standard_manpower) AS standard_manpower,
            COALESCE(t.target_ton,m.target_ton) AS target_ton
            FROM workforce_daily_output o JOIN machines m ON m.machine=o.machine
            LEFT JOIN machine_shift_targets t ON t.machine=o.machine AND t.shift=o.shift
            WHERE o.work_date=?""" + clause + " ORDER BY o.division,o.machine,o.shift",
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
                column_config={'Tons':st.column_config.NumberColumn(format='%.0f'),
                    'Target (tons)':st.column_config.NumberColumn(format='%.0f'),
                    'Output per person (tons)':st.column_config.NumberColumn(format='%.2f')})
            st.caption('Gap = actual manpower minus machine/shift standard. Targets and standards are read from your masters. Machine stages are kept separate to avoid adding the same material twice.')

    def attendance(self):
        st.title("Attendance upload")
        st.caption("Choose the plant, upload the sheet, then save. Issues go to HR Review automatically.")
        if self.division == self.c["ALL_DIVISIONS"]:
            st.info("Select one Division in the sidebar to upload attendance.")
            return
        format_choice = "Standard / BTS"
        if self.division == "Dhaulana Glass Plant":
            format_choice = st.radio(
                "Attendance format", ["Dhaulana monthly punch sheet", "Standard / BTS"], horizontal=True,
            )
        upload_types = ["xlsx"] if format_choice == "Dhaulana monthly punch sheet" else ["xls", "xlsx", "csv"]
        upload = st.file_uploader("Attendance sheet", type=upload_types, key=f"simple_att_file_{self.division}_{format_choice}")
        if not upload:
            return
        try:
            upload.seek(0)
            if format_choice == "Dhaulana monthly punch sheet":
                _, preview = self.c["import_dhaulana_attendance_excel"](upload, dry_run=True)
            else:
                _, preview = self.c["import_standard_attendance_excel"](upload, self.division, dry_run=True)
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
            existing = self.read(
                "SELECT employee_id,work_date,shift,division FROM attendance WHERE work_date BETWEEN ? AND ?",
                (preview.work_date.min(), preview.work_date.max()),
            )
            source_keys = set(zip(preview.employee_id, preview.work_date, preview["shift"]))
            matching = [
                row for row in existing.itertuples()
                if (str(row.employee_id), str(row.work_date)[:10], str(row.shift)) in source_keys
            ]
            if any(row.division != self.division for row in matching):
                st.error("Matching employee/date/shift rows already belong to another division. Check those records before importing this sheet.")
                return
            collisions = len(matching)
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
                saved = self.c["_bulk_upsert_attendance"](records, "Simple attendance upload", replace_scope=False, overwrite=overwrite)
                st.session_state.pop("simple_hr_queue", None)
                st.success(f"Saved {saved:,} rows. Open HR Review to resolve the flagged entries.")
        except Exception as exc:
            st.error(f"Attendance could not be saved: {exc}")

    def review(self):
        st.title("HR Review")
        message = st.session_state.pop("simple_hr_success", None)
        if message:
            st.success(message)
        start, end = self.period()
        st.caption(f"{start:%d %b %Y} to {end:%d %b %Y}. Check the issue, choose the final status and add a reason.")
        master_clause, master_params = self.scope()
        pending = self.read("SELECT employee_id,employee_name,division,designation FROM employees WHERE UPPER(TRIM(department))='HR REVIEW'" + master_clause, master_params)
        if not pending.empty and self.c["can_edit_hr"](self.role):
            with st.expander(f"Confirm new employees ({len(pending)})", expanded=False):
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
                            try:
                                self.write(confirm_master)
                                st.session_state.pop("simple_hr_queue", None)
                                st.session_state["simple_hr_success"] = f"Confirmed employee {eid}."
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Employee could not be confirmed: {exc}")
                else:
                    st.info("Admin must add a department in Settings before confirming employees.")
        clause, params = self.scope("a.division")
        rows = self.read("""SELECT a.id,a.work_date,a.employee_id,
            COALESCE(e.employee_name,a.source_employee_name,a.employee_id) AS employee_name,
            a.division,a.shift,a.time_in,a.time_out,a.working_hours,a.ot_hours,a.raw_status,
            COALESCE(NULLIF(a.source_issue,''),'Incomplete punch or attendance exception') AS issue,
            a.status,a.remark,a.updated_at,COALESCE(e.department,'HR Review') AS department,
            e.joining_date::text AS joining_date,e.last_working_date::text AS last_working_date,
            e.status AS employment_status,e.division AS master_division
            FROM attendance a LEFT JOIN employees e ON e.employee_id=a.employee_id
            WHERE (a.status='HR Review' OR a.review_required=TRUE)
            AND a.work_date BETWEEN ? AND ?""" + clause + " ORDER BY a.work_date,a.employee_id,a.id",
            (start.isoformat(), end.isoformat()) + params)
        if not rows.empty:
            placeholders = pd.Series(
                [is_post_exit_attendance_placeholder(row) for row in rows.itertuples(index=False)],
                index=rows.index,
                dtype=bool,
            )
            if placeholders.any():
                with st.expander(f"Post-exit sheet rows ({placeholders.sum():,})"):
                    st.caption("No-punch absence and weekly-off rows dated after a recorded exit. These source rows remain available for reference.")
                    st.dataframe(
                        rows.loc[placeholders, ["work_date", "employee_id", "employee_name", "division",
                                               "raw_status", "last_working_date"]],
                        hide_index=True,
                    )
                rows = rows.loc[~placeholders].copy()
        if rows.empty:
            st.success("No attendance issues requiring HR action for this month and division.")
            return
        rows["issue"] = [current_attendance_review_reason(row) for row in rows.itertuples(index=False)]
        st.metric("Rows needing HR action", len(rows))
        if not self.c["can_edit_hr"](self.role):
            st.dataframe(rows, hide_index=True)
            return
        export_labels = {
            "employee_id": "Employee ID", "employee_name": "Employee Name",
            "work_date": "Attendance Date", "division": "Attendance Division",
            "master_division": "Master Division", "department": "Master Department",
            "employment_status": "Master Status", "joining_date": "Master Joining Date",
            "last_working_date": "Master Last Working Date", "issue": "Review Reason",
            "raw_status": "Sheet Status", "time_in": "Time In", "time_out": "Time Out",
            "working_hours": "Working Hours", "ot_hours": "OT Hours",
        }
        master_rows = rows[rows.issue.str.startswith((
            "Division mismatch", "Employee ID awaiting", "Employee Master missing",
            "Inactive employee missing", "Attendance before joining", "Attendance after last working",
        ))]
        detail_col, master_col = st.columns(2)
        detail_col.download_button(
            "Download all HR Review details",
            review_csv(rows[list(export_labels)].rename(columns=export_labels)),
            f"hr_review_{start:%Y_%m}.csv",
            "text/csv",
        )
        if not master_rows.empty:
            master_fields = [field for field in export_labels if field not in {
                "work_date", "raw_status", "time_in", "time_out", "working_hours", "ot_hours",
            }]
            master_check = (
                master_rows.groupby(master_fields, dropna=False, sort=False)
                .size().rename("Affected attendance rows").reset_index()
                .sort_values("employee_id", kind="stable").rename(columns=export_labels)
            )
            master_col.download_button(
                "Download Employee Master check list",
                review_csv(master_check),
                f"employee_master_checks_{start:%Y_%m}.csv",
                "text/csv",
            )
        st.caption("Downloads cover the selected division and month. Verify division mismatches before changing Employee Master.")
        issue_filter, employee_filter = st.columns(2)
        issue = issue_filter.selectbox("Review reason", ["All reasons"] + sorted(rows.issue.unique()))
        if issue != "All reasons":
            rows = rows[rows.issue == issue]
        choices = rows.employee_id.drop_duplicates().tolist()
        employee = employee_filter.selectbox("Employee", ["All employees"] + choices)
        if employee != "All employees":
            rows = rows[rows.employee_id == employee].copy()
        rows = rows.copy()
        rows.insert(0, "Resolve", False)
        rows["Display date"] = pd.to_datetime(rows.work_date, errors="coerce").dt.strftime("%d %b %Y")
        rows["Final status"] = ""
        rows["HR reason"] = ""
        rows["Final hours"] = pd.to_numeric(rows.working_hours, errors="coerce").fillna(0.0)
        editable = {"Resolve", "Final status", "HR reason", "Final hours"}
        queue_revision = hashlib.sha256(
            rows[["id", "updated_at", "issue", "joining_date", "last_working_date",
                  "employment_status", "master_division"]].to_json().encode()
        ).hexdigest()
        with st.form(f"simple_hr_resolution_{queue_revision}"):
            bulk_status = st.selectbox("Status for selected rows",
                                       ["Use status from sheet", "Use manually entered final status"] + sorted(PAID | {"Absent", "LWP"}))
            st.caption("Use status from sheet saves eligible rows and leaves exceptions in HR Review.")
            bulk_reason = st.text_input("Reason for selected rows", placeholder="Leave blank to use individual reasons")
            select_all = st.checkbox(f"Apply to all {len(rows):,} filtered rows")
            confirmed = st.checkbox("HR has verified the rows being saved")
            edited = st.data_editor(rows, hide_index=True, use_container_width=True,
                column_order=["Resolve", "Display date", "employee_id", "employee_name", "issue",
                              "raw_status", "time_in", "time_out", "Final status", "Final hours", "HR reason"],
                disabled=[c for c in rows.columns if c not in editable],
                column_config={"id": None, "department": None, "joining_date": None, "last_working_date": None,
                    "updated_at": None, "employment_status": None, "master_division": None, "working_hours": None, "ot_hours": None, "status": None, "remark": None,
                    "Display date": st.column_config.TextColumn("Date"),
                    "employee_id": st.column_config.TextColumn("Employee ID"),
                    "employee_name": st.column_config.TextColumn("Employee"),
                    "time_in": st.column_config.TextColumn("In"),
                    "time_out": st.column_config.TextColumn("Out"),
                    "raw_status": st.column_config.TextColumn("Sheet status"),
                    "issue": st.column_config.TextColumn("What HR needs to check"),
                    "Final status": st.column_config.SelectboxColumn(options=sorted(PAID | {"Absent", "LWP"})),
                    "Final hours": st.column_config.NumberColumn(min_value=0.0, max_value=24.0, step=0.25)}, key=f"simple_hr_editor_{self.division}_{start}_{issue}_{employee}_{queue_revision}")
            submitted = st.form_submit_button("Save selected HR decisions", type="primary")
        if not submitted:
            return
        if not confirmed:
            st.error("Confirm that HR has verified the rows being saved.")
            return
        selected = edited.copy() if select_all else edited[edited.Resolve.fillna(False)].copy()
        if bulk_status == "Use status from sheet":
            valid_codes = {"PP", "P", "PRESENT", "OD", "ONDUTY", "ON-DUTY", "AA", "A", "ABSENT",
                           "WO", "W/O", "OFF", "H", "PH", "HOLIDAY", "PUBLICHOLIDAY", "HD", "HALFDAY",
                           "CL", "SL", "EL", "LWP", "LEAVE"}
            mapper = self.c["_map_attendance_status"]
            selected["Final status"] = [
                mapper(row.raw_status, row["Final hours"], row.time_in, row.time_out)
                if str(row.raw_status).strip().upper().replace(" ", "") in valid_codes else "HR Review"
                for _, row in selected.iterrows()
            ]
        elif bulk_status != "Use manually entered final status":
            selected["Final status"] = bulk_status
        if bulk_reason.strip():
            selected["HR reason"] = bulk_reason.strip()
        if selected.empty:
            st.error("Tick Resolve for the rows you have checked.")
            return
        held = 0
        if bulk_status == "Use status from sheet":
            def eligible(row):
                status = row["Final status"]
                if status not in PAID | {"Absent", "LWP"}:
                    return False
                if str(row.department).strip().upper() == "HR REVIEW" or pd.isna(row.employment_status):
                    return False
                if str(row.issue).startswith("Division mismatch") or "Punch check:" in str(row.issue):
                    return False
                if status == "Absent" and (str(row.time_in or "").strip() not in {"", "00:00", "00:00:00"}
                                            or str(row.time_out or "").strip() not in {"", "00:00", "00:00:00"}):
                    return False
                if not 0 <= float(row["Final hours"]) <= 24:
                    return False
                joined = employment_date(row.joining_date)
                left = employment_date(row.last_working_date)
                work_day = pd.to_datetime(row.work_date, errors="coerce")
                inactive = str(row.employment_status).strip().upper() in INACTIVE
                return (pd.notna(work_day) and pd.notna(joined) and work_day.date() >= joined.date()
                        and (not inactive or pd.notna(left))
                        and (pd.isna(left) or work_day.date() <= left.date()))

            eligible_rows = selected.apply(eligible, axis=1)
            held = int((~eligible_rows).sum())
            selected = selected.loc[eligible_rows].copy()
            if selected.empty:
                st.warning(f"All {held:,} selected rows still need manual HR review.")
                return
        if not selected["Final status"].isin(PAID | {"Absent", "LWP"}).all():
            st.error("Choose a final status for every selected row.")
            return
        if selected['HR reason'].fillna('').str.strip().eq('').any():
            st.error("Add an HR reason for each selected row.")
            return
        if selected.department.astype(str).str.upper().eq("HR REVIEW").any():
            st.error("An employee is awaiting master confirmation. Complete their department and salary under Settings → Employee Master, then resolve attendance here.")
            return
        ot_threshold = self.c["get_setting_float"]("ot_threshold_hours", 12.0)

        def save(cur):
            for _, row in selected.sort_values("id").iterrows():
                hours = float(row["Final hours"])
                status = row["Final status"]
                if status not in PAID | {"Absent", "LWP"} or not 0 <= hours <= 24:
                    raise ValueError("Invalid status or hours")
                joined = employment_date(row.joining_date)
                left = employment_date(row.last_working_date)
                work_day = pd.Timestamp(row.work_date).date()
                if status in PAID and str(row.employment_status).strip().upper() in INACTIVE and pd.isna(left):
                    raise ValueError("Enter the inactive employee's last working date before approving paid attendance.")
                if status in PAID and ((not pd.isna(joined) and work_day < joined.date()) or (not pd.isna(left) and work_day > left.date())):
                    raise ValueError("Paid attendance is outside this employee's employment dates. Check Joining & Leaving first.")
                cur.execute("""UPDATE attendance SET status=%s,working_hours=%s,ot_hours=%s,
                    review_required=FALSE,source_issue='',remark=%s,reviewed_by=%s,updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s AND division=%s AND updated_at IS NOT DISTINCT FROM %s
                    AND (status='HR Review' OR review_required=TRUE)""",
                    (status, hours, max(0.0, hours - ot_threshold) if status in WORKED else 0,
                     f"{row['remark'] or ''} | HR {self.user['username']}: {row['HR reason']}", self.user["username"], int(row.id), row.division,
                     None if pd.isna(row.updated_at) else row.updated_at))
                if cur.rowcount != 1:
                    raise ValueError("A row changed after this page loaded. Reload HR Review and try again.")
        try:
            self.write(save)
            st.session_state.pop("simple_hr_queue", None)
            message = f"Resolved {len(selected):,} attendance rows."
            if held:
                message += f" {held:,} selected rows remain in HR Review."
            st.session_state["simple_hr_success"] = message
            st.rerun()
        except Exception as exc:
            st.error(f"No selected changes saved: {exc}")

    def auto_corrugation_upload(self):
        with st.expander("AUTO Corrugation · Daily totals"):
            st.caption("Import the Finsys Date Total production weight for Greater Noida. These totals are reported separately from machine entries.")
            upload = st.file_uploader("Daily production CSV", type=["csv"], key="auto_corrugation_csv")
            if upload is None:
                return
            try:
                upload.seek(0)
                rows = pd.read_csv(upload, dtype=str, keep_default_na=False)
                required = {"Production Date", "Finsys Machine / Stage", "Production Weight (kg)"}
                if rows.empty or not required.issubset(rows.columns):
                    raise ValueError("Use the daily production CSV with date, stage and production weight in kg.")
                start, end = self.period()
                records = []
                for day, stage, weight in rows[["Production Date", "Finsys Machine / Stage",
                                                "Production Weight (kg)"]].itertuples(index=False, name=None):
                    day = date.fromisoformat(day.strip())
                    kg = Decimal(weight.strip())
                    if not start <= day <= end or stage.strip().upper() != "AUTO CORRUGATION":
                        raise ValueError("Every row must be AUTO CORRUGATION for the selected month.")
                    if not kg.is_finite() or kg < 0 or kg != kg.to_integral_value() or kg > 999999999999:
                        raise ValueError("Production weight must be a nonnegative whole number of kilograms.")
                    records.append((day, int(kg)))
                if len({day for day, _ in records}) != len(records):
                    raise ValueError("The file must contain one row per production date.")
            except (InvalidOperation, ValueError) as exc:
                st.error(f"Invalid daily production file: {exc}")
                return
            total = sum(kg for _, kg in records)
            st.write(f"{len(records)} dates · {total:,} kg · {total / 1000:,.0f} tons")
            st.dataframe(pd.DataFrame(sorted(records), columns=["Production date", "Production weight (kg)"]),
                         hide_index=True)
            if not st.button("Save AUTO Corrugation daily totals", type="primary"):
                return

            def save(cur):
                cur.execute("""CREATE TABLE IF NOT EXISTS auto_corrugation_daily (
                    work_date DATE PRIMARY KEY, weight_kg BIGINT NOT NULL CHECK (weight_kg >= 0),
                    entered_by TEXT NOT NULL)""")
                for day, kg in sorted(records):
                    cur.execute("""INSERT INTO auto_corrugation_daily (work_date,weight_kg,entered_by)
                                   VALUES (%s,%s,%s) ON CONFLICT (work_date) DO NOTHING""",
                                (day, kg, self.user["username"]))
                    if not cur.rowcount:
                        cur.execute("SELECT weight_kg FROM auto_corrugation_daily WHERE work_date=%s", (day,))
                        if cur.fetchone()[0] != kg:
                            raise ValueError(f"{day}: a different total already exists. No rows were changed.")
            try:
                self.write(save)
            except Exception as exc:
                st.error(f"Daily totals could not be saved: {exc}")
            else:
                st.success(f"Verified {len(records)} daily AUTO Corrugation totals in the ERP.")

    def production(self):
        st.title("Production & manpower")
        if st.session_state.pop("simple_production_saved", False):
            st.success("Production and manpower saved. Open Cost & Attrition to see the result.")
        st.caption("One entry per date, shift and machine. Select the employees who worked and enter output in tons.")
        if self.division == self.c["ALL_DIVISIONS"]:
            st.info("Select one Division in the sidebar.")
            return
        if self.division == "Greater Noida Plant":
            self.auto_corrugation_upload()
        machines = self.read("SELECT machine FROM machines WHERE active=TRUE ORDER BY machine")
        if machines.empty:
            st.info("Add machines in Settings first.")
            return
        start, end = self.period()
        day = st.date_input(
            "Production date", value=max(start, min(date.today(), end)),
            min_value=start, max_value=end, key=f"simple_production_date_{start:%Y%m}",
        )
        shift = st.selectbox("Shift", ["A", "B", "General"])
        shift_entries = self.read("""SELECT machine,output_ton FROM workforce_daily_output
            WHERE division=? AND work_date=? AND shift=?""", (self.division, day.isoformat(), shift))
        checklist = machines.merge(shift_entries, on="machine", how="left", indicator=True)
        checklist["Entry status"] = checklist["_merge"].map({"both": "Saved", "left_only": "Not entered"})
        count = int(checklist["_merge"].eq("both").sum())
        with st.expander(f"Shift entries: {count} of {len(checklist)} active machines saved", expanded=True):
            st.caption("Check machines scheduled for this shift. Idle machines can be left blank.")
            st.dataframe(checklist[["machine", "Entry status", "output_ton"]].rename(
                columns={"machine": "Machine", "output_ton": "Saved tons"}),
                hide_index=True, width="stretch",
                column_config={"Saved tons": st.column_config.NumberColumn(format="%.0f")})
        machine = st.selectbox("Machine", machines.machine.tolist())
        employees = self.read("""SELECT a.employee_id,e.employee_name,a.status,a.working_hours,a.ot_hours
            FROM attendance a JOIN employees e ON e.employee_id=a.employee_id
            WHERE a.division=? AND a.work_date=? AND a.shift=? AND a.status IN ('Present','OD','Half Day')
            AND COALESCE(a.review_required,FALSE)=FALSE AND UPPER(e.department)<>'HR REVIEW'
            ORDER BY e.employee_name""", (self.division, day.isoformat(), shift))
        labels = {str(r.employee_id): f"{r.employee_name} ({r.employee_id})" for r in employees.itertuples()}
        entry_key = f"{self.user['username']}_{self.division}_{day}_{shift}_{machine}"
        draft = st.session_state.get("simple_production_entry")
        reload_entry = st.button("Reload saved entry")
        if reload_entry or draft is None or draft[0] != entry_key:
            saved = self.read(
                "SELECT * FROM workforce_daily_output WHERE division=? AND work_date=? AND shift=? AND machine=?",
                (self.division, day.isoformat(), shift, machine),
            )
            previous = saved.iloc[0].to_dict() if not saved.empty else {}
            form_version = draft[2] + 1 if draft else 0
            st.session_state["simple_production_entry"] = (entry_key, previous, form_version)
        else:
            previous, form_version = draft[1:]
        old_ids = json.loads(previous.get("employee_ids", "[]"))
        eligible_ids = [eid for eid in old_ids if eid in labels]
        missing_ids = sorted(set(old_ids) - set(eligible_ids))
        if missing_ids:
            st.warning("Previously assigned employees lack eligible attendance: " + ", ".join(missing_ids))
        elif not labels:
            st.info("No verified employee attendance for this date and shift. You can still enter contractor manpower.")
        with st.form(f"simple_production_form_{entry_key}_{form_version}"):
            tons = st.number_input("Production (tons)", min_value=0.0, value=float(previous.get("output_ton", 0)), step=0.1, format="%.4f")
            assigned = st.multiselect("Employees on this machine", list(labels), default=eligible_ids, format_func=lambda eid: labels[eid])
            contractors = st.number_input("Contractor manpower", min_value=0, value=int(previous.get("contractor_headcount", 0)))
            contractor_cost = st.number_input("Total contractor labour cost for this shift (₹)", min_value=0.0, value=float(previous.get("contractor_cost", 0)), step=100.0)
            note = st.text_input("Remarks", value=str(previous.get("remark") or ""))
            remove_missing = not missing_ids or st.checkbox("Remove the assignments listed above when saving")
            submit = st.form_submit_button("Save production & manpower", type="primary")
        if not submit:
            return
        if self.role not in self.c["FULL_CONTROL_ROLES"] and not (self.c["_backend_allowed"] & {"Production Entry", "Manpower Allocation"}):
            st.error("Your role does not have production edit access.")
            return
        if not remove_missing:
            st.error("Resolve attendance or confirm removal of the affected assignments.")
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
                    AND UPPER(e.department)<>'HR REVIEW' FOR SHARE OF a,e""", (self.division, day.isoformat(), shift, assigned))
                verified = {str(r[0]) for r in cur.fetchall()}
                if verified != set(assigned):
                    raise ValueError("An employee's attendance has changed. Reload and select verified employees again.")
            cur.execute("SELECT employee_ids FROM workforce_daily_output WHERE division=%s AND work_date=%s AND shift=%s AND machine<>%s", (self.division, day, shift, machine))
            already = set(e for r in cur.fetchall() for e in json.loads(r[0]))
            duplicates = already.intersection(assigned)
            if duplicates:
                raise ValueError("These employees are assigned to another machine in the same shift: " + ", ".join(sorted(duplicates)))
            cur.execute("""INSERT INTO workforce_daily_output(work_date,division,shift,machine,output_ton,employee_ids,
                contractor_headcount,contractor_cost,remark,entered_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(work_date,division,shift,machine) DO UPDATE SET output_ton=excluded.output_ton,
                employee_ids=excluded.employee_ids,contractor_headcount=excluded.contractor_headcount,
                contractor_cost=excluded.contractor_cost,remark=excluded.remark,entered_by=excluded.entered_by,updated_at=CURRENT_TIMESTAMP
                WHERE workforce_daily_output.updated_at IS NOT DISTINCT FROM %s""",
                (day, self.division, shift, machine, tons, json.dumps(assigned), contractors,
                 contractor_cost, note, self.user['username'], previous.get("updated_at")))
            if cur.rowcount != 1:
                raise ValueError("Someone else updated this production entry. Reload it before saving.")
        try:
            self.write(save)
            st.session_state.pop("simple_production_entry", None)
            st.session_state["simple_production_saved"] = True
            st.rerun()
        except Exception as exc:
            st.error(f"Production was not saved: {exc}")

    def reports(self, heading=True):
        if heading:
            st.title("Cost & attrition")
        start, end = self.period()
        st.caption(f"{start:%B %Y} · {self.division}")
        if self.division in {"Greater Noida Plant", self.c["ALL_DIVISIONS"]}:
            table = self.read("SELECT to_regclass('auto_corrugation_daily') IS NOT NULL AS available")
            if not table.empty and bool(table.iloc[0]["available"]):
                totals = self.read("""SELECT work_date AS "Date", weight_kg AS "Production weight (kg)"
                                      FROM auto_corrugation_daily WHERE work_date BETWEEN ? AND ?
                                      ORDER BY work_date""", (start, end))
                if not totals.empty:
                    st.subheader("Greater Noida · AUTO Corrugation daily totals")
                    kg = totals["Production weight (kg)"]
                    st.metric("Production (tons)", f"{kg.sum() / 1000:,.0f}")
                    totals["Production (tons)"] = kg / 1000
                    st.dataframe(totals, hide_index=True, column_config={"Production (tons)": st.column_config.NumberColumn(format="%.0f")})
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
                report = production_cost_rows(output, att)
                totals = []
                for (division,machine), group in report.groupby(['Division','Machine']):
                    valid = group['Labour cost (₹)'].notna().all()
                    tons = float(group.Tons.sum())
                    cost = float(group['Labour cost (₹)'].sum()) if valid else None
                    totals.append({'Division': division, 'Machine': machine, 'Manpower shifts': int(group.Manpower.sum()),
                        'Tons': tons, 'Labour cost (₹)': cost, 'Cost/ton (₹)': cost/tons if valid and tons>0 else None,
                        'Action': 'Complete' if valid and tons>0 else 'Check daily entries'})
                formats = {'Tons': st.column_config.NumberColumn(format='%.0f'), 'Labour cost (₹)': st.column_config.NumberColumn(format='₹%.2f'), 'Cost/ton (₹)': st.column_config.NumberColumn(format='₹%.2f')}
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

    def bulk_employment_dates(self, employees):
        fields = {"employee_id": "Employee ID", "employee_name": "Employee Name",
                  "division": "Division", "joining_date": "Joining Date",
                  "last_working_date": "Last Working Date", "status": "Employment Status"}
        joined = employees.joining_date.map(employment_date)
        left = employees.last_working_date.map(employment_date)
        inactive = employees.status.astype(str).str.strip().str.upper().isin(INACTIVE)
        problems = pd.DataFrame({
            "Missing joining date": joined.isna(),
            "Inactive employee missing exit date": inactive & left.isna(),
            "Exit date before joining": left.lt(joined),
        })
        needed = employees.loc[problems.any(axis=1), list(fields)].rename(columns=fields)
        with st.expander(f"Dates to fix ({len(needed):,})", expanded=not needed.empty):
            if needed.empty:
                st.success("No missing or conflicting employment dates found.")
            else:
                needed["Needs correction"] = problems.loc[needed.index].apply(
                    lambda flags: ", ".join(flags.index[flags]), axis=1
                )
                st.dataframe(needed, hide_index=True, width="stretch")
                export = needed[["Employee ID", "Joining Date", "Last Working Date"]].copy()
                export["Employee ID"] = export["Employee ID"].map(
                    lambda value: "'" + str(value) if str(value).lstrip().startswith(("=", "+", "-", "@")) else str(value)
                )
                st.download_button("Download dates to fix", export.to_csv(index=False).encode("utf-8-sig"),
                                   "employment_dates_to_fix.csv", "text/csv")

        st.subheader("Bulk update employment dates")
        st.caption("Use Employee ID, Joining Date and Last Working Date. Use YYYY-MM-DD for typed dates. Blank cells keep saved dates.")
        upload = st.file_uploader("Corrected employee dates", type=["csv", "xlsx"], key="bulk_employment_dates")
        if upload is None:
            return
        try:
            upload.seek(0)
            incoming = (pd.read_csv(upload, dtype=str, keep_default_na=False)
                        if upload.name.lower().endswith(".csv")
                        else pd.read_excel(upload, dtype=str, keep_default_na=False))
        except (ValueError, OSError, ImportError):
            st.error("Could not read the file. Save it as a CSV or XLSX workbook and try again.")
            return
        incoming.columns = [" ".join(str(c).strip().lower().replace("_", " ").split()) for c in incoming.columns]
        if incoming.columns.duplicated().any() or not {"employee id", "joining date", "last working date"}.issubset(incoming.columns):
            st.error("Use unique headers: Employee ID, Joining Date and Last Working Date.")
            return
        incoming["employee id"] = incoming["employee id"].str.strip()
        if incoming["employee id"].eq("").any() or incoming["employee id"].duplicated().any():
            st.error("Every row must have a unique Employee ID.")
            return
        master = {str(row.employee_id): row for row in employees.itertuples(index=False)}
        changes, errors = [], []
        for _, entry in incoming.iterrows():
            eid = entry["employee id"]
            row = master.get(eid)
            raw_join, raw_left = entry["joining date"].strip(), entry["last working date"].strip()
            if row is None:
                errors.append(f"{eid}: Employee ID is outside the selected division or missing from Employee Master.")
                continue
            if not (raw_join or raw_left):
                continue
            old_join, old_left = map(employment_date, (row.joining_date, row.last_working_date))
            new_join = employment_date(raw_join) if raw_join else old_join
            new_left = employment_date(raw_left) if raw_left else old_left
            if (pd.isna(new_join) or ((raw_left or pd.notna(row.last_working_date) and str(row.last_working_date).strip()) and pd.isna(new_left))
                    or new_join.date() > date.today()
                    or (pd.notna(new_left) and (new_left < new_join or new_left.date() > date.today()))):
                errors.append(f"{eid}: Check joining and last working dates.")
                continue
            join = new_join.date().isoformat()
            leave = None if pd.isna(new_left) else new_left.date().isoformat()
            old_join_display = None if pd.isna(old_join) else old_join.date().isoformat()
            old_left_display = None if pd.isna(old_left) else old_left.date().isoformat()
            if (join, leave) != (old_join_display, old_left_display):
                status = "Left" if raw_left and leave and str(row.status).strip().upper() not in INACTIVE else row.status
                changes.append((row, join, leave, status, old_join_display, old_left_display))
        if errors:
            st.error(f"Correct {len(errors):,} rows before saving.")
            st.dataframe(pd.DataFrame({"Upload issue": errors}), hide_index=True, width="stretch")
            return
        if not changes:
            st.info("No employment dates would change.")
            return
        st.dataframe(pd.DataFrame([
            (row.employee_id, row.employee_name, old_join, join, old_leave, leave, row.status, status)
            for row, join, leave, status, old_join, old_leave in changes
        ], columns=["Employee ID", "Employee", "Saved joining", "New joining",
                    "Saved exit", "New exit", "Saved status", "New status"]), hide_index=True, width="stretch")
        fingerprint = hashlib.sha256(repr(changes).encode()).hexdigest()
        confirmed = st.checkbox("HR has verified the dates and status changes above",
                                key=f"confirm_employment_{fingerprint}")
        if st.button(f"Save {len(changes):,} employee updates", disabled=not confirmed, type="primary"):
            def save(cur):
                for row, join, leave, status, _, _ in sorted(changes, key=lambda item: str(item[0].employee_id)):
                    cur.execute("""UPDATE employees SET joining_date=%s,last_working_date=%s,status=%s
                                   WHERE employee_id=%s AND division IS NOT DISTINCT FROM %s
                                     AND joining_date::text IS NOT DISTINCT FROM %s
                                     AND last_working_date::text IS NOT DISTINCT FROM %s
                                     AND status IS NOT DISTINCT FROM %s""",
                                (join, leave, status, row.employee_id, row.division,
                                 None if pd.isna(row.joining_date) else str(row.joining_date),
                                 None if pd.isna(row.last_working_date) else str(row.last_working_date), row.status))
                    if cur.rowcount != 1:
                        raise ValueError("Employee records changed. Refresh and review the file again.")
            try:
                self.write(save)
            except ValueError as exc:
                st.error(str(exc))
                return
            st.session_state.pop("simple_hr_queue", None)
            st.session_state["employment_dates_saved"] = len(changes)
            st.rerun()

    def lifecycle(self):
        st.title("Employee Joining & Exit")
        st.caption("HR records the actual joining date and last working date. Attendance uploads do not change employment status.")
        if not self.c["can_edit_hr"](self.role):
            st.error('HR or Admin access is required.')
            return
        clause, params = self.scope()
        employees = self.read('SELECT employee_id,employee_name,division,department,joining_date::text AS joining_date,last_working_date::text AS last_working_date,status FROM employees WHERE 1=1'+clause+' ORDER BY employee_name', params)
        if employees.empty:
            st.info('No employees in this division.')
            return
        saved = st.session_state.pop("employment_dates_saved", None)
        if saved:
            employee_label = "employee" if saved == 1 else "employees"
            st.success(f"Saved employment dates for {saved:,} {employee_label}.")
        start, end = self.period()
        result = attrition_summary(employees.to_dict("records"), start, end)
        confirmed_master = employees[~employees.department.astype(str).str.strip().str.upper().eq("HR REVIEW")]
        joining = confirmed_master.joining_date.map(employment_date)
        joiners = joining.between(pd.Timestamp(start), pd.Timestamp(end)).sum()
        st.caption(f"{start:%B %Y} · {self.division}")
        a, b, c = st.columns(3)
        a.metric("Recorded joiners", int(joiners))
        b.metric("Recorded leavers", result["leavers"])
        c.metric("Attrition", "Pending dates" if result["issues"] else
                 ("N/A" if result["rate"] is None else f"{result['rate']:.2f}%"))
        self.bulk_employment_dates(employees)
        st.subheader("Edit one employee")
        mapping = {r.employee_id: f'{r.employee_name} ({r.employee_id})' for r in employees.itertuples()}
        eid = st.selectbox('Employee', list(mapping), format_func=lambda x: mapping[x])
        row = employees[employees.employee_id==eid].iloc[0]
        st.caption(f"{row.division} · {row.status}")
        joined = employment_date(row.joining_date)
        left = employment_date(row.last_working_date)
        with st.form(f"simple_dates_{eid}"):
            join = st.date_input("Joining date", value=None if pd.isna(joined) else joined.date())
            leave = st.date_input("Last working date (blank if still employed)", value=None if pd.isna(left) else left.date())
            if pd.isna(joined):
                st.caption("You can save a confirmed last working date while HR verifies the joining date.")
            submit = st.form_submit_button("Save dates", type="primary")
        if submit:
            today = date.today()
            if (not join and not leave) or (join and join > today) or (leave and (leave > today or (join and leave < join))):
                st.error("Enter a valid employment date. Dates cannot be in the future, and the last working date must be on or after joining.")
                return
            if str(row.status).strip().upper() in INACTIVE and not leave:
                st.error("Enter the actual last working date for this inactive employee. Admin can reactivate employees in Employee Master.")
                return
            if not join and pd.notna(joined):
                st.error("Keep the saved joining date or enter a verified correction.")
                return

            def save(cur):
                cur.execute(
                    """UPDATE employees SET joining_date=COALESCE(%s, joining_date),
                              last_working_date=%s, status=%s
                       WHERE employee_id=%s AND division IS NOT DISTINCT FROM %s
                         AND joining_date::text IS NOT DISTINCT FROM %s
                         AND last_working_date::text IS NOT DISTINCT FROM %s
                         AND status IS NOT DISTINCT FROM %s""",
                    (join.isoformat() if join else None, leave.isoformat() if leave else None,
                     "Left" if leave else row.status, eid, row.division,
                     None if pd.isna(row.joining_date) else row.joining_date,
                     None if pd.isna(row.last_working_date) else row.last_working_date, row.status),
                )
                if cur.rowcount != 1:
                    raise ValueError("This employee record changed. Reopen the page and review the saved dates.")

            try:
                self.write(save)
            except ValueError as exc:
                st.error(str(exc))
                return
            st.session_state.pop("simple_hr_queue", None)
            st.session_state["employment_dates_saved"] = 1
            st.rerun()

    def render(self, page):
        {'Simple Attendance': self.attendance, 'Simple HR Review': self.review,
         'Simple Production': self.production, 'Simple Reports': self.reports,
         'Simple Lifecycle': self.lifecycle}[page]()
