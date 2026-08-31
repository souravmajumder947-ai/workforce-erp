from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

replacements = [
    (
'''            div_options = ["All Divisions"] + sorted(reviews["division"].dropna().astype(str).unique().tolist())
            review_div_filter = f1.selectbox("Division", div_options, key="v80_review_div_filter")
''',
'''            div_options = sorted(reviews["division"].dropna().astype(str).unique().tolist())
            review_div_filter = f1.multiselect(
                "Division", div_options, default=[], placeholder="All divisions",
                key="v81_review_div_filter"
            )
'''
    ),
    (
'''            emp_options = ["All Employees"] + sorted(employee_labels.keys(), key=lambda x: employee_labels[x].lower())
            review_emp_filter = f3.selectbox(
                "Employee", emp_options,
                format_func=lambda x: x if x == "All Employees" else employee_labels.get(x,x),
                key="v80_review_emp_filter"
            )

            issue_options = ["All Issues","Missing Punch","Unknown Employee","Division Mismatch","Other HR Review"]
            review_issue_filter = f4.selectbox("Issue Type", issue_options, key="v80_review_issue_filter")
''',
'''            emp_options = sorted(employee_labels.keys(), key=lambda x: employee_labels[x].lower())
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
'''
    ),
    (
'''            if review_div_filter != "All Divisions":
                filtered = filtered[filtered["division"].astype(str) == review_div_filter]
''',
'''            if review_div_filter:
                filtered = filtered[filtered["division"].astype(str).isin(review_div_filter)]
'''
    ),
    (
'''            if review_emp_filter != "All Employees":
                filtered = filtered[filtered["employee_id"].astype(str) == str(review_emp_filter)]
            if review_issue_filter != "All Issues":
                filtered = filtered[filtered["issue_type"] == review_issue_filter]
''',
'''            if review_emp_filter:
                filtered = filtered[filtered["employee_id"].astype(str).isin([str(x) for x in review_emp_filter])]
            if review_issue_filter:
                filtered = filtered[filtered["issue_type"].isin(review_issue_filter)]
'''
    ),
    (
'''                select_all_filtered = csel.checkbox(
                    f"Select all filtered ({len(filtered):,})", value=False, key="v80_select_all_filtered"
                )
''',
'''                select_all_filtered = csel.checkbox(
                    f"Select all filtered ({len(filtered):,})", value=False, key="v81_select_all_filtered",
                    help="Choose multiple filters above, then select every matching row in one click."
                )
'''
    ),
]

for old, new in replacements:
    if old not in text:
        # Idempotent success if the new block is already present.
        if new in text:
            continue
        raise SystemExit('Expected HR Review multi-select target not found; patch stopped safely.')
    text = text.replace(old, new, 1)

old_caption = (
    '                "Filter the exceptions, select only the rows HR has checked, then resolve those selected rows. "\n'
    '                "Employee Master is updated only for selected and resolved master exceptions."\n'
)
new_caption = (
    '                "Choose multiple divisions, employees or issue types, then use Select all filtered to pick every matching row at once. "\n'
    '                "Employee Master is updated only for selected and resolved master exceptions."\n'
)
if old_caption in text:
    text = text.replace(old_caption, new_caption, 1)

path.write_text(text, encoding='utf-8')
print('HR Review multi-select patch applied')
