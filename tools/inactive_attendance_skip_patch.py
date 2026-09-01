from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

# 1) Attendance validation: inactive employees are not HR Review and are not imported.
old_validate = '''        emp = master_map.get(emp_id)\n        issue = ""\n        pending_master = bool(emp) and _clean_text(emp.get("department")).upper() == "HR REVIEW"\n        if not emp:\n            issue = "Employee ID not found in Employee Master"\n        elif pending_master:\n            issue = "Employee ID awaiting HR Master confirmation"\n        else:\n'''
new_validate = '''        emp = master_map.get(emp_id)\n        issue = ""\n        emp_status = _clean_text(emp.get("status")).upper() if emp else ""\n        inactive_master = bool(emp) and emp_status in {"INACTIVE", "LEFT", "RESIGNED", "TERMINATED"}\n        pending_master = (\n            bool(emp)\n            and not inactive_master\n            and _clean_text(emp.get("department")).upper() == "HR REVIEW"\n        )\n        if not emp:\n            issue = "Employee ID not found in Employee Master"\n        elif inactive_master:\n            rec["skip_import"] = True\n            rec["source_issue"] = "Inactive Employee in Master"\n            rec["review_required"] = False\n            rec["status"] = "Inactive"\n            rec["ot_hours"] = 0.0\n            continue\n        elif pending_master:\n            issue = "Employee ID awaiting HR Master confirmation"\n        else:\n'''
if old_validate not in text:
    raise SystemExit('attendance validation anchor not found')
text = text.replace(old_validate, new_validate, 1)

# 2) Remove inactive employees from the actual attendance payload.
old_bulk = '''    records = _validate_and_enrich_attendance_records(records)\n\n    # FK-HR-REVIEW-PLACEHOLDER-V1\n'''
new_bulk = '''    records = _validate_and_enrich_attendance_records(records)\n    # Employees already marked inactive/left/resigned/terminated in Employee Master\n    # must not be recreated, imported, or sent to HR Review from a biometric file.\n    records = [rec for rec in records if not bool(rec.get("skip_import", False))]\n    if not records:\n        return 0\n\n    # FK-HR-REVIEW-PLACEHOLDER-V1\n'''
if old_bulk not in text:
    raise SystemExit('bulk attendance anchor not found')
text = text.replace(old_bulk, new_bulk, 1)

# 3) Replace precheck so inactive IDs are shown separately and excluded from import/HR Review.
start_marker = 'def attendance_precheck(preview_df):\n'
end_marker = 'def import_salary_master_excel(uploaded_file, division):\n'
start = text.find(start_marker)
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('attendance_precheck block not found')

