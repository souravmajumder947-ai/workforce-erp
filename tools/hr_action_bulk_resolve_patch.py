from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

# Missing attendance means no attendance row anywhere for that employee/date.
old_join = '''               LEFT JOIN attendance a
                 ON a.employee_id=e.employee_id
                AND a.work_date=?
                AND a.division=e.division
'''
new_join = '''               LEFT JOIN attendance a
                 ON a.employee_id=e.employee_id
                AND a.work_date=?
'''
if old_join in text:
    text = text.replace(old_join, new_join, 1)

start_marker = '        with st.expander(f"Employee Master Pending ({len(master_pending):,})", expanded=(reviews.empty and not master_pending.empty)):'
end_marker = '        if reviews.empty:'
start = text.find(start_marker)
if start < 0:
    raise SystemExit('Employee Master Pending block not found')
end = text.find(end_marker, start)
if end < 0:
    raise SystemExit('HR review continuation marker not found')

replacement = '''        with st.expander(f"Employee Master Pending ({len(master_pending):,})", expanded=(reviews.empty and not master_pending.empty)):
            if master_pending.empty:
                st.success("No temporary employee masters are waiting for HR completion.")
            else:
                mp = master_pending.rename(columns={
                    "division":"Division","employee_id":"Employee ID","employee_name":"Employee Name",
                    "department":"Department","designation":"Designation","shift":"Shift",
                    "status":"Status","remarks":"HR Remarks"
                }).copy()
                mp.insert(0, "Select", False)

                try:
                    dept_ref = read_df(
                        """SELECT department FROM departments WHERE COALESCE(TRIM(department),'')<>''
                           UNION
                           SELECT DISTINCT department FROM employees
                           WHERE COALESCE(TRIM(department),'')<>''
                             AND LOWER(TRIM(department))<>'hr review'
                           ORDER BY department"""
                    )
                    dept_options = sorted({
                        _clean_text(v) for v in dept_ref.get("department", pd.Series(dtype=str)).tolist()
                        if _clean_text(v) and _clean_text(v).lower() != "hr review"
                    })
                except Exception:
                    dept_options = []

                m1,m2,m3,m4 = st.columns([1,1.25,1.15,1.0])
                select_all_master = m1.checkbox(
                    f"Select all pending ({len(mp):,})", value=False, key="v84_select_all_master_pending"
                )
                bulk_master_department = m2.selectbox(
                    "Bulk Department",
                    ["Keep Each Row Department"] + dept_options,
                    key="v84_bulk_master_department"
                )
                bulk_master_division = m3.selectbox(
                    "Bulk Division",
                    ["Keep Each Row Division"] + DIVISIONS,
                    key="v84_bulk_master_division"
                )
                bulk_master_shift = m4.selectbox(
                    "Bulk Shift",
                    ["Keep Each Row Shift","A","B","General"],
                    key="v84_bulk_master_shift"
                )
                if select_all_master:
                    mp["Select"] = True

                master_editor = st.data_editor(
                    mp[["Select","Division","Employee ID","Employee Name","Department","Designation","Shift"]],
                    hide_index=True,use_container_width=True,height=430,
                    disabled=["Employee ID"],
                    column_config={
                        "Select":st.column_config.CheckboxColumn("Select",default=False),
                        "Division":st.column_config.SelectboxColumn("Division",options=DIVISIONS,required=True),
                        "Employee Name":st.column_config.TextColumn("Employee Name"),
                        "Department":st.column_config.SelectboxColumn(
                            "Department",options=["HR Review"] + dept_options,required=True
                        ),
                        "Designation":st.column_config.TextColumn("Designation"),
                        "Shift":st.column_config.SelectboxColumn("Shift",options=["A","B","General"],required=True),
                    },
                    key="v84_master_pending_editor"
                )
                selected_master_count = int(master_editor["Select"].fillna(False).astype(bool).sum())
                st.caption(
                    f"Selected: {selected_master_count:,}. Correct Department / Division / Designation / Shift here. "
                    "Rows disappear from Employee Master Pending once Department is no longer HR Review."
                )

                if can_edit_hr(_current_role):
                    confirm_master = st.checkbox(
                        "I confirm HR has verified the selected employee master details.",
                        value=False,key="v84_confirm_master_pending"
                    )
                    if st.button(
                        "Save Selected Employee Masters",
                        type="primary",use_container_width=True,
                        disabled=(selected_master_count == 0 or not confirm_master),
                        key="v84_save_master_pending"
                    ):
                        selected_mp = master_editor[master_editor["Select"].fillna(False).astype(bool)].copy()
                        conn = get_pg_conn()
                        try:
                            cur = conn.cursor(); resolved_master = 0; still_pending_master = 0
                            for _,r in selected_mp.iterrows():
                                employee_id = str(r["Employee ID"])
                                employee_name = _clean_text(r["Employee Name"]) or employee_id
                                department = _clean_text(r["Department"]) or "HR Review"
                                designation = _clean_text(r["Designation"]) or "Employee"
                                division = _clean_text(r["Division"]) or "Greater Noida Plant"
                                shift = _clean_text(r["Shift"]) or "General"
                                if bulk_master_department != "Keep Each Row Department":
                                    department = bulk_master_department
                                if bulk_master_division != "Keep Each Row Division":
                                    division = bulk_master_division
                                if bulk_master_shift != "Keep Each Row Shift":
                                    shift = bulk_master_shift
                                cur.execute(
                                    """UPDATE employees
                                       SET employee_name=%s,department=%s,designation=%s,division=%s,shift=%s,status='Active'
                                       WHERE employee_id=%s""",
                                    (employee_name,department,designation,division,shift,employee_id)
                                )
                                if department.strip().lower() != "hr review":
                                    resolved_master += 1
                                    cur.execute(
                                        """UPDATE attendance SET source_issue=''
                                           WHERE employee_id=%s
                                             AND LOWER(COALESCE(source_issue,'')) LIKE %s""",
                                        (employee_id, "%not found%")
                                    )
                                else:
                                    still_pending_master += 1
                            conn.commit(); cur.close()
                            st.success(
                                f"Employee Master saved: {resolved_master:,} completed, "
                                f"{still_pending_master:,} still pending HR department confirmation."
                            )
                            st.rerun()
                        except Exception:
                            conn.rollback(); raise
                        finally:
                            conn.close()
                else:
                    st.info("Only Admin / HR can update pending employee masters.")

        with st.expander(f"Missing Attendance on {global_work_date.strftime('%d %b %Y')} ({len(missing_attendance):,})", expanded=False):
            if missing_attendance.empty:
                st.success("Every active employee has an attendance record for this date.")
            else:
                ma = missing_attendance.rename(columns={
                    "division":"Division","employee_id":"Employee ID","employee_name":"Employee Name",
                    "department":"Department","designation":"Designation","shift":"Shift"
                }).copy()
                ma.insert(0,"Select",False)
                ma["Date"] = global_work_date.strftime("%d/%m/%Y")
                ma["Status"] = ""
                ma["HR Remark"] = ""

                a1,a2,a3 = st.columns([1,1.25,1.5])
                select_all_missing = a1.checkbox(
                    f"Select all missing ({len(ma):,})", value=False, key="v84_select_all_missing"
                )
                bulk_missing_status = a2.selectbox(
                    "Bulk Attendance Status",
                    ["Keep Each Row Status","WO","Absent","Leave","Holiday","LWP","Present","Half Day","CL","SL","EL"],
                    key="v84_bulk_missing_status"
                )
                bulk_missing_remark = a3.text_input(
                    "Bulk HR Remark", value="", placeholder="Optional remark for selected rows",
                    key="v84_bulk_missing_remark"
                )
                if select_all_missing:
                    ma["Select"] = True

                missing_editor = st.data_editor(
                    ma[["Select","Division","Employee ID","Employee Name","Department","Designation","Shift","Date","Status","HR Remark"]],
                    hide_index=True,use_container_width=True,height=430,
                    disabled=["Division","Employee ID","Employee Name","Department","Designation","Shift","Date"],
                    column_config={
                        "Select":st.column_config.CheckboxColumn("Select",default=False),
                        "Status":st.column_config.SelectboxColumn(
                            "Status",options=["","WO","Absent","Leave","Holiday","LWP","Present","Half Day","CL","SL","EL"]
                        ),
                        "HR Remark":st.column_config.TextColumn("HR Remark"),
                    },
                    key="v84_missing_attendance_editor"
                )
                selected_missing_count = int(missing_editor["Select"].fillna(False).astype(bool).sum())
                st.caption(
                    f"Selected: {selected_missing_count:,}. Choose the actual status. "
                    "Saving creates the missing attendance record and removes the employee from this list."
                )

                if can_edit_hr(_current_role):
                    confirm_missing = st.checkbox(
                        "I confirm HR has verified the selected missing-attendance rows.",
                        value=False,key="v84_confirm_missing_attendance"
                    )
                    if st.button(
                        "Resolve Selected Missing Attendance",
                        type="primary",use_container_width=True,
                        disabled=(selected_missing_count == 0 or not confirm_missing),
                        key="v84_resolve_missing_attendance"
                    ):
                        selected_ma = missing_editor[missing_editor["Select"].fillna(False).astype(bool)].copy()
                        prepared = []
                        invalid = []
                        for _,r in selected_ma.iterrows():
                            final_status = _clean_text(r["Status"])
                            if bulk_missing_status != "Keep Each Row Status":
                                final_status = bulk_missing_status
                            if not final_status:
                                invalid.append(str(r["Employee ID"]))
                                continue
                            remark = _clean_text(bulk_missing_remark) or _clean_text(r["HR Remark"]) or "Missing attendance resolved by HR"
                            prepared.append((r, final_status, remark))
                        if invalid:
                            st.error(
                                "Choose an attendance status for every selected employee. Missing status: "
                                + ", ".join(invalid[:20])
                            )
                        else:
                            conn = get_pg_conn()
                            try:
                                cur = conn.cursor()
                                for r,final_status,remark in prepared:
                                    shift = _clean_text(r["Shift"]) or "General"
                                    cur.execute(
                                        """INSERT INTO attendance(
                                               work_date,shift,employee_id,status,ot_hours,division,designation,
                                               day_name,time_in,time_out,working_hours,raw_status,remark,source_type,
                                               review_required,reviewed_by,source_employee_name,source_issue,updated_at
                                           ) VALUES (%s,%s,%s,%s,0,%s,%s,%s,NULL,NULL,0,'HR MANUAL',%s,
                                                     'HR Missing Attendance',FALSE,%s,%s,'',CURRENT_TIMESTAMP)
                                           ON CONFLICT(work_date,shift,employee_id) DO UPDATE SET
                                               status=excluded.status,division=excluded.division,
                                               designation=excluded.designation,day_name=excluded.day_name,
                                               raw_status='HR MANUAL',remark=excluded.remark,
                                               source_type='HR Missing Attendance',review_required=FALSE,
                                               reviewed_by=excluded.reviewed_by,source_employee_name=excluded.source_employee_name,
                                               source_issue='',updated_at=CURRENT_TIMESTAMP""",
                                        (
                                            global_work_date.isoformat(),shift,str(r["Employee ID"]),final_status,
                                            _clean_text(r["Division"]),_clean_text(r["Designation"]),
                                            global_work_date.strftime("%A"),remark,_current_user["username"],
                                            _clean_text(r["Employee Name"]) or str(r["Employee ID"])
                                        )
                                    )
                                conn.commit(); cur.close()
                                st.success(f"{len(prepared):,} missing attendance row(s) resolved and saved.")
                                st.rerun()
                            except Exception:
                                conn.rollback(); raise
                            finally:
                                conn.close()
                else:
                    st.info("Only Admin / HR can resolve missing attendance.")

'''

text = text[:start] + replacement + text[end:]
p.write_text(text, encoding='utf-8')
