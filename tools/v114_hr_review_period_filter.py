from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V11.4 HR REVIEW PERIOD FILTER"
if MARK in s:
    print("V11.4 HR Review period filter already applied")
    raise SystemExit(0)

old_start = '''    with tab_review:
        clause,params=v5_division_clause(global_division,"a.")
        # V11.3 SAFE DIVISION MISMATCH RESOLUTION
        reviews=read_df(
            """SELECT a.id,a.division,a.work_date,a.employee_id,
                      COALESCE(e.employee_name,a.source_employee_name,a.employee_id) AS employee_name,
                      COALESCE(e.division,'') AS master_division,
                      COALESCE(e.department,'General') AS department,
                      COALESCE(a.designation,e.designation,'Employee') AS designation,
                      a.shift,a.time_in,a.time_out,a.working_hours,a.raw_status,a.status,a.remark,
                      COALESCE(a.source_issue,'') AS source_issue
               FROM attendance a LEFT JOIN employees e ON e.employee_id=a.employee_id
               WHERE (a.status='HR Review' OR a.review_required=TRUE)
                 AND COALESCE(UPPER(TRIM(e.status)),'ACTIVE') NOT IN ('INACTIVE','LEFT','RESIGNED','TERMINATED') """ + clause + """
               ORDER BY a.work_date DESC,COALESCE(e.employee_name,a.source_employee_name,a.employee_id)""",
            params
        )

        # Keep Missing Attendance aligned with the attendance period being reviewed.
        # If HR Review contains older attendance (for example August while today is September),
        # use the latest review date instead of today's global working date.
        if reviews.empty:
            missing_reference_date = global_work_date
        else:
            _review_dates = pd.to_datetime(reviews["work_date"], errors="coerce").dropna()
            missing_reference_date = (_review_dates.max().date() if not _review_dates.empty else global_work_date)
'''

new_start = '''    with tab_review:
        # V11.4 HR REVIEW PERIOD FILTER
        # HR Review has its own date context and no longer depends on the app-wide Working Date.
        _hr_today = global_work_date
        _hr_this_month_start = _hr_today.replace(day=1)
        _hr_prev_month_end = _hr_this_month_start - timedelta(days=1)
        _hr_prev_month_start = _hr_prev_month_end.replace(day=1)

        if "v114_hr_review_from" not in st.session_state:
            st.session_state["v114_hr_review_from"] = _hr_this_month_start
        if "v114_hr_review_to" not in st.session_state:
            st.session_state["v114_hr_review_to"] = _hr_today

        st.markdown("#### HR Review Period")
        q1,q2,q3,q4 = st.columns(4)
        if q1.button("Today", use_container_width=True, key="v114_hr_today"):
            st.session_state["v114_hr_review_from"] = _hr_today
            st.session_state["v114_hr_review_to"] = _hr_today
        if q2.button("Yesterday", use_container_width=True, key="v114_hr_yesterday"):
            _yesterday = _hr_today - timedelta(days=1)
            st.session_state["v114_hr_review_from"] = _yesterday
            st.session_state["v114_hr_review_to"] = _yesterday
        if q3.button("This Month", use_container_width=True, key="v114_hr_this_month"):
            st.session_state["v114_hr_review_from"] = _hr_this_month_start
            st.session_state["v114_hr_review_to"] = _hr_today
        if q4.button("Previous Month", use_container_width=True, key="v114_hr_prev_month"):
            st.session_state["v114_hr_review_from"] = _hr_prev_month_start
            st.session_state["v114_hr_review_to"] = _hr_prev_month_end

        dfrom,dto = st.columns(2)
        review_from_date = dfrom.date_input(
            "From Date", format="DD/MM/YYYY", key="v114_hr_review_from"
        )
        review_to_date = dto.date_input(
            "To Date", format="DD/MM/YYYY", key="v114_hr_review_to"
        )
        if review_from_date > review_to_date:
            st.warning("From Date was later than To Date, so the period has been read in chronological order.")
            review_from_date, review_to_date = review_to_date, review_from_date

        st.caption(
            f"Selected HR Review period: **{review_from_date.strftime('%d/%m/%Y')} – "
            f"{review_to_date.strftime('%d/%m/%Y')}**. This is independent of the left-side Working Date. "
            "Missing From BTS uses the selected To Date so HR can investigate one exact attendance day safely."
        )

        clause,params=v5_division_clause(global_division,"a.")
        # V11.3 SAFE DIVISION MISMATCH RESOLUTION
        reviews=read_df(
            """SELECT a.id,a.division,a.work_date,a.employee_id,
                      COALESCE(e.employee_name,a.source_employee_name,a.employee_id) AS employee_name,
                      COALESCE(e.division,'') AS master_division,
                      COALESCE(e.department,'General') AS department,
                      COALESCE(a.designation,e.designation,'Employee') AS designation,
                      a.shift,a.time_in,a.time_out,a.working_hours,a.raw_status,a.status,a.remark,
                      COALESCE(a.source_issue,'') AS source_issue
               FROM attendance a LEFT JOIN employees e ON e.employee_id=a.employee_id
               WHERE (a.status='HR Review' OR a.review_required=TRUE)
                 AND a.work_date BETWEEN ? AND ?
                 AND COALESCE(UPPER(TRIM(e.status)),'ACTIVE') NOT IN ('INACTIVE','LEFT','RESIGNED','TERMINATED') """ + clause + """
               ORDER BY a.work_date DESC,COALESCE(e.employee_name,a.source_employee_name,a.employee_id)""",
            (review_from_date.isoformat(), review_to_date.isoformat()) + params
        )

        # Missing From BTS follows the HR Review To Date, never the global Working Date.
        missing_reference_date = review_to_date
'''

