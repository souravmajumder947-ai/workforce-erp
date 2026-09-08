from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
MARK="# V13.1 FULL FINSYS SHEET REPORT"
if MARK in s:
    print("V13.1 already applied")
    raise SystemExit(0)

# ------------------------------------------------------------
# Remove Working Date from sidebar. Keep an internal default only.
# ------------------------------------------------------------
old_sidebar='''global_work_date = st.sidebar.date_input(
    "Working Date", value=date.today(), format="DD/MM/YYYY", key="v5_global_work_date"
)
'''
new_sidebar='''# V13.1: Working Date removed from sidebar to avoid date/month confusion.
# Each operational page controls its own date/period.
global_work_date = date.today()
'''
if old_sidebar not in s:
    raise RuntimeError("Sidebar Working Date anchor not found")
s=s.replace(old_sidebar,new_sidebar,1)

# Daily Corrugation Report gets its own date selector.
old_daily='''        _v128_day=global_work_date
        st.caption(f"Date: {_v128_day.strftime('%d/%m/%Y')} · controlled by sidebar Working Date")
'''
new_daily='''        _v128_day=st.date_input(
            "Report Date",
            value=date.today(),
            format="DD/MM/YYYY",
            key="v131_daily_corrugation_date"
        )
        st.caption(f"Daily report: {_v128_day.strftime('%d/%m/%Y')}")
'''
if old_daily not in s:
    raise RuntimeError("Daily report date anchor not found")
s=s.replace(old_daily,new_daily,1)

# Production monthly report defaults to current month independently.
old_month='''        _v128_default_month=date(global_work_date.year,global_work_date.month,1)
'''
new_month='''        _v128_default_month=date(date.today().year,date.today().month,1)
'''
if old_month in s:
    s=s.replace(old_month,new_month,1)

# ------------------------------------------------------------
# Replace Reel Reports with a full Finsys-style sheet register.
# ------------------------------------------------------------
start=s.find('''    with tab_reel_reports:
        st.markdown("### Reel Reports")
''')
end=s.find('''    with tab_mp:
        c1,c2,c3=st.columns(3)
''',start)
if start==-1 or end==-1:
    raise RuntimeError("Reel Reports block boundaries not found")

