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


# Treat temporary biometric placeholders as still awaiting HR Master confirmation.
replace_once(
'''    master = read_df(
        """SELECT employee_id,employee_name,division,designation,shift,status
           FROM employees"""
    )''',
'''    master = read_df(
        """SELECT employee_id,employee_name,division,department,designation,shift,status
           FROM employees"""
    )''',
'validation master query'
)

replace_once(
'''        if not emp:
            issue = "Employee ID not found in Employee Master"
        else:
            master_div = _clean_text(emp.get("division"))''',
'''        pending_master = bool(emp) and _clean_text(emp.get("department")).upper() == "HR REVIEW"
        if not emp:
            issue = "Employee ID not found in Employee Master"
        elif pending_master:
            issue = "Employee ID awaiting HR Master confirmation"
        else:
            master_div = _clean_text(emp.get("division"))''',
'pending placeholder validation'
)

# Pending placeholders should remain visible as Unknown IDs in future prechecks.
replace_once(
'''    master = read_df("SELECT employee_id,division FROM employees")
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
            mismatch.append(f"{eid}: master={master_map[eid]}, file={div}"); has_issue = True''',
'''    master = read_df("SELECT employee_id,division,department FROM employees")
    master_map = {}
    if not master.empty:
        master_map = {
            str(r["employee_id"]).strip(): {
                "division": _clean_text(r.get("division")),
                "department": _clean_text(r.get("department")),
            }
            for _, r in master.iterrows()
        }

    unknown, mismatch, exception_mask = [], [], []
    for _, r in df.iterrows():
        eid = str(r.get("employee_id","")).strip()
        div = _clean_text(r.get("division"))
        has_issue = False
        emp_master = master_map.get(eid)
        if not emp_master or emp_master.get("department", "").upper() == "HR REVIEW":
            unknown.append(eid); has_issue = True
        elif emp_master.get("division") and div and emp_master.get("division") != div:
            mismatch.append(f"{eid}: master={emp_master.get('division')}, file={div}"); has_issue = True''',
'precheck pending placeholders'
)

# New unknown placeholders are clearly marked by Department=HR Review.
# Existing valid masters are never overwritten here.
replace_once(
'''                       ) VALUES (%s,%s,'HR Review',%s,'Permanent',%s,%s,'Active')
                       ON CONFLICT(employee_id) DO NOTHING""",''',
'''                       ) VALUES (%s,%s,'HR Review',%s,'Permanent',%s,%s,'Active')
                       ON CONFLICT(employee_id) DO NOTHING""",''',
'placeholder marker check'
)

