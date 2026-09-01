from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

old = '''               FROM attendance a LEFT JOIN employees e ON e.employee_id=a.employee_id\n               WHERE (a.status='HR Review' OR a.review_required=TRUE) """ + clause + """\n               ORDER BY a.work_date DESC,COALESCE(e.employee_name,a.source_employee_name,a.employee_id)""",\n'''
new = '''               FROM attendance a LEFT JOIN employees e ON e.employee_id=a.employee_id\n               WHERE (a.status='HR Review' OR a.review_required=TRUE)\n                 AND COALESCE(UPPER(TRIM(e.status)),'ACTIVE') NOT IN ('INACTIVE','LEFT','RESIGNED','TERMINATED') """ + clause + """\n               ORDER BY a.work_date DESC,COALESCE(e.employee_name,a.source_employee_name,a.employee_id)""",\n'''

if old not in text:
    raise SystemExit('HR Review query anchor not found')
text = text.replace(old, new, 1)

caption_old = '''        st.caption(\n            "This single view combines attendance exceptions, employee masters awaiting HR completion, "\n            "and employees with no attendance record for the selected working date."\n        )\n'''
caption_new = '''        st.caption(\n            "This single view combines attendance exceptions, employee masters awaiting HR completion, "\n            "and employees with no attendance record for the selected working date. "\n            "Employees already marked Inactive / Left / Resigned / Terminated in Employee Master are excluded from HR Review."\n        )\n'''
if caption_old in text:
    text = text.replace(caption_old, caption_new, 1)

p.write_text(text, encoding='utf-8')