block=r'''    with tab_reel_reports:
        # V13.1 FULL FINSYS SHEET REPORT
        st.markdown("### Reel Reports")
        st.caption(
            "Full Finsys-style Reel Wise Issue / Reel Wise Return register. "
            "Choose the period, search any field, sort the sheet and export selected columns."
        )

        _v131_report_type=st.radio(
            "Report Type",
            ["Reel Wise Issue","Reel Wise Return","Issue + Return"],
            horizontal=True,
            key="v131_report_type"
        )

        with st.expander("Select Period", expanded=True):
            _v131_preset=st.radio(
                "Quick Period",
                [
                    "M.T.D (Month To Date)","Y.T.D (Year To Date)",
                    "Previous Month","Next Month","Yesterday","Today",
                    "First Qtr","Second Qtr","Third Qtr","Fourth Qtr",
                    "Full Year","Custom"
                ],
                horizontal=True,
                key="v131_period_preset"
            )

            def _v131_month_bounds(_d):
                _first=date(_d.year,_d.month,1)
                if _d.month==12:
                    _next=date(_d.year+1,1,1)
                else:
                    _next=date(_d.year,_d.month+1,1)
                return _first,_next-timedelta(days=1)

            def _v131_shift_month(_d,_delta):
                _y,_m=_d.year,_d.month+_delta
                while _m<1:
                    _m+=12; _y-=1
                while _m>12:
                    _m-=12; _y+=1
                return date(_y,_m,1)

            def _v131_period(_preset):
                _wd=date.today()
                if _preset=="M.T.D (Month To Date)":
                    return date(_wd.year,_wd.month,1),_wd
                if _preset=="Y.T.D (Year To Date)":
                    return date(_wd.year,1,1),_wd
                if _preset=="Previous Month":
                    return _v131_month_bounds(_v131_shift_month(_wd,-1))
                if _preset=="Next Month":
                    return _v131_month_bounds(_v131_shift_month(_wd,1))
                if _preset=="Yesterday":
                    _y=_wd-timedelta(days=1)
                    return _y,_y
                if _preset=="Today":
                    return _wd,_wd
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
                return _v131_month_bounds(_wd)

            _pf,_pt=_v131_period(_v131_preset)
            if st.session_state.get("v131_last_period") != _v131_preset:
                if _v131_preset!="Custom":
                    st.session_state["v131_date_from"]=_pf
                    st.session_state["v131_date_to"]=_pt
                else:
                    st.session_state.setdefault("v131_date_from",_pf)
                    st.session_state.setdefault("v131_date_to",_pt)
                st.session_state["v131_last_period"]=_v131_preset

            d1,d2=st.columns(2)
            _v131_from=d1.date_input(
                "Date From",
                value=st.session_state.get("v131_date_from",_pf),
                format="DD/MM/YYYY",
                key="v131_date_from"
            )
            _v131_to=d2.date_input(
                "Date To",
                value=st.session_state.get("v131_date_to",_pt),
                format="DD/MM/YYYY",
                key="v131_date_to"
            )

        if _v131_from>_v131_to:
            st.error("Date From cannot be after Date To.")
        else:
            _v131_types=(
                ["ISSUE"] if _v131_report_type=="Reel Wise Issue"
                else ["RETURN"] if _v131_report_type=="Reel Wise Return"
                else ["ISSUE","RETURN"]
            )

            _v131_raw=read_df(
                """SELECT movement_type,work_date,vch_no,supplier,acode,item,
                          quantity_kg,quantity_ton,reel_no,co_reel,reel_mill,
                          irate,movement_value,job_no,job_date,reel_size,gsm,
                          icode,cpartno
                   FROM production_reel_transactions
                   WHERE work_date BETWEEN ? AND ?
                     AND movement_type = ANY(?::text[])
                   ORDER BY work_date,vch_no,reel_no""",
                (_v131_from.isoformat(),_v131_to.isoformat(),_v131_types)
            )

            _v131_search=st.text_input(
                "Search",
                placeholder="Voucher / Supplier / Item / Reel No / Job No / ICODE / Part No",
                key="v131_search"
            )

            if _v131_raw.empty:
                st.info(
                    f"No {_v131_report_type.lower()} records found from "
                    f"{_v131_from.strftime('%d/%m/%Y')} to {_v131_to.strftime('%d/%m/%Y')}."
                )
            else:
                _v131_df=_v131_raw.copy()
                if str(_v131_search or "").strip():
                    _needle=str(_v131_search).strip().lower()
                    _mask=_v131_df.astype(str).apply(
                        lambda col:col.str.lower().str.contains(_needle,na=False)
                    ).any(axis=1)
                    _v131_df=_v131_df[_mask].copy()

                _qty_col=(
                    "QTY_OUT" if _v131_report_type=="Reel Wise Issue"
                    else "QTY_RETURN" if _v131_report_type=="Reel Wise Return"
                    else "QTY_KG"
                )

                _v131_df=_v131_df.rename(columns={
                    "movement_type":"TYPE",
                    "work_date":"VCH_DT",
                    "vch_no":"VCH_NO",
                    "supplier":"SUPPLIER",
                    "acode":"ACODE",
                    "item":"ITEM",
                    "quantity_kg":_qty_col,
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

                _v131_df["VCH_DT"]=pd.to_datetime(
                    _v131_df["VCH_DT"],errors="coerce"
                ).dt.strftime("%d/%m/%Y")
                _v131_df["JOB_DT"]=pd.to_datetime(
                    _v131_df["JOB_DT"],errors="coerce"
                ).dt.strftime("%d/%m/%Y")

                _sheet_cols=[
                    "VCH_DT","VCH_NO","SUPPLIER","ITEM",_qty_col,
                    "REEL_NO","CO_REEL","REEL_MILL","TYPE","IRATE",
                    "JOB_NO","JOB_DT","REEL_SIZE","GSM","ICODE",
                    "CPARTNO","ACODE","QTY_TON","VALUE"
                ]
                _sheet_cols=[c for c in _sheet_cols if c in _v131_df.columns]

                _default_cols=[
                    "VCH_DT","VCH_NO","SUPPLIER","ITEM",_qty_col,
                    "REEL_NO","CO_REEL","REEL_MILL","TYPE","IRATE",
                    "JOB_NO","JOB_DT","REEL_SIZE","GSM","ICODE"
                ]
                _default_cols=[c for c in _default_cols if c in _v131_df.columns]

                with st.expander("Print / Export Selected Columns", expanded=False):
                    _v131_selected_cols=st.multiselect(
                        "Select report columns",
                        _sheet_cols,
                        default=_default_cols,
                        key="v131_selected_columns"
                    )
                    if not _v131_selected_cols:
                        _v131_selected_cols=_default_cols

                _records=len(_v131_df)
                _qty_kg=float(
                    pd.to_numeric(_v131_df[_qty_col],errors="coerce").fillna(0).sum()
                )
                _qty_ton=float(
                    pd.to_numeric(_v131_df["QTY_TON"],errors="coerce").fillna(0).sum()
                )
                _value=float(
                    pd.to_numeric(_v131_df["VALUE"],errors="coerce").fillna(0).sum()
                )
                _avg_rate=(
                    _value/_qty_kg if _qty_kg>0 else 0.0
                )

                st.markdown(
                    f"### {_v131_report_type} "
                    f"{_v131_from.strftime('%d/%m/%Y')} to {_v131_to.strftime('%d/%m/%Y')}"
                )

                # Finsys-style sheet totals directly above the register.
                h1,h2,h3,h4,h5=st.columns(5)
                h1.metric("Records",f"{_records:,}")
                h2.metric("Total Qty",f"{_qty_kg:,.0f} Kg")
                h3.metric("Total Ton",f"{_qty_ton:,.2f} T")
                h4.metric("Total Value",v5_money(_value))
                h5.metric("Avg Rate",f"₹{_avg_rate:,.2f}/Kg")

                st.caption(
                    "Click any column header to sort. Search filters the complete sheet. "
                    "Horizontal scroll is available for all ERP columns."
                )

                _v131_sheet=_v131_df[_v131_selected_cols].copy()
                st.dataframe(
                    _v131_sheet,
                    hide_index=True,
                    use_container_width=True,
                    height=650,
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
                _v131_excel=make_excel_report(
                    _v131_sheet,
                    _v131_report_type,
                    f"{_v131_from.strftime('%d/%m/%Y')} to {_v131_to.strftime('%d/%m/%Y')}"
                )
                e1.download_button(
                    "Download Excel - Current Sheet",
                    data=_v131_excel,
                    file_name=(
                        f"{_v131_report_type.replace(' ','_')}_"
                        f"{_v131_from.strftime('%Y%m%d')}_to_{_v131_to.strftime('%Y%m%d')}.xlsx"
                    ),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True,
                    key="v131_download_current_sheet"
                )

                _v131_csv=_v131_sheet.to_csv(index=False).encode("utf-8-sig")
                e2.download_button(
                    "Download CSV - Current Sheet",
                    data=_v131_csv,
                    file_name=(
                        f"{_v131_report_type.replace(' ','_')}_"
                        f"{_v131_from.strftime('%Y%m%d')}_to_{_v131_to.strftime('%Y%m%d')}.csv"
                    ),
                    mime="text/csv",
                    use_container_width=True,
                    key="v131_download_current_csv"
                )

'''
s=s[:start]+block+s[end:]
p.write_text(s,encoding="utf-8")
print("Applied V13.1 full Finsys sheet report and removed sidebar Working Date")