new_review = r'''    with tab_review:
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
            reviews = reviews.copy()
            reviews["work_date_dt"] = pd.to_datetime(reviews["work_date"], errors="coerce").dt.date

            def _review_issue_type(row):
                issue = _clean_text(row.get("source_issue"))
                remark = _clean_text(row.get("remark"))
                raw = _clean_text(row.get("raw_status")).upper().replace(" ", "")
                tin = _clean_text(row.get("time_in"))
                tout = _clean_text(row.get("time_out"))
                if "not found" in issue.lower() or "awaiting hr master" in issue.lower():
                    return "Unknown Employee"
                if "division mismatch" in issue.lower():
                    return "Division Mismatch"
                incomplete_punch = (
                    "incomplete pp" in remark.lower()
                    or (raw in {"PP","P","PRESENT"} and ((not tin or tin == "00:00") or (not tout or tout == "00:00")))
                )
                if incomplete_punch:
                    return "Missing Punch"
                return "Other HR Review"

            reviews["issue_type"] = reviews.apply(_review_issue_type, axis=1)

            st.markdown("#### HR Review Control Centre")
            st.caption(
                "Filter the exceptions, select only the rows HR has checked, then resolve those selected rows. "
                "Employee Master is updated only for selected and resolved master exceptions."
            )

            f1,f2,f3,f4 = st.columns([1.05,1.25,1.35,1.15])
            div_options = ["All Divisions"] + sorted(reviews["division"].dropna().astype(str).unique().tolist())
            review_div_filter = f1.selectbox("Division", div_options, key="v80_review_div_filter")

            valid_dates = [d for d in reviews["work_date_dt"].dropna().tolist()]
            min_review_date = min(valid_dates) if valid_dates else global_work_date
            max_review_date = max(valid_dates) if valid_dates else global_work_date
            review_date_filter = f2.date_input(
                "Date Range", value=(min_review_date,max_review_date), format="DD/MM/YYYY", key="v80_review_date_filter"
            )

            employee_labels = {}
            for _,rr in reviews[["employee_id","employee_name"]].drop_duplicates().iterrows():
                eid = str(rr["employee_id"])
                employee_labels[eid] = f"{_clean_text(rr['employee_name']) or eid} · {eid}"
            emp_options = ["All Employees"] + sorted(employee_labels.keys(), key=lambda x: employee_labels[x].lower())
            review_emp_filter = f3.selectbox(
                "Employee", emp_options,
                format_func=lambda x: x if x == "All Employees" else employee_labels.get(x,x),
                key="v80_review_emp_filter"
            )

            issue_options = ["All Issues","Missing Punch","Unknown Employee","Division Mismatch","Other HR Review"]
            review_issue_filter = f4.selectbox("Issue Type", issue_options, key="v80_review_issue_filter")

            filtered = reviews.copy()
            if review_div_filter != "All Divisions":
                filtered = filtered[filtered["division"].astype(str) == review_div_filter]
            if isinstance(review_date_filter,(tuple,list)) and len(review_date_filter) == 2:
                filtered = filtered[
                    filtered["work_date_dt"].apply(lambda d: bool(d and review_date_filter[0] <= d <= review_date_filter[1]))
                ]
            if review_emp_filter != "All Employees":
                filtered = filtered[filtered["employee_id"].astype(str) == str(review_emp_filter)]
            if review_issue_filter != "All Issues":
                filtered = filtered[filtered["issue_type"] == review_issue_filter]

            k1,k2,k3,k4 = st.columns(4)
            k1.metric("Filtered Reviews", f"{len(filtered):,}")
            k2.metric("Missing Punch", f"{int((filtered['issue_type']=='Missing Punch').sum()):,}")
            k3.metric("Master Exceptions", f"{int(filtered['issue_type'].isin(['Unknown Employee','Division Mismatch']).sum()):,}")
            k4.metric("Employees", f"{filtered['employee_id'].astype(str).nunique():,}")

            if filtered.empty:
                st.info("No HR Review rows match the selected filters.")
            else:
                if filtered["source_issue"].astype(str).str.len().gt(0).any():
                    st.info(
                        "Unknown Employee and Division Mismatch rows update Employee Master only after HR selects the row "
                        "and resolves it to a final attendance status."
                    )

                csel,cstatus,cdiv = st.columns([1,1.25,1.4])
                select_all_filtered = csel.checkbox(
                    f"Select all filtered ({len(filtered):,})", value=False, key="v80_select_all_filtered"
                )
                bulk_status = cstatus.selectbox(
                    "Bulk Status for Selected",
                    ["Keep Each Row Status","Present","Half Day","Absent","LWP","WO","Holiday","Leave","CL","SL","EL","HR Review"],
                    key="v80_bulk_review_status"
                )
                bulk_division = cdiv.selectbox(
                    "Bulk Division for Selected",
                    ["Keep Each Row Division"] + DIVISIONS,
                    key="v80_bulk_review_division"
                )

                review_show = filtered.rename(columns={
                    "id":"ID","division":"Division","work_date":"Date","employee_id":"Employee ID","employee_name":"Employee Name",
                    "department":"Department","designation":"Designation","shift":"Shift","time_in":"Time In","time_out":"Time Out",
                    "working_hours":"Working Hrs","raw_status":"Raw Status","status":"Status","remark":"Remark",
                    "source_issue":"Master Issue","issue_type":"Issue Type"
                }).copy()
                review_show.insert(0,"Select",bool(select_all_filtered))
                display_cols = [
                    "Select","ID","Issue Type","Division","Date","Employee ID","Employee Name","Department","Designation",
                    "Shift","Time In","Time Out","Working Hrs","Raw Status","Status","Remark","Master Issue"
                ]
                review_show = review_show[[c for c in display_cols if c in review_show.columns]]

                edited=st.data_editor(
                    review_show, hide_index=True,use_container_width=True,height=520,
                    disabled=["ID","Issue Type","Date","Employee ID","Shift","Time In","Time Out","Working Hrs","Raw Status","Master Issue"],
                    column_config={
                        "Select":st.column_config.CheckboxColumn("Select",default=False),
                        "Division":st.column_config.SelectboxColumn("Division",options=DIVISIONS,required=True),
                        "Employee Name":st.column_config.TextColumn("Employee Name"),
                        "Department":st.column_config.TextColumn("Department"),
                        "Designation":st.column_config.TextColumn("Designation"),
                        "Status":st.column_config.SelectboxColumn(
                            "Status",options=["Present","Half Day","Absent","LWP","WO","Holiday","Leave","CL","SL","EL","HR Review"]
                        ),
                        "Remark":st.column_config.TextColumn("HR Remark"),
                    }, key="v80_review_editor"
                )

                selected_count = int(edited["Select"].fillna(False).astype(bool).sum()) if "Select" in edited.columns else 0
                st.caption(
                    f"Selected: {selected_count:,} row(s). Bulk Status/Division, when chosen, is applied only to selected rows. "
                    "Raw Status is read-only and kept for biometric audit."
                )

                if can_edit_hr(_current_role):
                    confirm_selected = st.checkbox(
                        "I confirm HR has checked the selected rows.", value=False, key="v80_confirm_selected_reviews"
                    )
                    if st.button(
                        "Resolve Selected HR Reviews",
                        type="primary",use_container_width=True,
                        disabled=(selected_count == 0 or not confirm_selected),
                        key="v80_resolve_selected_reviews"
                    ):
                        selected = edited[edited["Select"].fillna(False).astype(bool)].copy()
                        conn=get_pg_conn()
                        try:
                            cur=conn.cursor(); master_ids=set(); resolved_rows=0; remaining_rows=0
                            for _,r in selected.iterrows():
                                final_status = str(r["Status"])
                                if bulk_status != "Keep Each Row Status":
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
                        except Exception:
                            conn.rollback();raise
                        finally:
                            conn.close()
                else:
                    st.info("Only Admin / HR can resolve HR Review rows.")

'''
regex_once(r'    with tab_review:.*?(?=    with tab_month:)', new_review, 'HR Review V2 block')

path.write_text(text, encoding='utf-8')
print('HR Review V2 patch applied')
