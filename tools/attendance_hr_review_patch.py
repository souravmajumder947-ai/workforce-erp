from pathlib import Path
import re

path = Path('app.py')
text = path.read_text(encoding='utf-8')

def replace_once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 match, found {count}')
    text = text.replace(old, new, 1)

def regex_once(pattern, replacement, label):
    global text
    text2, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 match, found {count}')
    text = text2

replace_once(
    '            ("reviewed_by", "TEXT"),\n            ("updated_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")',
    '            ("reviewed_by", "TEXT"),\n            ("source_employee_name", "TEXT"),\n            ("source_issue", "TEXT"),\n            ("updated_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")',
    'attendance source columns migration'
)

new_validate = '''def _validate_and_enrich_attendance_records(records):
    """Validate attendance without blocking good rows.

    Matched employees are enriched from Employee Master. Unknown Employee IDs and
    division mismatches are retained as attendance transactions but forced to
    HR Review. Employee Master is never created/changed during import.
    """
    if not records:
        return records

    master = read_df(
        """SELECT employee_id,employee_name,division,designation,shift,status
           FROM employees"""
    )
    master_map = {}
    if not master.empty:
        master["employee_id"] = master["employee_id"].astype(str)
        master_map = {str(r["employee_id"]): r.to_dict() for _, r in master.iterrows()}

    for rec in records:
        emp_id = str(rec.get("employee_id", "")).strip()
        rec["source_employee_name"] = _clean_text(rec.get("employee_name")) or emp_id
        emp = master_map.get(emp_id)
        issue = ""
        if not emp:
            issue = "Employee ID not found in Employee Master"
        else:
            master_div = _clean_text(emp.get("division"))
            rec_div = _clean_text(rec.get("division"))
            if master_div and rec_div and master_div != rec_div:
                issue = f"Division mismatch: master={master_div}; file={rec_div}"
            else:
                rec["employee_name"] = _clean_text(emp.get("employee_name")) or rec.get("employee_name") or emp_id
                rec["designation"] = _clean_text(emp.get("designation")) or rec.get("designation", "")
                if not _clean_text(rec.get("shift")):
                    rec["shift"] = _clean_text(emp.get("shift")) or "General"

        rec["source_issue"] = issue
        if issue:
            rec["status"] = "HR Review"
            rec["review_required"] = True
            existing_remark = _clean_text(rec.get("remark"))
            if issue not in existing_remark:
                rec["remark"] = f"{existing_remark} | {issue}".strip(" |")
            rec["ot_hours"] = 0.0

    return records
'''
regex_once(r'def _validate_and_enrich_attendance_records\(records\):.*?(?=\ndef _hours_value\(value\):)', new_validate, 'validation')

new_bulk = '''def _bulk_upsert_attendance(records, source_type):
    if not records:
        return 0
    records = _validate_and_enrich_attendance_records(records)
    conn = get_pg_conn()
    try:
        cur = conn.cursor()
        payload = []
        for rec in records:
            payload.append((
                rec["work_date"], rec["shift"], rec["employee_id"], rec["status"], float(rec.get("ot_hours", 0)),
                rec["division"], rec.get("designation", ""), rec.get("day_name", ""), rec.get("time_in"), rec.get("time_out"),
                float(rec.get("working_hours", 0)), rec.get("raw_status", ""), rec.get("remark", ""), source_type,
                bool(rec.get("review_required", False)), rec.get("source_employee_name", rec.get("employee_name", "")),
                rec.get("source_issue", ""),
            ))
        execute_values(cur, """
            INSERT INTO attendance(
                work_date, shift, employee_id, status, ot_hours, division, designation,
                day_name, time_in, time_out, working_hours, raw_status, remark,
                source_type, review_required, source_employee_name, source_issue
            ) VALUES %s
            ON CONFLICT(work_date, shift, employee_id) DO UPDATE SET
                status=excluded.status, ot_hours=excluded.ot_hours, division=excluded.division,
                designation=excluded.designation, day_name=excluded.day_name,
                time_in=excluded.time_in, time_out=excluded.time_out,
                working_hours=excluded.working_hours, raw_status=excluded.raw_status,
                remark=CASE WHEN COALESCE(attendance.remark,'') <> '' AND COALESCE(excluded.remark,'') = '' THEN attendance.remark ELSE excluded.remark END,
                source_type=excluded.source_type, review_required=excluded.review_required,
                source_employee_name=excluded.source_employee_name, source_issue=excluded.source_issue,
                updated_at=CURRENT_TIMESTAMP
        """, payload, page_size=1000)
        conn.commit(); cur.close(); return len(payload)
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()
'''
regex_once(r'def _bulk_upsert_attendance\(records, source_type\):.*?(?=\n\n\n# ============================================================\n# PAYROLL V4)', new_bulk, 'bulk upsert')

