from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
MARK="# V12.7 CORRECT PRODUCTION DATE MONTH CONTEXT"
if MARK in s:
    print("V12.7 already applied")
    raise SystemExit(0)

# Daily report must use only the sidebar Working Date.
old='''        # V12.6 SHOW IMPORTED FINSYS MOVEMENTS IN REPORTS
        _v126_working_date_key=global_work_date.isoformat()
        if st.session_state.get("v126_last_working_date") != _v126_working_date_key:
            st.session_state["v123_daily_report_date"]=global_work_date
            st.session_state["v126_last_working_date"]=_v126_working_date_key
        _v123_day=st.date_input(
            "Report Date",value=global_work_date,format="DD/MM/YYYY",key="v123_daily_report_date"
        )
'''
new='''        # V12.7 CORRECT PRODUCTION DATE MONTH CONTEXT
        # Daily production reporting has one date source only: sidebar Working Date.
        _v123_day=global_work_date
        st.info(
            f"📅 Daily Report Date: **{_v123_day.strftime('%d/%m/%Y')}** "
            "· controlled by the sidebar Working Date"
        )
'''
if old not in s:
    raise RuntimeError("Daily report date block not found")
s=s.replace(old,new,1)

# Monthly report must default from Working Date month, never from Payroll Month.
old='''        _v123_month=st.selectbox(
            "Production Month",_month_opts,
            index=_month_opts.index(global_payroll_month),
            format_func=lambda d:d.strftime("%b %Y"),
            key="v123_monthly_report_month"
        )
'''
new='''        _v127_working_month=date(global_work_date.year,global_work_date.month,1)
        _v127_month_default=(
            _v127_working_month
            if _v127_working_month in _month_opts
            else _month_opts[-1]
        )
        _v123_month=st.selectbox(
            "Production Month",
            _month_opts,
            index=_month_opts.index(_v127_month_default),
            format_func=lambda d:d.strftime("%b %Y"),
            key="v127_monthly_report_month",
            help="This is the Production Month. It is independent from Payroll Month."
        )
        st.caption(
            f"Monthly production period: {_v123_month.strftime('%B %Y')} "
            "· Payroll Month does not control this report."
        )
'''
if old not in s:
    raise RuntimeError("Monthly production month selector not found")
s=s.replace(old,new,1)

# Clarify report captions so date vs month cannot be confused.
s=s.replace(
    '"MD material flow: Opening WIP → Reel Issue → Reel Return → Net Issue → Consumption → Closing WIP → Production → Ton/Person."',
    '"Daily report only. Date format is DD/MM/YYYY and follows the sidebar Working Date. "'
    '"Material flow: Opening WIP → Reel Issue → Reel Return → Net Issue → Consumption → Closing WIP → Production → Ton/Person."',
    1
)
s=s.replace(
    '"Complete monthly material flow and productivity report from this app: "'
    '\n            "Issue, Return, Consumption, WIP, Production, Waste and Ton/Person."',
    '"Monthly report only. Select the Production Month in MMM YYYY format. "'
    '\n            "Issue, Return, Consumption, WIP, Production, Waste and Ton/Person are summarized for that production month."',
    1
)

p.write_text(s,encoding="utf-8")
print("Applied V12.7 production date/month context correction")
