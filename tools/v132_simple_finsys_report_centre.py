from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
MARK="# V13.2 SIMPLE FINSYS REPORT CENTRE"
if MARK in s:
    print("V13.2 already applied")
    raise SystemExit(0)

old_tabs='''    tab_prod,tab_daily_report,tab_monthly,tab_reel_reports,tab_mp=st.tabs([
        "Production Entry","Daily Production Report","Monthly MD Report",
        "Reel Reports","Manpower Allocation"
    ])
'''
new_tabs='''    # V13.2 SIMPLE FINSYS REPORT CENTRE
    tab_prod,tab_report_centre,tab_mp=st.tabs([
        "Production Entry","Report Centre","Manpower Allocation"
    ])
'''
if old_tabs not in s:
    raise RuntimeError("Operations tab definition not found")
s=s.replace(old_tabs,new_tabs,1)

s=s.replace(
    '"Production is day-wise by machine. Corrugation tracks reel issue, return, WIP and consumption; downstream machines use daily material-conversion flow.",',
    '"Production is day-wise by machine. Corrugation tracks reel issue, return, consumption, production and manpower productivity.",',
    1
)

start=s.find('''    with tab_daily_report:
''')
end=s.find('''    with tab_mp:
        c1,c2,c3=st.columns(3)
''',start)
if start==-1 or end==-1:
    raise RuntimeError("Existing report blocks not found")

