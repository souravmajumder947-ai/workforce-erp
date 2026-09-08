from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
MARK="# V13.3 REEL WISE CONSUMPTION REPORT"
if MARK in s:
    print("V13.3 already applied")
    raise SystemExit(0)

s=s.replace(
'''            [
                "Reel Wise Issue",
                "Reel Wise Return",
                "Daily Corrugation",
                "Monthly Corrugation"
            ],''',
'''            [
                "Reel Wise Issue",
                "Reel Wise Return",
                "Reel Wise Consumption",
                "Daily Corrugation",
                "Monthly Corrugation"
            ],''',
1
)

s=s.replace(
'''        # ---------------- REEL WISE ISSUE / RETURN ----------------
        if _v132_report in ["Reel Wise Issue","Reel Wise Return"]:''',
'''        # V13.3 REEL WISE CONSUMPTION REPORT
        # ---------------- REEL WISE ISSUE / RETURN / CONSUMPTION ----------------
        if _v132_report in ["Reel Wise Issue","Reel Wise Return","Reel Wise Consumption"]:''',
1
)

start=s.find('''                if st.session_state.get("v132_reel_ready"):
''')
end=s.find('''        # ---------------- DAILY CORRUGATION ----------------
''',start)
if start==-1 or end==-1:
    raise RuntimeError("Reel report ready block not found")

block=r'''                if st.session_state.get("v132_reel_ready"):
                    _rr_type=st.session_state.get("v132_reel_type",_v132_report)
                    _rr_from=st.session_state.get("v132_reel_from",_v132_from)
                    _rr_to=st.session_state.get("v132_reel_to",_v132_to)

                    st.markdown("---")
                    st.markdown(
                        f"### {_rr_type} {_rr_from.strftime('%d/%m/%Y')} to {_rr_to.strftime('%d/%m/%Y')}"
                    )

                    _search=st.text_input(
                        "Search",
                        placeholder="Enter search string & press Enter",
                        key="v132_reel_search"
                    )

                    if _rr_type=="Reel Wise Consumption":
                        _raw=read_df(
                            """SELECT work_date,line_no,reel_reference,paper_grade,
                                      COALESCE(NULLIF(consumption_ton,0),quantity_ton) AS consumption_ton,
                                      value_amount,remark
                               FROM production_reel_consumption
                               WHERE machine='Corrugation'
                                 AND work_date BETWEEN ? AND ?
                                 AND COALESCE(NULLIF(consumption_ton,0),quantity_ton)>0
                               ORDER BY work_date,line_no""",
                            (_rr_from.isoformat(),_rr_to.isoformat())
                        )

                        if _raw.empty:
                            st.info(
                                "No actual reel consumption records found for the selected period. "
                                "Issue/Return data is not treated as consumption."
                            )
                        else:
                            _df=_raw.copy()
                            if str(_search or "").strip():
                                _needle=str(_search).strip().lower()
                                _mask=_df.astype(str).apply(
                                    lambda col:col.str.lower().str.contains(_needle,na=False)
                                ).any(axis=1)
                                _df=_df[_mask].copy()

                            _df["QTY_CONS"]=pd.to_numeric(
                                _df["consumption_ton"],errors="coerce"
                            ).fillna(0.0)*1000.0
                            _df["QTY_TON"]=pd.to_numeric(
                                _df["consumption_ton"],errors="coerce"
                            ).fillna(0.0)
                            _df["VALUE"]=pd.to_numeric(
                                _df["value_amount"],errors="coerce"
                            ).fillna(0.0)
                            _df["RATE"]=_df.apply(
                                lambda r:(
                                    float(r["VALUE"])/float(r["QTY_CONS"])
                                    if float(r["QTY_CONS"])>0 else 0.0
                                ),
                                axis=1
                            )
                            _df=_df.rename(columns={
                                "work_date":"VCH_DT",
                                "line_no":"LINE",
                                "reel_reference":"ERP_CODE",
                                "paper_grade":"ITEM",
                                "remark":"REMARK"
                            })
                            _df["VCH_DT"]=pd.to_datetime(
                                _df["VCH_DT"],errors="coerce"
                            ).dt.strftime("%d/%m/%Y")

                            _all_cols=[
                                "VCH_DT","LINE","ERP_CODE","ITEM",
                                "QTY_CONS","QTY_TON","RATE","VALUE","REMARK"
                            ]
                            _all_cols=[c for c in _all_cols if c in _df.columns]
                            _default_cols=[
                                "VCH_DT","ERP_CODE","ITEM",
                                "QTY_CONS","QTY_TON","RATE","VALUE"
                            ]
                            _default_cols=[c for c in _default_cols if c in _df.columns]

                            with st.expander("Print / Export Selected Columns"):
                                _show_cols=st.multiselect(
                                    "Columns",
                                    _all_cols,
                                    default=_default_cols,
                                    key="v133_consumption_columns"
                                )
                                if not _show_cols:
                                    _show_cols=_default_cols

                            _records=len(_df)
                            _kg=float(pd.to_numeric(_df["QTY_CONS"],errors="coerce").fillna(0).sum())
                            _ton=float(pd.to_numeric(_df["QTY_TON"],errors="coerce").fillna(0).sum())
                            _value=float(pd.to_numeric(_df["VALUE"],errors="coerce").fillna(0).sum())
                            _avg_rate=(_value/_kg) if _kg>0 else 0.0

                            m1,m2,m3,m4,m5=st.columns(5)
                            m1.metric("Records",f"{_records:,}")
                            m2.metric("Consumption Qty",f"{_kg:,.0f} Kg")
                            m3.metric("Consumption Ton",f"{_ton:,.2f} T")
                            m4.metric("Consumption Value",v5_money(_value))
                            m5.metric("Avg Rate",f"₹{_avg_rate:,.2f}/Kg")

                            st.caption(
                                "Actual consumption only. Net Issue is not used as consumption. "
                                "Click column headers to sort and use horizontal scroll for the full sheet."
                            )
                            _sheet=_df[_show_cols].copy()
                            st.dataframe(
                                _sheet,
                                hide_index=True,
                                use_container_width=True,
                                height=620,
                                column_config={
                                    "QTY_CONS":st.column_config.NumberColumn("QTY_CONS",format="%.0f"),
                                    "QTY_TON":st.column_config.NumberColumn("QTY_TON",format="%.2f T"),
                                    "RATE":st.column_config.NumberColumn("RATE",format="₹%.2f"),
                                    "VALUE":st.column_config.NumberColumn("VALUE",format="₹%.2f"),
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
                                file_name=f"Reel_Wise_Consumption_{_rr_from:%Y%m%d}_to_{_rr_to:%Y%m%d}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                type="primary",
                                use_container_width=True,
                                key="v133_consumption_excel"
                            )
                            e2.download_button(
                                "Download CSV",
                                data=_sheet.to_csv(index=False).encode("utf-8-sig"),
                                file_name=f"Reel_Wise_Consumption_{_rr_from:%Y%m%d}_to_{_rr_to:%Y%m%d}.csv",
                                mime="text/csv",
                                use_container_width=True,
                                key="v133_consumption_csv"
                            )
                    else:
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

'''
s=s[:start]+block+s[end:]
p.write_text(s,encoding="utf-8")
print("Applied V13.3 Reel Wise Consumption report")
