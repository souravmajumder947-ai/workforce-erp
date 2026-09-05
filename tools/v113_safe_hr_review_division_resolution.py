from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V11.3 SAFE DIVISION MISMATCH RESOLUTION"
if MARK in s:
    print("V11.3 mismatch-resolution safety already applied")
    raise SystemExit(0)

# Add master division to the HR Review source query so HR can see attendance-vs-master side by side.
old_query = '''        reviews=read_df(
            """SELECT a.id,a.division,a.work_date,a.employee_id,
                      COALESCE(e.employee_name,a.source_employee_name,a.employee_id) AS employee_name,
                      COALESCE(e.department,'General') AS department,
                      COALESCE(a.designation,e.designation,'Employee') AS designation,
                      a.shift,a.time_in,a.time_out,a.working_hours,a.raw_status,a.status,a.remark,
                      COALESCE(a.source_issue,'') AS source_issue
'''
new_query = '''        # V11.3 SAFE DIVISION MISMATCH RESOLUTION
        reviews=read_df(
            """SELECT a.id,a.division,a.work_date,a.employee_id,
                      COALESCE(e.employee_name,a.source_employee_name,a.employee_id) AS employee_name,
                      COALESCE(e.division,'') AS master_division,
                      COALESCE(e.department,'General') AS department,
                      COALESCE(a.designation,e.designation,'Employee') AS designation,
                      a.shift,a.time_in,a.time_out,a.working_hours,a.raw_status,a.status,a.remark,
                      COALESCE(a.source_issue,'') AS source_issue
'''
if old_query not in s:
    raise RuntimeError("HR Review query anchor not found")
s = s.replace(old_query, new_query, 1)

# Replace the old explanation that implied every master exception changes Employee Master.
old_info = '''                    st.info(
                        "Unknown Employee and Division Mismatch rows update Employee Master only after HR selects the row "
                        "and resolves it to a final attendance status."
                    )
'''
new_info = '''                    st.info(
                        "Unknown Employee rows can create/complete Employee Master after HR verification. "
                        "Division Mismatch rows do **not** change Employee Master unless HR explicitly chooses "
                        "'Move Employee to Attendance Division'."
                    )
'''
if old_info not in s:
    raise RuntimeError("Master-exception info anchor not found")
s = s.replace(old_info, new_info, 1)

# Change the control row from 3 to 4 columns and add the explicit mismatch-resolution policy.
old_controls = '''                csel,cstatus,cdiv = st.columns([1,1.25,1.4])
                select_all_filtered = csel.checkbox(
                    f"Select all filtered ({len(filtered):,})", value=False, key="v81_select_all_filtered",
                    help="Choose multiple filters above, then select every matching row in one click."
                )
                bulk_status = cstatus.selectbox(
                    "Bulk Status for Selected",
                    ["Keep Each Row Status","Use Raw Biometric Status (Auto)","Present","Half Day","Absent","LWP","WO","Holiday","Leave","CL","SL","EL","HR Review"],
                    key="v82_bulk_review_status"
                )
                bulk_division = cdiv.selectbox(
                    "Bulk Division for Selected",
                    ["Keep Each Row Division"] + DIVISIONS,
                    key="v80_bulk_review_division"
                )
'''
new_controls = '''                csel,cstatus,cdiv,cmaster = st.columns([1,1.3,1.25,1.6])
                select_all_filtered = csel.checkbox(
                    f"Select all filtered ({len(filtered):,})", value=False, key="v81_select_all_filtered",
                    help="Choose multiple filters above, then select every matching row in one click."
                )
                bulk_status = cstatus.selectbox(
                    "Bulk Status for Selected",
                    ["Keep Each Row Status","Use Raw Biometric Status (Auto)","Present","Half Day","Absent","LWP","WO","Holiday","Leave","CL","SL","EL","HR Review"],
                    key="v82_bulk_review_status"
                )
                bulk_division = cdiv.selectbox(
                    "Attendance Division",
                    ["Keep Each Row Division"] + DIVISIONS,
                    key="v80_bulk_review_division",
                    help="Changes the selected attendance row only. It does not change Employee Master by itself."
                )
                mismatch_master_action = cmaster.selectbox(
                    "Division Mismatch Resolution",
                    [
                        "Keep Employee Master Division",
                        "Move Employee to Attendance Division",
                    ],
                    index=0,
                    key="v113_mismatch_master_action",
                    help=(
                        "Safe default: keep the employee's permanent/master division and resolve only the attendance row. "
                        "Choose Move Employee only when HR confirms this is a permanent transfer/master correction."
                    )
                )
'''
if old_controls not in s:
    raise RuntimeError("HR Review control-row anchor not found")