block=r'''    with tab_report_centre:
        st.markdown("""
        <style>
        .v132-report-head{
          border:1px solid rgba(125,211,252,.22);
          border-radius:14px;
          padding:16px 18px;
          margin-bottom:14px;
          background:linear-gradient(135deg,rgba(14,28,45,.95),rgba(10,20,34,.95));
        }
        .v132-report-head h3{margin:0 0 4px 0!important;font-size:22px!important;}
        .v132-report-head p{margin:0;color:#a9b8ca;font-size:13px;}
        .v132-step{
          font-size:12px;color:#8fa2b7;margin:4px 0 10px 0;
          letter-spacing:.02em;
        }
        </style>
        <div class="v132-report-head">
          <h3>Report Centre</h3>
          <p>Finsys-style workflow: choose report → select period → show report → search / sort → export.</p>
        </div>
        """,unsafe_allow_html=True)

        _v132_report=st.radio(
            "Choose Report",
            [
                "Reel Wise Issue",
                "Reel Wise Return",
                "Daily Corrugation",
                "Monthly Corrugation"
            ],
            horizontal=True,
            key="v132_report_choice"
        )

        # ---------------- REEL WISE ISSUE / RETURN ----------------
        if _v132_report in ["Reel Wise Issue","Reel Wise Return"]:
            st.markdown("#### Select Period")
            st.caption("Date format: DD/MM/YYYY")

            _v132_quick=st.selectbox(
                "Quick Period",
                [
                    "M.T.D (Month To Date)",
                    "Y.T.D (Year To Date)",
                    "Previous Month",
                    "Today",
                    "Yesterday",
                    "First Qtr",
                    "Second Qtr",
                    "Third Qtr",
                    "Fourth Qtr",
                    "Full Year",
                    "Custom"
                ],
                key="v132_reel_quick_period"
            )

            def _v132_month_bounds(_d):
                _f=date(_d.year,_d.month,1)
                if _d.month==12:
                    _n=date(_d.year+1,1,1)
                else:
                    _n=date(_d.year,_d.month+1,1)
                return _f,_n-timedelta(days=1)

            def _v132_prev_month(_d):
                return date(_d.year-1,12,1) if _d.month==1 else date(_d.year,_d.month-1,1)

            def _v132_period(_name):
                _today=date.today()
                if _name=="M.T.D (Month To Date)":
                    return date(_today.year,_today.month,1),_today
                if _name=="Y.T.D (Year To Date)":
                    return date(_today.year,1,1),_today
                if _name=="Previous Month":
                    return _v132_month_bounds(_v132_prev_month(_today))
                if _name=="Today":
                    return _today,_today
                if _name=="Yesterday":
                    _y=_today-timedelta(days=1)
                    return _y,_y
                if _name=="First Qtr":
                    return date(_today.year,1,1),date(_today.year,3,31)
                if _name=="Second Qtr":
                    return date(_today.year,4,1),date(_today.year,6,30)
                if _name=="Third Qtr":
                    return date(_today.year,7,1),date(_today.year,9,30)
                if _name=="Fourth Qtr":
                    return date(_today.year,10,1),date(_today.year,12,31)
                if _name=="Full Year":
                    return date(_today.year,1,1),date(_today.year,12,31)
                return _v132_month_bounds(_today)

            _v132_pf,_v132_pt=_v132_period(_v132_quick)
            if st.session_state.get("v132_last_quick") != _v132_quick:
                if _v132_quick!="Custom":
                    st.session_state["v132_from"]=_v132_pf
                    st.session_state["v132_to"]=_v132_pt
                else:
                    st.session_state.setdefault("v132_from",_v132_pf)
                    st.session_state.setdefault("v132_to",_v132_pt)
                st.session_state["v132_last_quick"]=_v132_quick

            d1,d2=st.columns(2)
            _v132_from=d1.date_input(
                "Date From",
                value=st.session_state.get("v132_from",_v132_pf),
                format="DD/MM/YYYY",
                key="v132_from"
            )
            _v132_to=d2.date_input(
                "Date To",
                value=st.session_state.get("v132_to",_v132_pt),
                format="DD/MM/YYYY",
                key="v132_to"
            )

            if _v132_from>_v132_to:
                st.error("Date From cannot be after Date To.")
            else:
                if st.button(
                    "Show Report",
                    type="primary",
                    use_container_width=True,
                    key="v132_show_reel_report"
                ):
                    st.session_state["v132_reel_ready"]=True
                    st.session_state["v132_reel_type"]=_v132_report
                    st.session_state["v132_reel_from"]=_v132_from
                    st.session_state["v132_reel_to"]=_v132_to

                if st.session_state.get("v132_reel_ready"):
                    _rr_type=st.session_state.get("v132_reel_type",_v132_report)
                    _rr_from=st.session_state.get("v132_reel_from",_v132_from)
                    _rr_to=st.session_state.get("v132_reel_to",_v132_to)
                    _movement="ISSUE" if _rr_type=="Reel Wise Issue" else "RETURN"
                    _qty_col="QTY_OUT" if _movement=="ISSUE" else "QTY_RETURN"

                    _raw=read_df(
                        """SELECT movement_type,work_date,vch_no,supplier,acode,item,
                                  quantity_kg,quantity_ton,reel_no,co_reel,reel_mill,
                                  irate,movement_value,job_no,job_date,reel_size,gsm,
                                  icode,cpartno
                           FROM production_reel_transactions
                           WHERE movement_type=?
                             AND work_date BETWEEN ? AND ?
                           ORDER BY work_date,vch_no,reel_no""",
                        (_movement,_rr_from.isoformat(),_rr_to.isoformat())
                    )

                    st.markdown("---")
                    st.markdown(
                        f"### {_rr_type} {_rr_from.strftime('%d/%m/%Y')} to {_rr_to.strftime('%d/%m/%Y')}"
                    )

                    _search=st.text_input(
                        "Search",
                        placeholder="Enter search string & press Enter",
                        key="v132_reel_search"
                    )

                    if _raw.empty:
                        st.info("No records found for the selected period.")
                    else:
                        _df=_raw.copy()
                        if str(_search or "").strip():
                            _needle=str(_search).strip().lower()
                            _mask=_df.astype(str).apply(
                                lambda col:col.str.lower().str.contains(_needle,na=False)
                            ).any(axis=1)
                            _df=_df[_mask].copy()

                        _df=_df.rename(columns={
                            "work_date":"VCH_DT","vch_no":"VCH_NO",
                            "supplier":"SUPPLIER","item":"ITEM",
                            "quantity_kg":_qty_col,"reel_no":"REEL_NO",
                            "co_reel":"CO_REEL","reel_mill":"REEL_MILL",
                            "movement_type":"TYPE","irate":"IRATE",
                            "job_no":"JOB_NO","job_date":"JOB_DT",
                            "reel_size":"REEL_SIZE","gsm":"GSM",
                            "icode":"ICODE","cpartno":"CPARTNO",
                            "acode":"ACODE","quantity_ton":"QTY_TON",
                            "movement_value":"VALUE"
                        })
                        _df["VCH_DT"]=pd.to_datetime(
                            _df["VCH_DT"],errors="coerce"
                        ).dt.strftime("%d/%m/%Y")
                        _df["JOB_DT"]=pd.to_datetime(
                            _df["JOB_DT"],errors="coerce"
                        ).dt.strftime("%d/%m/%Y")

                        _all_cols=[
                            "VCH_DT","VCH_NO","SUPPLIER","ITEM",_qty_col,
                            "REEL_NO","CO_REEL","REEL_MILL","TYPE","IRATE",
                            "JOB_NO","JOB_DT","REEL_SIZE","GSM","ICODE",
                            "CPARTNO","ACODE","QTY_TON","VALUE"
                        ]
                        _all_cols=[c for c in _all_cols if c in _df.columns]
                        _default_cols=[
                            "VCH_DT","VCH_NO","SUPPLIER","ITEM",_qty_col,
                            "REEL_NO","CO_REEL","REEL_MILL","TYPE","IRATE",
                            "JOB_NO","JOB_DT","REEL_SIZE","GSM","ICODE"
                        ]
                        _default_cols=[c for c in _default_cols if c in _df.columns]

                        with st.expander("Print / Export Selected Columns"):
                            _show_cols=st.multiselect(
                                "Columns",
                                _all_cols,
                                default=_default_cols,
                                key="v132_reel_columns"
                            )
                            if not _show_cols:
                                _show_cols=_default_cols

                        _records=len(_df)
                        _kg=float(pd.to_numeric(_df[_qty_col],errors="coerce").fillna(0).sum())
                        _ton=float(pd.to_numeric(_df["QTY_TON"],errors="coerce").fillna(0).sum())
                        _value=float(pd.to_numeric(_df["VALUE"],errors="coerce").fillna(0).sum())

                        m1,m2,m3,m4=st.columns(4)
                        m1.metric("Records",f"{_records:,}")
                        m2.metric("Total Qty",f"{_kg:,.0f} Kg")
                        m3.metric("Total Ton",f"{_ton:,.2f} T")
                        m4.metric("Total Value",v5_money(_value))

                        st.caption(
                            "Click a column header to sort. Horizontal scroll shows the complete ERP sheet."
                        )
                        _sheet=_df[_show_cols].copy()
                        st.dataframe(
                            _sheet,
                            hide_index=True,
                            use_container_width=True,
                            height=620,
                            column_config={
                                _qty_col:st.column_config.NumberColumn(_qty_col,format="%.0f"),
                                "QTY_TON":st.column_config.NumberColumn("QTY_TON",format="%.2f T"),
                                "IRATE":st.column_config.NumberColumn("IRATE",format="₹%.2f"),
                                "VALUE":st.column_config.NumberColumn("VALUE",format="₹%.2f"),
                                "REEL_SIZE":st.column_config.NumberColumn("REEL_SIZE",format="%.0f"),
                                "GSM":st.column_config.NumberColumn("GSM",format="%.0f"),
                            }
                        )

                        e1,e2=st.columns(2)
                        _xlsx=make_excel_report(
                            _sheet,_rr_type,
                            f"{_rr_from.strftime('%d/%m/%Y')} to {_rr_to.strftime('%d/%m/%Y')}"
                        )
                        e1.download_button(
                            "Download Excel",
                            data=_xlsx,
                            file_name=f"{_rr_type.replace(' ','_')}_{_rr_from:%Y%m%d}_to_{_rr_to:%Y%m%d}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary",
                            use_container_width=True,
                            key="v132_reel_excel"
                        )
                        e2.download_button(
                            "Download CSV",
                            data=_sheet.to_csv(index=False).encode("utf-8-sig"),
                            file_name=f"{_rr_type.replace(' ','_')}_{_rr_from:%Y%m%d}_to_{_rr_to:%Y%m%d}.csv",
                            mime="text/csv",
                            use_container_width=True,
                            key="v132_reel_csv"
                        )

        # ---------------- DAILY CORRUGATION ----------------
        elif _v132_report=="Daily Corrugation":
            st.markdown("#### Select Date")
            _d=st.date_input(
                "Report Date",
                value=date.today(),
                format="DD/MM/YYYY",
                key="v132_daily_date"
            )
            if st.button(
                "Show Report",
                type="primary",
                use_container_width=True,
                key="v132_show_daily"
            ):
                st.session_state["v132_daily_ready"]=True
                st.session_state["v132_daily_selected"]=_d

            if st.session_state.get("v132_daily_ready"):
                _rd=st.session_state.get("v132_daily_selected",_d)
                _mov=read_df(
                    """SELECT movement_type,
                              SUM(quantity_ton) AS qty_ton,
                              SUM(movement_value) AS movement_value
                       FROM production_reel_transactions
                       WHERE work_date=?
                       GROUP BY movement_type""",
                    (_rd.isoformat(),)
                )
                _prod=read_df(
                    """SELECT production_ton,target_ton,waste_ton,breakdown_hours,
                              paper_cost,material_processed_ton,good_output_ton
                       FROM production
                       WHERE work_date=? AND shift='DAY' AND machine='Corrugation'
                       LIMIT 1""",
                    (_rd.isoformat(),)
                )
                _mp=read_df(
                    """SELECT shift,COUNT(DISTINCT employee_id) AS people
                       FROM manpower_allocation
                       WHERE work_date=? AND machine='Corrugation'
                       GROUP BY shift""",
                    (_rd.isoformat(),)
                )

                _issue=_return=_issue_value=_return_value=0.0
                for _,_r in _mov.iterrows():
                    if str(_r["movement_type"])=="ISSUE":
                        _issue=float(_r["qty_ton"] or 0); _issue_value=float(_r["movement_value"] or 0)
                    elif str(_r["movement_type"])=="RETURN":
                        _return=float(_r["qty_ton"] or 0); _return_value=float(_r["movement_value"] or 0)
                _net=_issue-_return

                _pr=_prod.iloc[0].to_dict() if not _prod.empty else {}
                _cons=float(_pr.get("material_processed_ton") or 0)
                _cons_value=float(_pr.get("paper_cost") or 0)
                _output=float(_pr.get("good_output_ton") or _pr.get("production_ton") or 0)
                _target=float(_pr.get("target_ton") or 0)
                _waste=float(_pr.get("waste_ton") or 0)
                _break=float(_pr.get("breakdown_hours") or 0)
                _a=_b=0
                for _,_r in _mp.iterrows():
                    if str(_r["shift"])=="A": _a=int(_r["people"] or 0)
                    elif str(_r["shift"])=="B": _b=int(_r["people"] or 0)
                _people=_a+_b

                st.markdown("---")
                st.markdown(f"### Daily Corrugation Report · {_rd.strftime('%d/%m/%Y')}")

                r1,r2,r3=st.columns(3)
                r1.metric("Reel Issue",f"{_issue:,.2f} T")
                r2.metric("Reel Return",f"{_return:,.2f} T")
                r3.metric("Net Issue",f"{_net:,.2f} T")

                if _cons>0:
                    r1,r2,r3=st.columns(3)
                    r1.metric("Consumption",f"{_cons:,.2f} T")
                    r2.metric("Consumption Value",v5_money(_cons_value))
                    r3.metric(
                        "Avg Paper Rate",
                        f"₹{(_cons_value/(_cons*1000.0)):,.2f}/Kg" if _cons>0 else "—"
                    )

                if _output>0 or _target>0:
                    _ach=(_output/_target*100.0) if _target>0 else 0.0
                    _yield=(_output/_cons*100.0) if _cons>0 else 0.0
                    _waste_pct=(_waste/_cons*100.0) if _cons>0 else 0.0
                    r1,r2,r3,r4=st.columns(4)
                    r1.metric("Production",f"{_output:,.2f} T")
                    r2.metric("Target",f"{_target:,.2f} T")
                    r3.metric("Achievement",f"{_ach:,.2f}%")
                    r4.metric("Breakdown",f"{_break:,.2f} Hrs")
                    r1,r2,r3=st.columns(3)
                    r1.metric("Waste",f"{_waste:,.2f} T")
                    r2.metric("Waste %",f"{_waste_pct:,.2f}%" if _cons>0 else "PENDING")
                    r3.metric("Yield",f"{_yield:,.2f}%" if _cons>0 else "PENDING")

                if _people>0:
                    r1,r2,r3,r4=st.columns(4)
                    r1.metric("Shift A",f"{_a}")
                    r2.metric("Shift B",f"{_b}")
                    r3.metric("Total Person-Shifts",f"{_people}")
                    r4.metric(
                        "Ton / Person",
                        f"{(_output/_people):,.2f} T" if _output>0 else "0.00 T"
                    )

                if _issue<=0 and _return<=0 and _cons<=0 and _output<=0:
                    st.info("No Corrugation data is available for this date.")

        # ---------------- MONTHLY CORRUGATION ----------------
        else:
            st.markdown("#### Select Production Month")
            _default_month=date(date.today().year,date.today().month,1)
            _month=st.selectbox(
                "Production Month",
                _month_opts,
                index=_month_opts.index(_default_month) if _default_month in _month_opts else len(_month_opts)-1,
                format_func=lambda d:d.strftime("%b %Y"),
                key="v132_month"
            )
            if st.button(
                "Show Report",
                type="primary",
                use_container_width=True,
                key="v132_show_monthly"
            ):
                st.session_state["v132_month_ready"]=True
                st.session_state["v132_month_selected"]=_month

            if st.session_state.get("v132_month_ready"):
                _rm=st.session_state.get("v132_month_selected",_month)
                _f,_t=_month_range(_rm)
                _mov=read_df(
                    """SELECT work_date,
                              SUM(CASE WHEN movement_type='ISSUE' THEN quantity_ton ELSE 0 END) AS issue_ton,
                              SUM(CASE WHEN movement_type='RETURN' THEN quantity_ton ELSE 0 END) AS return_ton,
                              SUM(CASE WHEN movement_type='ISSUE' THEN movement_value ELSE 0 END) AS issue_value,
                              SUM(CASE WHEN movement_type='RETURN' THEN movement_value ELSE 0 END) AS return_value
                       FROM production_reel_transactions
                       WHERE work_date BETWEEN ? AND ?
                       GROUP BY work_date ORDER BY work_date""",
                    (_f.isoformat(),_t.isoformat())
                )
                _prod=read_df(
                    """SELECT work_date,production_ton,target_ton,waste_ton,breakdown_hours,
                              paper_cost,material_processed_ton,good_output_ton
                       FROM production
                       WHERE shift='DAY' AND machine='Corrugation'
                         AND work_date BETWEEN ? AND ?
                       ORDER BY work_date""",
                    (_f.isoformat(),_t.isoformat())
                )
                _mp=read_df(
                    """SELECT work_date,shift,COUNT(DISTINCT employee_id) AS people
                       FROM manpower_allocation
                       WHERE machine='Corrugation'
                         AND work_date BETWEEN ? AND ?
                       GROUP BY work_date,shift""",
                    (_f.isoformat(),_t.isoformat())
                )

                _dates=set()
                if not _mov.empty:
                    _mov["work_date"]=_mov["work_date"].astype(str); _dates.update(_mov["work_date"].tolist())
                if not _prod.empty:
                    _prod["work_date"]=_prod["work_date"].astype(str); _dates.update(_prod["work_date"].tolist())
                if not _mp.empty:
                    _mp["work_date"]=_mp["work_date"].astype(str); _dates.update(_mp["work_date"].tolist())

                st.markdown("---")
                st.markdown(f"### Monthly Corrugation Report · {_rm.strftime('%B %Y')}")

                if not _dates:
                    st.info("No Corrugation data is available for this month.")
                else:
                    _d=pd.DataFrame({"work_date":sorted(_dates)})
                    if not _mov.empty: _d=_d.merge(_mov,on="work_date",how="left")
                    if not _prod.empty: _d=_d.merge(_prod,on="work_date",how="left")
                    for _c in [
                        "issue_ton","return_ton","issue_value","return_value",
                        "production_ton","target_ton","waste_ton","breakdown_hours",
                        "paper_cost","material_processed_ton","good_output_ton"
                    ]:
                        if _c not in _d.columns: _d[_c]=0.0
                        _d[_c]=pd.to_numeric(_d[_c],errors="coerce").fillna(0.0)

                    _d["Date"]=pd.to_datetime(_d["work_date"],errors="coerce").dt.date
                    _d["Reel Issue Ton"]=_d["issue_ton"]
                    _d["Reel Return Ton"]=_d["return_ton"]
                    _d["Net Issue Ton"]=_d["Reel Issue Ton"]-_d["Reel Return Ton"]
                    _d["Consumption Ton"]=_d["material_processed_ton"]
                    _d["Production Ton"]=_d.apply(
                        lambda r:float(r["good_output_ton"]) if float(r["good_output_ton"])>0 else float(r["production_ton"]),
                        axis=1
                    )
                    _d["Target Ton"]=_d["target_ton"]
                    _d["Waste Ton"]=_d["waste_ton"]
                    _d["Achievement %"]=_d.apply(
                        lambda r:(float(r["Production Ton"])/float(r["Target Ton"])*100.0) if float(r["Target Ton"])>0 else 0.0,
                        axis=1
                    )
                    _d["Total Manpower"]=0
                    if not _mp.empty:
                        for _day,_g in _mp.groupby("work_date"):
                            _d.loc[_d["work_date"]==str(_day),"Total Manpower"]=int(
                                pd.to_numeric(_g["people"],errors="coerce").fillna(0).sum()
                            )
                    _d["Ton / Person"]=_d.apply(
                        lambda r:(float(r["Production Ton"])/float(r["Total Manpower"])) if float(r["Total Manpower"])>0 else 0.0,
                        axis=1
                    )

                    _issue=float(_d["Reel Issue Ton"].sum())
                    _return=float(_d["Reel Return Ton"].sum())
                    _cons=float(_d["Consumption Ton"].sum())
                    _output=float(_d["Production Ton"].sum())
                    _target=float(_d["Target Ton"].sum())
                    _waste=float(_d["Waste Ton"].sum())
                    _people=int(_d["Total Manpower"].sum())

                    r1,r2,r3=st.columns(3)
                    r1.metric("Reel Issue",f"{_issue:,.2f} T")
                    r2.metric("Reel Return",f"{_return:,.2f} T")
                    r3.metric("Net Issue",f"{(_issue-_return):,.2f} T")

                    if _cons>0:
                        r1,r2=st.columns(2)
                        r1.metric("Consumption",f"{_cons:,.2f} T")
                        r2.metric(
                            "Yield",
                            f"{(_output/_cons*100.0):,.2f}%" if _output>0 else "0.00%"
                        )

                    if _output>0 or _target>0:
                        r1,r2,r3,r4=st.columns(4)
                        r1.metric("Production",f"{_output:,.2f} T")
                        r2.metric("Target",f"{_target:,.2f} T")
                        r3.metric(
                            "Achievement",
                            f"{(_output/_target*100.0):,.2f}%" if _target>0 else "0.00%"
                        )
                        r4.metric("Waste",f"{_waste:,.2f} T")

                    if _people>0:
                        r1,r2=st.columns(2)
                        r1.metric("Person-Shifts",f"{_people:,}")
                        r2.metric(
                            "Corrugation Ton / Person",
                            f"{(_output/_people):,.2f} T" if _output>0 else "0.00 T"
                        )

                    _cols=[
                        "Date","Reel Issue Ton","Reel Return Ton","Net Issue Ton"
                    ]
                    if _cons>0: _cols+=["Consumption Ton"]
                    if _output>0 or _target>0:
                        _cols+=["Production Ton","Target Ton","Achievement %","Waste Ton"]
                    if _people>0:
                        _cols+=["Total Manpower","Ton / Person"]

                    _sheet=_d[_cols].copy()
                    st.markdown("#### Date-wise Summary")
                    st.dataframe(
                        _sheet,
                        hide_index=True,
                        use_container_width=True,
                        height=500,
                        column_config={
                            "Reel Issue Ton":st.column_config.NumberColumn(format="%.2f T"),
                            "Reel Return Ton":st.column_config.NumberColumn(format="%.2f T"),
                            "Net Issue Ton":st.column_config.NumberColumn(format="%.2f T"),
                            "Consumption Ton":st.column_config.NumberColumn(format="%.2f T"),
                            "Production Ton":st.column_config.NumberColumn(format="%.2f T"),
                            "Target Ton":st.column_config.NumberColumn(format="%.2f T"),
                            "Achievement %":st.column_config.NumberColumn(format="%.2f%%"),
                            "Waste Ton":st.column_config.NumberColumn(format="%.2f T"),
                            "Ton / Person":st.column_config.NumberColumn(format="%.2f T"),
                        }
                    )
                    _xlsx=make_excel_report(
                        _sheet,
                        "Monthly Corrugation Report",
                        _rm.strftime("%B %Y")
                    )
                    st.download_button(
                        "Download Monthly Report",
                        data=_xlsx,
                        file_name=f"Corrugation_Monthly_{_rm:%Y_%m}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True,
                        key="v132_month_excel"
                    )

'''
s=s[:start]+block+s[end:]
p.write_text(s,encoding="utf-8")
print("Applied V13.2 simple Finsys-style Report Centre")