new_precheck = '''def attendance_precheck(preview_df):\n    """Preview attendance and route only genuine master exceptions to HR Review.\n\n    Employees already marked Inactive/Left/Resigned/Terminated are shown separately\n    and skipped from attendance import. They are never recreated as temporary HR\n    Review employees.\n    """\n    result = {\n        "rows_ready": 0, "employees": 0, "dates": 0, "duplicates": 0,\n        "unknown_ids": [], "division_mismatches": [], "inactive_ids": [],\n        "inactive_rows": 0, "hr_review": 0,\n        "master_exception_rows": 0, "status_summary": pd.DataFrame()\n    }\n    if preview_df is None or preview_df.empty:\n        return result\n\n    df = preview_df.copy()\n    result["employees"] = int(df["employee_id"].astype(str).nunique())\n    result["dates"] = int(df["work_date"].astype(str).nunique())\n    dup_mask = df.duplicated(subset=["work_date","shift","employee_id"], keep=False)\n    result["duplicates"] = int(dup_mask.sum())\n\n    master = read_df("SELECT employee_id,division,department,status FROM employees")\n    master_map = {}\n    if not master.empty:\n        master_map = {\n            str(r["employee_id"]).strip(): {\n                "division": _clean_text(r.get("division")),\n                "department": _clean_text(r.get("department")),\n                "status": _clean_text(r.get("status")),\n            }\n            for _, r in master.iterrows()\n        }\n\n    unknown, mismatch, inactive = [], [], []\n    exception_mask, inactive_mask = [], []\n    for _, r in df.iterrows():\n        eid = str(r.get("employee_id","")).strip()\n        div = _clean_text(r.get("division"))\n        has_issue = False\n        is_inactive = False\n        emp_master = master_map.get(eid)\n        master_status = _clean_text(emp_master.get("status")) .upper() if emp_master else ""\n\n        if emp_master and master_status in {"INACTIVE", "LEFT", "RESIGNED", "TERMINATED"}:\n            inactive.append(eid)\n            is_inactive = True\n        elif not emp_master or emp_master.get("department", "").upper() == "HR REVIEW":\n            unknown.append(eid)\n            has_issue = True\n        elif emp_master.get("division") and div and emp_master.get("division") != div:\n            mismatch.append(f"{eid}: master={emp_master.get('division')}, file={div}")\n            has_issue = True\n\n        exception_mask.append(has_issue)\n        inactive_mask.append(is_inactive)\n\n    result["unknown_ids"] = sorted(set(x for x in unknown if x))\n    result["division_mismatches"] = sorted(set(mismatch))\n    result["inactive_ids"] = sorted(set(x for x in inactive if x))\n\n    exception_series = pd.Series(exception_mask, index=df.index, dtype=bool)\n    inactive_series = pd.Series(inactive_mask, index=df.index, dtype=bool)\n    result["inactive_rows"] = int(inactive_series.sum())\n    result["master_exception_rows"] = int(exception_series.sum())\n\n    biometric_review = df["status"].astype(str).eq("HR Review") & ~inactive_series\n    result["hr_review"] = int((biometric_review | exception_series).sum())\n    result["rows_ready"] = max(0, len(df) - result["duplicates"] - result["inactive_rows"])\n\n    display_status = df.loc[~inactive_series, "status"].astype(str).copy()\n    display_exceptions = exception_series.loc[display_status.index]\n    display_status.loc[display_exceptions] = "HR Review"\n    result["status_summary"] = (\n        display_status.value_counts()\n        .rename_axis("Status")\n        .reset_index(name="Rows")\n        .sort_values("Status")\n    )\n    return result\n\n'''
text = text[:start] + new_precheck + text[end:]

# 4) Pre-import UI: show importable rows and a clear inactive warning.
old_metrics = '''                    p1.metric("Rows",f"{len(attendance_preview):,}")\n                    p2.metric("Employees",f"{precheck['employees']:,}")\n'''
new_metrics = '''                    p1.metric("Rows to Import",f"{precheck['rows_ready']:,}")\n                    p2.metric("Employees",f"{precheck['employees']:,}")\n'''
if old_metrics not in text:
    raise SystemExit('precheck metric anchor not found')
text = text.replace(old_metrics, new_metrics, 1)

unknown_anchor = '''                    if precheck["unknown_ids"]:\n                        st.warning(\n'''
inactive_block = '''                    if precheck.get("inactive_ids"):\n                        st.info(\n                            f"{len(precheck['inactive_ids'])} inactive employee ID(s) are present in the biometric file and "\n                            "will be skipped (not imported and not sent to HR Review): "\n                            + ", ".join(precheck["inactive_ids"][:20])\n                        )\n\n                    if precheck["unknown_ids"]:\n                        st.warning(\n'''
if unknown_anchor not in text:
    raise SystemExit('unknown IDs UI anchor not found')
text = text.replace(unknown_anchor, inactive_block, 1)

old_success = '''                        st.success(\n                            f"{len(attendance_preview):,} row(s) can be imported for **{actual}**. "\n                            f"{precheck['hr_review']:,} row(s) will stay in HR Review until HR confirms them."\n                        )\n'''
new_success = '''                        inactive_note = (\n                            f" {precheck.get('inactive_rows', 0):,} inactive row(s) will be skipped."\n                            if precheck.get('inactive_rows', 0) else ""\n                        )\n                        st.success(\n                            f"{precheck['rows_ready']:,} row(s) can be imported for **{actual}**. "\n                            f"{precheck['hr_review']:,} row(s) will stay in HR Review until HR confirms them."\n                            + inactive_note\n                        )\n'''
if old_success not in text:
    raise SystemExit('precheck success anchor not found')
text = text.replace(old_success, new_success, 1)

p.write_text(text, encoding='utf-8')