if old_start not in s:
    raise RuntimeError("HR Review start/date anchor not found")
s = s.replace(old_start, new_start, 1)

old_filters = '''            f1,f2,f3,f4 = st.columns([1.05,1.25,1.35,1.15])
            div_options = sorted(reviews["division"].dropna().astype(str).unique().tolist())
            review_div_filter = f1.multiselect(
                "Division", div_options, default=[], placeholder="All divisions",
                key="v81_review_div_filter"
            )

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
            emp_options = sorted(employee_labels.keys(), key=lambda x: employee_labels[x].lower())
            review_emp_filter = f3.multiselect(
                "Employees", emp_options, default=[],
                format_func=lambda x: employee_labels.get(x,x),
                placeholder="All employees", key="v81_review_emp_filter"
            )

            issue_options = ["Missing Punch","Unknown Employee","Division Mismatch","Other HR Review"]
            review_issue_filter = f4.multiselect(
                "Issue Type", issue_options, default=[], placeholder="All issues",
                key="v81_review_issue_filter"
            )

            filtered = reviews.copy()
            if review_div_filter:
                filtered = filtered[filtered["division"].astype(str).isin(review_div_filter)]
            if isinstance(review_date_filter,(tuple,list)) and len(review_date_filter) == 2:
                filtered = filtered[
                    filtered["work_date_dt"].apply(lambda d: bool(d and review_date_filter[0] <= d <= review_date_filter[1]))
                ]
            if review_emp_filter:
                filtered = filtered[filtered["employee_id"].astype(str).isin([str(x) for x in review_emp_filter])]
            if review_issue_filter:
                filtered = filtered[filtered["issue_type"].isin(review_issue_filter)]
'''

new_filters = '''            f1,f2,f3 = st.columns([1.1,1.55,1.2])
            div_options = sorted(reviews["division"].dropna().astype(str).unique().tolist())
            review_div_filter = f1.multiselect(
                "Division", div_options, default=[], placeholder="All divisions",
                key="v81_review_div_filter"
            )

            employee_labels = {}
            for _,rr in reviews[["employee_id","employee_name"]].drop_duplicates().iterrows():
                eid = str(rr["employee_id"])
                employee_labels[eid] = f"{_clean_text(rr['employee_name']) or eid} · {eid}"
            emp_options = sorted(employee_labels.keys(), key=lambda x: employee_labels[x].lower())
            review_emp_filter = f2.multiselect(
                "Employees", emp_options, default=[],
                format_func=lambda x: employee_labels.get(x,x),
                placeholder="All employees", key="v81_review_emp_filter"
            )

            issue_options = ["Missing Punch","Unknown Employee","Division Mismatch","Other HR Review"]
            review_issue_filter = f3.multiselect(
                "Issue Type", issue_options, default=[], placeholder="All issues",
                key="v81_review_issue_filter"
            )

            filtered = reviews.copy()
            if review_div_filter:
                filtered = filtered[filtered["division"].astype(str).isin(review_div_filter)]
            if review_emp_filter:
                filtered = filtered[filtered["employee_id"].astype(str).isin([str(x) for x in review_emp_filter])]
            if review_issue_filter:
                filtered = filtered[filtered["issue_type"].isin(review_issue_filter)]
'''

if old_filters not in s:
    raise RuntimeError("HR Review inner date-filter anchor not found")
s = s.replace(old_filters, new_filters, 1)

old_save = '''                                            global_work_date.isoformat(),shift,str(r["Employee ID"]),final_status,
                                            _clean_text(r["Division"]),_clean_text(r["Designation"]),
                                            global_work_date.strftime("%A"),remark,_current_user["username"],
'''
new_save = '''                                            missing_reference_date.isoformat(),shift,str(r["Employee ID"]),final_status,
                                            _clean_text(r["Division"]),_clean_text(r["Designation"]),
                                            missing_reference_date.strftime("%A"),remark,_current_user["username"],
'''
if old_save not in s:
    raise RuntimeError("Missing-attendance save-date anchor not found")
s = s.replace(old_save, new_save, 1)

p.write_text(s, encoding="utf-8")
print("Applied V11.4 HR Review period filter")