new_precheck = '''def attendance_precheck(preview_df):
    """Preview attendance and route master exceptions to HR Review."""
    result = {
        "rows_ready": 0, "employees": 0, "dates": 0, "duplicates": 0,
        "unknown_ids": [], "division_mismatches": [], "hr_review": 0,
        "master_exception_rows": 0, "status_summary": pd.DataFrame()
    }
    if preview_df is None or preview_df.empty:
        return result

    df = preview_df.copy()
    result["employees"] = int(df["employee_id"].astype(str).nunique())
    result["dates"] = int(df["work_date"].astype(str).nunique())
    dup_mask = df.duplicated(subset=["work_date","shift","employee_id"], keep=False)
    result["duplicates"] = int(dup_mask.sum())

    master = read_df("SELECT employee_id,division FROM employees")
    master_map = {}
    if not master.empty:
        master_map = {str(r["employee_id"]).strip(): _clean_text(r.get("division")) for _, r in master.iterrows()}

    unknown, mismatch, exception_mask = [], [], []
    for _, r in df.iterrows():
        eid = str(r.get("employee_id","")).strip()
        div = _clean_text(r.get("division"))
        has_issue = False
        if eid not in master_map:
            unknown.append(eid); has_issue = True
        elif master_map[eid] and div and master_map[eid] != div:
            mismatch.append(f"{eid}: master={master_map[eid]}, file={div}"); has_issue = True
        exception_mask.append(has_issue)

    result["unknown_ids"] = sorted(set(x for x in unknown if x))
    result["division_mismatches"] = sorted(set(mismatch))
    exception_series = pd.Series(exception_mask, index=df.index)
    result["master_exception_rows"] = int(exception_series.sum())
    biometric_review = df["status"].astype(str).eq("HR Review")
    result["hr_review"] = int((biometric_review | exception_series).sum())
    result["rows_ready"] = max(0, len(df) - result["duplicates"])
    display_status = df["status"].astype(str).copy()
    display_status.loc[exception_series] = "HR Review"
    result["status_summary"] = display_status.value_counts().rename_axis("Status").reset_index(name="Rows").sort_values("Status")
    return result
'''
regex_once(r'def attendance_precheck\(preview_df\):.*?(?=\ndef import_salary_master_excel\(uploaded_file, division\):)', new_precheck, 'precheck')

replace_once(
'''                    if precheck["unknown_ids"]:
                        st.error(
                            f"{len(precheck['unknown_ids'])} Employee ID(s) are not in Employee Master: "
                            + ", ".join(precheck["unknown_ids"][:20])
                        )

                    if precheck["division_mismatches"]:
                        st.error(
                            "Division mismatch found: "
                            + " | ".join(precheck["division_mismatches"][:12])
                        )

                    hard_errors = (
                        precheck["duplicates"] > 0
                        or len(precheck["unknown_ids"]) > 0
                        or len(precheck["division_mismatches"]) > 0
                    )

                    if not hard_errors:
                        st.success(
                            f"{len(attendance_preview):,} row(s) passed pre-import checks for **{actual}**."
                        )
''',
'''                    if precheck["unknown_ids"]:
                        st.warning(
                            f"{len(precheck['unknown_ids'])} Employee ID(s) are not in Employee Master. "
                            "Their attendance will be imported as HR Review: "
                            + ", ".join(precheck["unknown_ids"][:20])
                        )

                    if precheck["division_mismatches"]:
                        st.warning(
                            "Division mismatch rows will be imported as HR Review: "
                            + " | ".join(precheck["division_mismatches"][:12])
                        )

                    hard_errors = precheck["duplicates"] > 0

                    if not hard_errors:
                        st.success(
                            f"{len(attendance_preview):,} row(s) can be imported for **{actual}**. "
                            f"{precheck['hr_review']:,} row(s) will stay in HR Review until HR confirms them."
                        )
''', 'exception UI')

