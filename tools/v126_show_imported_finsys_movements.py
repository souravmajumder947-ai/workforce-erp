from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
MARK="# V12.6 SHOW IMPORTED FINSYS MOVEMENTS IN REPORTS"
if MARK in s:
    print("V12.6 already applied")
    raise SystemExit(0)

# Daily report date should follow the global Working Date whenever Working Date changes.
old='''        _v123_day=st.date_input(
            "Report Date",value=global_work_date,format="DD/MM/YYYY",key="v123_daily_report_date"
        )
'''
new='''        # V12.6 SHOW IMPORTED FINSYS MOVEMENTS IN REPORTS
        _v126_working_date_key=global_work_date.isoformat()
        if st.session_state.get("v126_last_working_date") != _v126_working_date_key:
            st.session_state["v123_daily_report_date"]=global_work_date
            st.session_state["v126_last_working_date"]=_v126_working_date_key
        _v123_day=st.date_input(
            "Report Date",value=global_work_date,format="DD/MM/YYYY",key="v123_daily_report_date"
        )
'''
if old not in s:
    raise RuntimeError("Daily report date anchor not found")
s=s.replace(old,new,1)

# Detailed Finsys Issue/Return transactions are valid report data even if no production/consumption row exists.
old='''        if _v123_prod.empty and _v123_reels.empty:
            st.info(f"No Corrugation data is saved for {_v123_day.strftime('%d/%m/%Y')}.")
        else:
'''
new='''        if _v123_prod.empty and _v123_reels.empty and _v125_move_day.empty:
            st.info(f"No Corrugation data is saved for {_v123_day.strftime('%d/%m/%Y')}.")
        else:
'''
if old not in s:
    raise RuntimeError("Daily no-data condition anchor not found")
s=s.replace(old,new,1)

# Monthly detailed movement rows should make the report render even before consumption/production is entered.
old='''        if _v123_prod_month.empty and _v123_reel_rows.empty:
            st.info(f"No Corrugation data is saved for {_v123_month.strftime('%B %Y')}.")
        else:
'''
new='''        if _v123_prod_month.empty and _v123_reel_rows.empty and _v125_move_month.empty:
            st.info(f"No Corrugation data is saved for {_v123_month.strftime('%B %Y')}.")
        else:
'''
if old not in s:
    raise RuntimeError("Monthly no-data condition anchor not found")
s=s.replace(old,new,1)

# Make pending consumption explicit when only Issue/Return has been imported.
old='''            _v123_expected=_v123_opening+_v123_net-_v123_closing
            _v123_flow_variance=_v123_expected-_v123_consumption
'''
new='''            _v123_expected=_v123_opening+_v123_net-_v123_closing
            _v123_flow_variance=(
                _v123_expected-_v123_consumption
                if _v123_consumption>0 or _v123_opening>0 or _v123_closing>0
                else 0.0
            )
'''
if old not in s:
    raise RuntimeError("Daily flow variance anchor not found")
s=s.replace(old,new,1)

# Avoid showing misleading monthly flow variance when only Issue/Return transactions are available.
old='''            _v123_daily["Flow Variance Ton"]=(
                _v123_daily["Expected Consumption Ton"]-_v123_daily["Consumption Ton"]
            )
'''
new='''            _v123_daily["Flow Variance Ton"]=_v123_daily.apply(
                lambda r:(
                    float(r["Expected Consumption Ton"])-float(r["Consumption Ton"])
                    if (
                        float(r["Consumption Ton"])>0
                        or float(r["Opening WIP Ton"])>0
                        or float(r["Closing WIP Ton"])>0
                    ) else 0.0
                ),
                axis=1
            )
'''
if old not in s:
    raise RuntimeError("Monthly flow variance anchor not found")
s=s.replace(old,new,1)

p.write_text(s,encoding="utf-8")
print("Applied V12.6 imported Finsys movement report visibility fix")
