from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

# 1) Allow attendance bulk upsert to atomically replace all existing rows
# for the dates/divisions present in the validated upload.
old = "def _bulk_upsert_attendance(records, source_type):"
new = "def _bulk_upsert_attendance(records, source_type, replace_scope=False):"
if old not in text:
    raise SystemExit('bulk upsert definition anchor not found')
text = text.replace(old, new, 1)

old = '''    conn = get_pg_conn()\n    try:\n        cur = conn.cursor()\n        payload = []'''
new = '''    conn = get_pg_conn()\n    try:\n        cur = conn.cursor()\n\n        # BTS FULL-REFRESH MODE\n        # When enabled, this validated upload becomes the attendance source of truth\n        # for every division/date present in the parsed records. Deletion and insert\n        # happen in the SAME transaction, so a failed insert rolls the delete back.\n        if replace_scope:\n            scope = {}\n            for rec in records:\n                div = _clean_text(rec.get("division"))\n                work_date = _clean_text(rec.get("work_date"))\n                if div and work_date:\n                    scope.setdefault(div, set()).add(work_date)\n            for div, dates in scope.items():\n                cur.execute(\n                    "DELETE FROM attendance WHERE division=%s AND work_date = ANY(%s)",\n                    (div, sorted(dates))\n                )\n\n        payload = []'''
if old not in text:
    raise SystemExit('bulk upsert transaction anchor not found')
text = text.replace(old, new, 1)

# 2) Thread replace_scope through both importers.
old = "def import_standard_attendance_excel(uploaded_file, division, target_date=None, dry_run=False, start_date=None, end_date=None):"
new = "def import_standard_attendance_excel(uploaded_file, division, target_date=None, dry_run=False, start_date=None, end_date=None, replace_scope=False):"
if old not in text:
    raise SystemExit('standard importer definition anchor not found')
text = text.replace(old, new, 1)

old = "    saved = _bulk_upsert_attendance(records, source_label)\n    return saved, pd.DataFrame(records)"
new = "    saved = _bulk_upsert_attendance(records, source_label, replace_scope=replace_scope)\n    return saved, pd.DataFrame(records)"
if text.count(old) < 1:
    raise SystemExit('standard importer save anchor not found')
text = text.replace(old, new, 1)

old = "def import_dhaulana_attendance_excel(uploaded_file, target_date=None, dry_run=False, start_date=None, end_date=None):"
new = "def import_dhaulana_attendance_excel(uploaded_file, target_date=None, dry_run=False, start_date=None, end_date=None, replace_scope=False):"
if old not in text:
    raise SystemExit('dhaulana importer definition anchor not found')
text = text.replace(old, new, 1)

# Replace the second remaining save call (Dhaulana).
old = "    saved = _bulk_upsert_attendance(records, source_label)\n    return saved, pd.DataFrame(records)"
new = "    saved = _bulk_upsert_attendance(records, source_label, replace_scope=replace_scope)\n    return saved, pd.DataFrame(records)"
if old not in text:
    raise SystemExit('dhaulana importer save anchor not found')
text = text.replace(old, new, 1)

# 3) Add an explicit fresh-refresh control to the Attendance upload page.
old = '''                        confirm_att = st.checkbox(\n                            "I confirm this attendance preview is correct and can be saved.",\n                            key="v69_attendance_confirm"\n                        )\n                        if st.button('''
new = '''                        replace_existing_scope = st.checkbox(\n                            "Replace existing attendance for the dates in this upload",\n                            value=True,\n                            key="v101_replace_existing_attendance_scope",\n                            help=(\n                                "Recommended for a fresh BTS 1st-to-current-date report. Existing attendance, including earlier HR corrections, "\n                                "for the dates/division in this upload will be rebuilt from this validated file. Employee Master is not changed."\n                            )\n                        )\n                        if replace_existing_scope:\n                            st.warning(\n                                "Fresh BTS refresh is ON: earlier attendance/HR corrections for the dates in this upload will be replaced. "\n                                "The Employee Master, inactive status and historical data outside these dates are not affected."\n                            )\n\n                        confirm_att = st.checkbox(\n                            "I confirm this attendance preview is correct and can be saved.",\n                            key="v69_attendance_confirm"\n                        )\n                        if st.button('''
if old not in text:
    raise SystemExit('attendance confirm UI anchor not found')
text = text.replace(old, new, 1)

# 4) Pass the chosen fresh-refresh mode only on the actual save calls.
old = '''                                    saved, preview = import_dhaulana_attendance_excel(\n                                        attendance_file,target_date=target_date,dry_run=False,\n                                        start_date=target_start_date,end_date=target_end_date\n                                    )'''
new = '''                                    saved, preview = import_dhaulana_attendance_excel(\n                                        attendance_file,target_date=target_date,dry_run=False,\n                                        start_date=target_start_date,end_date=target_end_date,\n                                        replace_scope=replace_existing_scope\n                                    )'''
if old not in text:
    raise SystemExit('dhaulana UI import call anchor not found')
text = text.replace(old, new, 1)

old = '''                                    saved, preview = import_standard_attendance_excel(\n                                        attendance_file,actual,target_date=target_date,dry_run=False,\n                                        start_date=target_start_date,end_date=target_end_date\n                                    )'''
new = '''                                    saved, preview = import_standard_attendance_excel(\n                                        attendance_file,actual,target_date=target_date,dry_run=False,\n                                        start_date=target_start_date,end_date=target_end_date,\n                                        replace_scope=replace_existing_scope\n                                    )'''
if old not in text:
    raise SystemExit('standard UI import call anchor not found')
text = text.replace(old, new, 1)

p.write_text(text, encoding='utf-8')