s = s.replace(old_controls, new_controls, 1)

# Add Master Division to the review table and keep it read-only.
old_rename = '''                review_show = filtered.rename(columns={
                    "id":"ID","division":"Division","work_date":"Date","employee_id":"Employee ID","employee_name":"Employee Name",
                    "department":"Department","designation":"Designation","shift":"Shift","time_in":"Time In","time_out":"Time Out",
                    "working_hours":"Working Hrs","raw_status":"Raw Status","status":"Status","remark":"Remark",
                    "source_issue":"Master Issue","issue_type":"Issue Type"
                }).copy()
'''
new_rename = '''                review_show = filtered.rename(columns={
                    "id":"ID","division":"Division","master_division":"Master Division",
                    "work_date":"Date","employee_id":"Employee ID","employee_name":"Employee Name",
                    "department":"Department","designation":"Designation","shift":"Shift","time_in":"Time In","time_out":"Time Out",
                    "working_hours":"Working Hrs","raw_status":"Raw Status","status":"Status","remark":"Remark",
                    "source_issue":"Master Issue","issue_type":"Issue Type"
                }).copy()
'''
if old_rename not in s:
    raise RuntimeError("review_show rename anchor not found")
s = s.replace(old_rename, new_rename, 1)

old_cols = '''                display_cols = [
                    "Select","ID","Issue Type","Division","Date","Employee ID","Employee Name","Department","Designation",
                    "Shift","Time In","Time Out","Working Hrs","Raw Status","Status","Remark","Master Issue"
                ]
'''
new_cols = '''                display_cols = [
                    "Select","ID","Issue Type","Division","Master Division","Date","Employee ID","Employee Name","Department","Designation",
                    "Shift","Time In","Time Out","Working Hrs","Raw Status","Status","Remark","Master Issue"
                ]
'''
if old_cols not in s:
    raise RuntimeError("review display columns anchor not found")
s = s.replace(old_cols, new_cols, 1)

old_disabled = '''                    disabled=["ID","Issue Type","Date","Employee ID","Shift","Time In","Time Out","Working Hrs","Raw Status","Master Issue"],
'''
new_disabled = '''                    disabled=["ID","Issue Type","Master Division","Date","Employee ID","Shift","Time In","Time Out","Working Hrs","Raw Status","Master Issue"],
'''
if old_disabled not in s:
    raise RuntimeError("review editor disabled anchor not found")
s = s.replace(old_disabled, new_disabled, 1)

# Replace the caption to explain the new safety semantics.
old_caption = '''                st.caption(
                    f"Selected: {selected_count:,} row(s). For division mismatch, choose 'Use Raw Biometric Status (Auto)' "
                    "to convert PP→Present, WO→WO, AA→Absent, EL→EL while keeping incomplete punches in HR Review. "
                    "Raw Status remains read-only for biometric audit."
                )
'''
new_caption = '''                st.caption(
                    f"Selected: {selected_count:,} row(s). 'Use Raw Biometric Status (Auto)' converts "
                    "PP→Present, WO→WO, AA→Absent and EL→EL while incomplete punches stay in HR Review. "
                    "For Division Mismatch, the safe default keeps Employee Master unchanged and resolves only the attendance row."
                )
                if "Division Mismatch" in edited.loc[
                    edited["Select"].fillna(False).astype(bool), "Issue Type"
                ].astype(str).tolist():
                    if mismatch_master_action == "Keep Employee Master Division":
                        st.info(
                            "Safe mode selected: attendance can be resolved at the worked location while the employee's "
                            "permanent Employee Master division remains unchanged."
                        )
                    else:
                        st.warning(
                            "Master move selected: resolving a Division Mismatch will permanently update that employee's "
                            "Employee Master division to the attendance division. Use this only for a confirmed permanent transfer/correction."
                        )
'''
if old_caption not in s:
    raise RuntimeError("review caption anchor not found")
