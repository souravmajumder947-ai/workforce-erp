from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
MARK="# V13.0 FINSYS STYLE REEL REPORT VIEW"
if MARK in s:
    print("V13.0 already applied")
    raise SystemExit(0)

old_tabs='''    tab_prod,tab_daily_report,tab_monthly,tab_mp=st.tabs([
        "Production Entry","Daily Production Report","Monthly MD Report","Manpower Allocation"
    ])
'''
new_tabs='''    # V13.0 FINSYS STYLE REEL REPORT VIEW
    tab_prod,tab_daily_report,tab_monthly,tab_reel_reports,tab_mp=st.tabs([
        "Production Entry","Daily Production Report","Monthly MD Report",
        "Reel Reports","Manpower Allocation"
    ])
'''
if old_tabs not in s:
    raise RuntimeError("Operations tabs anchor not found")
s=s.replace(old_tabs,new_tabs,1)

insert_at=s.find('''    with tab_mp:
        c1,c2,c3=st.columns(3)
''')
if insert_at==-1:
    raise RuntimeError("Manpower tab anchor not found")

block=r'''    with tab_reel_reports:
        st.markdown("### Reel Reports")
        st.caption(
            "Finsys-style searchable register for Reel Wise Issue and Reel Wise Return. "
            "Use DD/MM/YYYY dates, search any field, sort columns and export the filtered result."
        )

        _v130_report_type=st.radio(
            "Report",
            ["Reel Wise Issue","Reel Wise Return","Issue + Return"],
            horizontal=True,
            key="v130_reel_report_type"
        )

        _v130_preset=st.selectbox(
            "Period",
            [
                "This Month","Previous Month","Next Month","Y.T.D (Year To Date)",
                "Today","Yesterday","First Qtr","Second Qtr","Third Qtr","Fourth Qtr",
                "Full Year","Custom"
            ],
            key="v130_period_preset"
        )

        def _v130_month_bounds(_d):
            _first=date(_d.year,_d.month,1)
            if _d.month==12:
                _next=date(_d.year+1,1,1)
            else:
                _next=date(_d.year,_d.month+1,1)
            return _first,_next-timedelta(days=1)

        def _v130_shift_month(_d,_delta):
            _y=_d.year
            _m=_d.month+_delta
            while _m<1:
                _m+=12; _y-=1
            while _m>12:
                _m-=12; _y+=1
            return date(_y,_m,1)

        def _v130_resolve_period(_preset):
            _wd=global_work_date
            if _preset=="This Month":
                return _v130_month_bounds(_wd)
            if _preset=="Previous Month":
                return _v130_month_bounds(_v130_shift_month(_wd,-1))
            if _preset=="Next Month":
                return _v130_month_bounds(_v130_shift_month(_wd,1))
            if _preset=="Y.T.D (Year To Date)":
                return date(_wd.year,1,1),_wd
            if _preset=="Today":
                return _wd,_wd
            if _preset=="Yesterday":
                _y=_wd-timedelta(days=1)
                return _y,_y
            if _preset=="First Qtr":
                return date(_wd.year,1,1),date(_wd.year,3,31)
            if _preset=="Second Qtr":
                return date(_wd.year,4,1),date(_wd.year,6,30)
            if _preset=="Third Qtr":
                return date(_wd.year,7,1),date(_wd.year,9,30)
            if _preset=="Fourth Qtr":
                return date(_wd.year,10,1),date(_wd.year,12,31)
            if _preset=="Full Year":
                return date(_wd.year,1,1),date(_wd.year,12,31)
            return _v130_month_bounds(_wd)

        _v130_preset_from,_v130_preset_to=_v130_resolve_period(_v130_preset)
        if st.session_state.get("v130_last_period") != _v130_preset:
            if _v130_preset!="Custom":
                st.session_state["v130_date_from"]=_v130_preset_from
                st.session_state["v130_date_to"]=_v130_preset_to
            elif "v130_date_from" not in st.session_state:
                st.session_state["v130_date_from"]=_v130_preset_from
                st.session_state["v130_date_to"]=_v130_preset_to
            st.session_state["v130_last_period"]=_v130_preset

        p1,p2=st.columns(2)
        _v130_from=p1.date_input(
            "Date From",
            value=st.session_state.get("v130_date_from",_v130_preset_from),
            format="DD/MM/YYYY",
            key="v130_date_from"
        )
        _v130_to=p2.date_input(
            "Date To",
            value=st.session_state.get("v130_date_to",_v130_preset_to),
            format="DD/MM/YYYY",
            key="v130_date_to"
        )

        if _v130_from>_v130_to:
            st.error("Date From cannot be after Date To.")
        else:
            _v130_movement_types=(
                ["ISSUE"] if _v130_report_type=="Reel Wise Issue"
                else ["RETURN"] if _v130_report_type=="Reel Wise Return"
                else ["ISSUE","RETURN"]
            )

            _v130_raw=read_df(
                """SELECT movement_type,work_date,vch_no,supplier,acode,item,
                          quantity_kg,quantity_ton,reel_no,co_reel,reel_mill,
                          irate,movement_value,job_no,job_date,reel_size,gsm,
                          icode,cpartno
                   FROM production_reel_transactions
                   WHERE work_date BETWEEN ? AND ?
                     AND movement_type = ANY(?::text[])
                   ORDER BY work_date,vch_no,reel_no""",
                (
                    _v130_from.isoformat(),
                    _v130_to.isoformat(),
                    _v130_movement_types
                )
            )

            _v130_search=st.text_input(
                "Search",
                placeholder="Voucher, supplier, item, reel no., job no., ICODE...",
                key="v130_reel_search"
            )

            if not _v130_raw.empty:
                _v130_view=_v130_raw.copy()
                if str(_v130_search or "").strip():
                    _needle=str(_v130_search).strip().lower()
                    _mask=_v130_view.astype(str).apply(
                        lambda col:col.str.lower().str.contains(_needle,na=False)
                    ).any(axis=1)
                    _v130_view=_v130_view[_mask].copy()

                _qty_name=(
                    "QTY_OUT"
                    if _v130_report_type=="Reel Wise Issue"
                    else "QTY_RETURN"
                    if _v130_report_type=="Reel Wise Return"
                    else "QTY_KG"
                )

                _v130_view=_v130_view.rename(columns={
                    "movement_type":"TYPE",
                    "work_date":"VCH_DT",
                    "vch_no":"VCH_NO",
                    "supplier":"SUPPLIER",
                    "acode":"ACODE",
                    "item":"ITEM",
                    "quantity_kg":_qty_name,
                    "quantity_ton":"QTY_TON",
                    "reel_no":"REEL_NO",
                    "co_reel":"CO_REEL",
                    "reel_mill":"REEL_MILL",
                    "irate":"IRATE",
                    "movement_value":"VALUE",
                    "job_no":"JOB_NO",
                    "job_date":"JOB_DT",
                    "reel_size":"REEL_SIZE",
                    "gsm":"GSM",
                    "icode":"ICODE",
                    "cpartno":"CPARTNO"
                })

                _v130_view["VCH_DT"]=pd.to_datetime(
                    _v130_view["VCH_DT"],errors="coerce"
                ).dt.strftime("%d/%m/%Y")
                _v130_view["JOB_DT"]=pd.to_datetime(
                    _v130_view["JOB_DT"],errors="coerce"
                ).dt.strftime("%d/%m/%Y")

                _all_cols=[
                    "VCH_DT","VCH_NO","SUPPLIER","ITEM",_qty_name,
                    "REEL_NO","CO_REEL","REEL_MILL","TYPE","IRATE",
                    "JOB_NO","JOB_DT","REEL_SIZE","GSM","ICODE","CPARTNO",
                    "ACODE","QTY_TON","VALUE"
                ]
                _default_cols=[
                    "VCH_DT","VCH_NO","SUPPLIER","ITEM",_qty_name,
                    "REEL_NO","CO_REEL","REEL_MILL","TYPE","IRATE",
                    "JOB_NO","JOB_DT","REEL_SIZE","GSM","ICODE"
                ]
                _all_cols=[c for c in _all_cols if c in _v130_view.columns]
                _default_cols=[c for c in _default_cols if c in _v130_view.columns]

                with st.expander("Report Columns"):
                    _v130_cols=st.multiselect(
                        "Columns to display/export",
                        _all_cols,
                        default=_default_cols,
                        key="v130_report_columns"
                    )
                    if not _v130_cols:
                        _v130_cols=_default_cols

                _v130_records=len(_v130_view)
                _v130_qty_kg=float(
                    pd.to_numeric(_v130_view.get(_qty_name,0),errors="coerce").fillna(0).sum()
                )
                _v130_qty_ton=float(
                    pd.to_numeric(_v130_view.get("QTY_TON",0),errors="coerce").fillna(0).sum()
                )
                _v130_value=float(
                    pd.to_numeric(_v130_view.get("VALUE",0),errors="coerce").fillna(0).sum()
                )

                st.markdown(
                    f"#### {_v130_report_type} "
                    f"{_v130_from.strftime('%d/%m/%Y')} to {_v130_to.strftime('%d/%m/%Y')}"
                )
                r1,r2,r3,r4=st.columns(4)
                r1.metric("Records",f"{_v130_records:,}")
                r2.metric("Total Quantity",f"{_v130_qty_kg:,.0f} Kg")
                r3.metric("Total Ton",f"{_v130_qty_ton:,.2f} T")
                r4.metric("Movement Value",v5_money(_v130_value))

                st.caption(
                    "Click a column header to sort. Use Search to filter the register. "
                    "The total above updates with the filtered result."
                )

                st.dataframe(
                    _v130_view[_v130_cols],
                    hide_index=True,
                    use_container_width=True,
                    height=560,
                    column_config={
                        _qty_name:st.column_config.NumberColumn(_qty_name,format="%.0f"),
                        "QTY_TON":st.column_config.NumberColumn("QTY_TON",format="%.2f T"),
                        "IRATE":st.column_config.NumberColumn("IRATE",format="₹%.2f"),
                        "VALUE":st.column_config.NumberColumn("VALUE",format="₹%.2f"),
                        "REEL_SIZE":st.column_config.NumberColumn("REEL_SIZE",format="%.0f"),
                        "GSM":st.column_config.NumberColumn("GSM",format="%.0f"),
                    }
                )

                _v130_export=_v130_view[_v130_cols].copy()
                _v130_bytes=make_excel_report(
                    _v130_export,
                    _v130_report_type,
                    f"{_v130_from.strftime('%d/%m/%Y')} to {_v130_to.strftime('%d/%m/%Y')}"
                )
                st.download_button(
                    "Download Excel Report",
                    data=_v130_bytes,
                    file_name=(
                        f"{_v130_report_type.replace(' ','_')}_"
                        f"{_v130_from.strftime('%Y%m%d')}_to_{_v130_to.strftime('%Y%m%d')}.xlsx"
                    ),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True,
                    key="v130_download_reel_register"
                )
            else:
                st.info(
                    f"No {_v130_report_type.lower()} records found from "
                    f"{_v130_from.strftime('%d/%m/%Y')} to {_v130_to.strftime('%d/%m/%Y')}."
                )

'''
s=s[:insert_at]+block+s[insert_at:]
p.write_text(s,encoding="utf-8")
print("Applied V13.0 Finsys-style Reel Reports view")
