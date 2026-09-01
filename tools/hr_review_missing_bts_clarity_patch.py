from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

old_caption = '''        st.caption(
            "This single view combines attendance exceptions, employee masters awaiting HR completion, "
            "and employees with no attendance record for the attendance-review date. "
            "Employees already marked Inactive / Left / Resigned / Terminated in Employee Master are excluded from HR Review."
        )'''
new_caption = '''        st.caption(
            "This single view combines attendance exceptions, employee masters awaiting HR completion, "
            "and active employees missing from the BTS attendance source for the attendance-review date. "
            "A missing BTS source record is not automatically an Absence. Employees already marked Inactive / Left / Resigned / Terminated are excluded."
        )'''
if old_caption not in text:
    raise SystemExit('HR action centre caption anchor not found')
text = text.replace(old_caption, new_caption, 1)

old_metric = '''        u3.metric(f"Missing Attendance · {missing_reference_date.strftime('%d %b %Y')}", f"{len(missing_attendance):,}")'''
new_metric = '''        u3.metric(f"Missing From BTS · {missing_reference_date.strftime('%d %b %Y')}", f"{len(missing_attendance):,}")'''
if old_metric not in text:
    raise SystemExit('Missing attendance metric anchor not found')
text = text.replace(old_metric, new_metric, 1)

old_expander = '''        with st.expander(f"Missing Attendance on {missing_reference_date.strftime('%d %b %Y')} ({len(missing_attendance):,})", expanded=False):
            if missing_attendance.empty:
                st.success("Every active employee has an attendance record for this date.")
            else:
                ma = missing_attendance.rename(columns={'''
new_expander = '''        with st.expander(f"Active Employees Missing From BTS on {missing_reference_date.strftime('%d %b %Y')} ({len(missing_attendance):,})", expanded=False):
            if missing_attendance.empty:
                st.success("Every active employee has an attendance record from the BTS source for this date.")
            else:
                missing_division_counts = (
                    missing_attendance.groupby("division", dropna=False).size().sort_values(ascending=False)
                )
                missing_division_text = " | ".join(
                    f"{(_clean_text(div) or 'Unassigned')}: {int(count):,}"
                    for div, count in missing_division_counts.items()
                )
                st.info(
                    f"BTS source check for **{missing_reference_date.strftime('%d %b %Y')}** — {missing_division_text}. "
                    "These employees are active in Employee Master but have no attendance row from the current BTS/imported source for this date. "
                    "Do not mark them Absent in bulk without HR verification."
                )
                ma = missing_attendance.rename(columns={'''
if old_expander not in text:
    raise SystemExit('Missing attendance expander anchor not found')
text = text.replace(old_expander, new_expander, 1)

old_select = '''                            "Select all missing'''
if old_select in text:
    text = text.replace('"Select all missing', '"Select all BTS-missing', 1)

p.write_text(text, encoding='utf-8')