new_review = '''    with tab_review:
        clause,params=v5_division_clause(global_division,"a.")
        reviews=read_df(
            """SELECT a.id,a.division,a.work_date,a.employee_id,
                      COALESCE(e.employee_name,a.source_employee_name,a.employee_id) AS employee_name,
                      COALESCE(e.department,'General') AS department,
                      COALESCE(a.designation,e.designation,'Employee') AS designation,
                      a.shift,a.time_in,a.time_out,a.working_hours,a.raw_status,a.status,a.remark,
                      COALESCE(a.source_issue,'') AS source_issue
               FROM attendance a LEFT JOIN employees e ON e.employee_id=a.employee_id
               WHERE (a.status='HR Review' OR a.review_required=TRUE) """ + clause + """
               ORDER BY a.work_date DESC,COALESCE(e.employee_name,a.source_employee_name,a.employee_id)""",
            params
        )
        if reviews.empty:
            st.success("No attendance records are waiting for HR Review.")
        else:
            st.caption(f"{len(reviews):,} record(s) require HR decision.")
            if (reviews["source_issue"].astype(str).str.len() > 0).any():
                st.info("When HR resolves an Unknown Employee ID or Division mismatch, the reviewed identity details are created/updated in Employee Master automatically.")
            review_show = reviews.rename(columns={
                "id":"ID","division":"Division","work_date":"Date","employee_id":"Employee ID","employee_name":"Employee Name",
                "department":"Department","designation":"Designation","shift":"Shift","time_in":"Time In","time_out":"Time Out",
                "working_hours":"Working Hrs","raw_status":"Raw Status","status":"Status","remark":"Remark","source_issue":"Master Issue"
            })
            edited=st.data_editor(
                review_show, hide_index=True,use_container_width=True,
                disabled=["ID","Date","Employee ID","Shift","Time In","Time Out","Working Hrs","Raw Status","Master Issue"],
                column_config={
                    "Division":st.column_config.SelectboxColumn("Division",options=DIVISIONS,required=True),
                    "Employee Name":st.column_config.TextColumn("Employee Name"),
                    "Department":st.column_config.TextColumn("Department"),
                    "Designation":st.column_config.TextColumn("Designation"),
                    "Status":st.column_config.SelectboxColumn("Status",options=["Present","Half Day","Absent","LWP","WO","Holiday","Leave","CL","SL","EL","HR Review"]),
                    "Remark":st.column_config.TextColumn("HR Remark"),
                }, key="v72_review_editor"
            )
            if can_edit_hr(_current_role) and st.button("Resolve HR Reviews & Update Master",type="primary",use_container_width=True,key="v72_resolve_review"):
                conn=get_pg_conn()
                try:
                    cur=conn.cursor(); master_ids=set()
                    for _,r in edited.iterrows():
                        resolved=str(r["Status"])!="HR Review"
                        division=_clean_text(r["Division"])
                        employee_name=_clean_text(r["Employee Name"]) or str(r["Employee ID"])
                        department=_clean_text(r["Department"]) or "General"
                        designation=_clean_text(r["Designation"]) or "Employee"
                        source_issue=_clean_text(r["Master Issue"])
                        cur.execute(
                            """UPDATE attendance SET status=%s,remark=%s,review_required=%s,reviewed_by=%s,
                               division=%s,designation=%s,source_employee_name=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s""",
                            (str(r["Status"]),str(r["Remark"] or ""),not resolved,_current_user["username"],division,designation,employee_name,int(r["ID"]))
                        )
                        if resolved and source_issue:
                            cur.execute(
                                """INSERT INTO employees(employee_id,employee_name,department,designation,employee_type,shift,division,status)
                                   VALUES (%s,%s,%s,%s,'Permanent',%s,%s,'Active')
                                   ON CONFLICT(employee_id) DO UPDATE SET employee_name=excluded.employee_name,
                                   department=excluded.department,designation=excluded.designation,division=excluded.division,status='Active'""",
                                (str(r["Employee ID"]),employee_name,department,designation,
                                 str(r["Shift"]) if str(r["Shift"]) in ("A","B") else "General",division)
                            )
                            master_ids.add(str(r["Employee ID"]))
                    for eid in master_ids:
                        cur.execute("UPDATE attendance SET source_issue='' WHERE employee_id=%s",(eid,))
                    conn.commit();cur.close()
                    st.success(f"HR Review decisions saved. Employee Master updated for {len(master_ids):,} exception employee(s).")
                    st.rerun()
                except Exception:
                    conn.rollback();raise
                finally: conn.close()

'''
regex_once(r'    with tab_review:.*?(?=    with tab_month:)', new_review, 'review tab')

path.write_text(text, encoding='utf-8')
print('Attendance HR review patch applied')
