from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

anchor = '''        )\n        # Unified HR Action Centre: attendance exceptions + temporary employee masters + missing attendance.\n'''
insert = '''        )\n\n        # Keep Missing Attendance aligned with the attendance period being reviewed.\n        # If HR Review contains older attendance (for example August while today is September),\n        # use the latest review date instead of today's global working date.\n        if reviews.empty:\n            missing_reference_date = global_work_date\n        else:\n            _review_dates = pd.to_datetime(reviews["work_date"], errors="coerce").dropna()\n            missing_reference_date = (_review_dates.max().date() if not _review_dates.empty else global_work_date)\n\n        # Unified HR Action Centre: attendance exceptions + temporary employee masters + missing attendance.\n'''
if anchor not in text:
    raise SystemExit('review context anchor not found')
text = text.replace(anchor, insert, 1)

old = '''            (global_work_date.isoformat(),) + missing_params\n        )'''
new = '''            (missing_reference_date.isoformat(),) + missing_params\n        )'''
if old not in text:
    raise SystemExit('missing attendance query date anchor not found')
text = text.replace(old, new, 1)

old = '''            "and employees with no attendance record for the selected working date. "'''
new = '''            "and employees with no attendance record for the attendance-review date. "'''
if old not in text:
    raise SystemExit('HR action centre caption anchor not found')
text = text.replace(old, new, 1)

old = '''        u3.metric("Missing Attendance", f"{len(missing_attendance):,}")'''
new = '''        u3.metric(f"Missing Attendance · {missing_reference_date.strftime('%d %b %Y')}", f"{len(missing_attendance):,}")'''
if old not in text:
    raise SystemExit('missing attendance metric anchor not found')
text = text.replace(old, new, 1)

old = '''        with st.expander(f"Missing Attendance on {global_work_date.strftime('%d %b %Y')} ({len(missing_attendance):,})", expanded=False):'''
new = '''        with st.expander(f"Missing Attendance on {missing_reference_date.strftime('%d %b %Y')} ({len(missing_attendance):,})", expanded=False):'''
if old not in text:
    raise SystemExit('missing attendance expander anchor not found')
text = text.replace(old, new, 1)

p.write_text(text, encoding='utf-8')