s = s.replace(old_caption, new_caption, 1)

# Replace resolution transaction logic. This is the critical safety fix.
old_logic = '''                        selected = edited[edited["Select"].fillna(False).astype(bool)].copy()
                        conn=get_pg_conn()
                        try:
                            cur=conn.cursor(); master_ids=set(); resolved_rows=0; remaining_rows=0
                            for _,r in selected.iterrows():
                                final_status = str(r["Status"])
                                if bulk_status == "Use Raw Biometric Status (Auto)":
                                    final_status = _map_attendance_status(
                                        r["Raw Status"], r["Working Hrs"], r["Time In"], r["Time Out"]
                                    )
                                elif bulk_status != "Keep Each Row Status":
                                    final_status = bulk_status
                                final_division = _clean_text(r["Division"])
                                if bulk_division != "Keep Each Row Division":
                                    final_division = bulk_division
                                employee_name=_clean_text(r["Employee Name"]) or str(r["Employee ID"])
                                department=_clean_text(r["Department"]) or "General"
                                designation=_clean_text(r["Designation"]) or "Employee"
                                source_issue=_clean_text(r["Master Issue"])
                                resolved = final_status != "HR Review"
                                cur.execute(
                                    """UPDATE attendance SET status=%s,remark=%s,review_required=%s,reviewed_by=%s,
                                       division=%s,designation=%s,source_employee_name=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s""",
                                    (final_status,str(r["Remark"] or ""),not resolved,_current_user["username"],
                                     final_division,designation,employee_name,int(r["ID"]))
                                )
                                if resolved:
                                    resolved_rows += 1
                                else:
                                    remaining_rows += 1
                                if resolved and source_issue:
                                    cur.execute(
                                        """INSERT INTO employees(employee_id,employee_name,department,designation,employee_type,shift,division,status)
                                           VALUES (%s,%s,%s,%s,'Permanent',%s,%s,'Active')
                                           ON CONFLICT(employee_id) DO UPDATE SET employee_name=excluded.employee_name,
                                           department=excluded.department,designation=excluded.designation,
                                           division=excluded.division,status='Active'""",
                                        (str(r["Employee ID"]),employee_name,department,designation,
                                         str(r["Shift"]) if str(r["Shift"]) in ("A","B") else "General",final_division)
                                    )
                                    master_ids.add(str(r["Employee ID"]))
                            for eid in master_ids:
                                cur.execute("UPDATE attendance SET source_issue='' WHERE employee_id=%s",(eid,))
                            conn.commit();cur.close()
                            st.success(
                                f"Selected HR Review rows saved: {resolved_rows:,} resolved, {remaining_rows:,} kept in HR Review. "
                                f"Employee Master updated for {len(master_ids):,} confirmed exception employee(s)."
                            )
                            st.rerun()
'''
new_logic = '''                        selected = edited[edited["Select"].fillna(False).astype(bool)].copy()
                        conn=get_pg_conn()
                        try:
                            cur=conn.cursor()
                            master_created_or_completed=set()
                            master_moved=set()
                            resolved_rows=0
                            remaining_rows=0
                            attendance_only_mismatch_rows=0

                            for _,r in selected.iterrows():
                                final_status = str(r["Status"])
                                if bulk_status == "Use Raw Biometric Status (Auto)":
                                    final_status = _map_attendance_status(
                                        r["Raw Status"], r["Working Hrs"], r["Time In"], r["Time Out"]
                                    )
                                elif bulk_status != "Keep Each Row Status":
                                    final_status = bulk_status

                                final_division = _clean_text(r["Division"])
                                if bulk_division != "Keep Each Row Division":
                                    final_division = bulk_division

                                employee_id = str(r["Employee ID"])
                                employee_name=_clean_text(r["Employee Name"]) or employee_id
                                department=_clean_text(r["Department"]) or "General"
                                designation=_clean_text(r["Designation"]) or "Employee"
                                source_issue=_clean_text(r["Master Issue"])
                                issue_type=_clean_text(r["Issue Type"])
                                resolved = final_status != "HR Review"

                                # Resolve only the selected attendance row. A resolved row's
                                # master/source exception is cleared on that row, not across
                                # the employee's entire attendance history.
                                cur.execute(
                                    """UPDATE attendance SET status=%s,remark=%s,review_required=%s,reviewed_by=%s,
                                       division=%s,designation=%s,source_employee_name=%s,
                                       source_issue=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s""",
                                    (
                                        final_status,str(r["Remark"] or ""),not resolved,_current_user["username"],
                                        final_division,designation,employee_name,
                                        "" if resolved else source_issue,
                                        int(r["ID"])
                                    )
                                )

                                if resolved:
                                    resolved_rows += 1
                                else:
                                    remaining_rows += 1
                                    continue

                                if issue_type == "Division Mismatch":
                                    if mismatch_master_action == "Move Employee to Attendance Division":
                                        # Permanent master correction: change only the master division.
                                        # Do not overwrite authoritative name/department/designation/salary fields.
                                        cur.execute(
                                            """UPDATE employees
                                               SET division=%s
                                               WHERE employee_id=%s""",
                                            (final_division, employee_id)
                                        )
                                        master_moved.add(employee_id)
                                    else:
                                        # Temporary cross-location work: attendance is resolved at
                                        # the worked location; Employee Master remains untouched.
                                        attendance_only_mismatch_rows += 1

                                elif issue_type == "Unknown Employee":
                                    # Existing unknown/pending-master workflow remains available
                                    # after explicit HR selection and final attendance resolution.
                                    cur.execute(
                                        """INSERT INTO employees(
                                               employee_id,employee_name,department,designation,
                                               employee_type,shift,division,status
                                           )
                                           VALUES (%s,%s,%s,%s,'Permanent',%s,%s,'Active')
                                           ON CONFLICT(employee_id) DO UPDATE SET
                                               employee_name=excluded.employee_name,
                                               department=excluded.department,
                                               designation=excluded.designation,
                                               division=excluded.division,
                                               status='Active'""",
                                        (
                                            employee_id,employee_name,department,designation,
                                            str(r["Shift"]) if str(r["Shift"]) in ("A","B") else "General",
                                            final_division
                                        )
                                    )
                                    master_created_or_completed.add(employee_id)

                            conn.commit();cur.close()

                            record_audit_event(
                                _current_user["username"], "HR_REVIEW_RESOLVE", "Attendance",
                                "Rows", str(len(selected)),
                                (
                                    f"Resolved={resolved_rows}; Remaining={remaining_rows}; "
                                    f"AttendanceOnlyDivisionMismatch={attendance_only_mismatch_rows}; "
                                    f"MasterMoved={len(master_moved)}; "
                                    f"UnknownMasterCompleted={len(master_created_or_completed)}"
                                )
                            )

                            st.success(
                                f"Selected HR Review rows saved: {resolved_rows:,} resolved, "
                                f"{remaining_rows:,} kept in HR Review. "
                                f"{attendance_only_mismatch_rows:,} division-mismatch row(s) resolved without changing Employee Master; "
                                f"{len(master_moved):,} employee master division(s) moved; "
                                f"{len(master_created_or_completed):,} unknown/pending employee master(s) completed."
                            )
                            st.rerun()
'''
if old_logic not in s:
    raise RuntimeError("HR Review resolution transaction anchor not found")
s = s.replace(old_logic, new_logic, 1)

p.write_text(s, encoding="utf-8")
print("Applied V11.3 safe division-mismatch resolution")
