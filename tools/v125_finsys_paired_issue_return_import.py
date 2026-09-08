from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
MARK="# V12.5 FINSYS PAIRED REEL ISSUE RETURN IMPORT"
if MARK in s:
    print("V12.5 already applied")
    raise SystemExit(0)

anchor='''                # V12.4 BULK REEL ISSUE RETURN UPLOAD
'''
if anchor not in s:
    raise RuntimeError("V12.4 anchor not found")

dual=r'''                # V12.5 FINSYS PAIRED REEL ISSUE RETURN IMPORT
                try:
                    _v125_conn=get_pg_conn()
                    _v125_cur=_v125_conn.cursor()
                    _v125_cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS production_reel_transactions(
                            id BIGSERIAL PRIMARY KEY,
                            movement_type TEXT NOT NULL,
                            work_date DATE NOT NULL,
                            vch_no TEXT,
                            supplier TEXT,
                            acode TEXT,
                            item TEXT,
                            quantity_kg NUMERIC(14,3) NOT NULL DEFAULT 0,
                            quantity_ton NUMERIC(14,6) NOT NULL DEFAULT 0,
                            reel_no TEXT,
                            co_reel TEXT,
                            reel_mill TEXT,
                            irate NUMERIC(14,4) NOT NULL DEFAULT 0,
                            movement_value NUMERIC(16,2) NOT NULL DEFAULT 0,
                            job_no TEXT,
                            job_date DATE,
                            reel_size NUMERIC(14,3) NOT NULL DEFAULT 0,
                            gsm NUMERIC(14,3) NOT NULL DEFAULT 0,
                            icode TEXT,
                            cpartno TEXT,
                            source_file TEXT,
                            source_row INTEGER,
                            entered_by TEXT,
                            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(movement_type,work_date,source_file,source_row)
                        )
                        """
                    )
                    _v125_conn.commit()
                    _v125_cur.close()
                    _v125_conn.close()
                except Exception as _v125_schema_exc:
                    try:
                        _v125_conn.rollback()
                        _v125_conn.close()
                    except Exception:
                        pass
                    st.error(f"Unable to prepare detailed reel movement storage: {_v125_schema_exc}")
                    st.stop()

                with st.expander("📥 Finsys Reel Issue + Reel Return Upload (Recommended)", expanded=False):
                    st.caption(
                        "Upload the two original Finsys files separately. These files are treated as KG-based "
                        "transaction data. Issue − Return is shown as Net Issue; it is NOT treated as consumption."
                    )
                    u1,u2=st.columns(2)
                    _v125_issue_file=u1.file_uploader(
                        "1. Upload Reel Issue File",
                        type=["csv","xlsx"],
                        key="v125_issue_file",
                        help="Expected Finsys columns include VCH_DT, ITEM, QTY_OUT, REEL_NO, IRATE, JOB_NO, REEL_SIZE, GSM, ICODE."
                    )
                    _v125_return_file=u2.file_uploader(
                        "2. Upload Reel Return File",
                        type=["csv","xlsx"],
                        key="v125_return_file",
                        help="Expected Finsys columns include VCH_DT, ITEM, QTY_RETURN, REEL_NO, IRATE, JOB_NO, REEL_SIZE, GSM, ICODE."
                    )
                    _v125_replace=st.checkbox(
                        "Replace previously imported Finsys Issue/Return transactions for the uploaded dates",
                        value=False,
                        key="v125_replace",
                        help="This replaces only detailed Issue/Return transaction rows. Production, manpower and consumption data are preserved."
                    )

                    def _v125_read_upload(_file):
                        _file.seek(0)
                        _name=str(getattr(_file,"name","")).lower()
                        if _name.endswith(".csv"):
                            _df=pd.read_csv(_file)
                        else:
                            _df=pd.read_excel(_file,engine="openpyxl")
                        _df.columns=[str(c).strip() for c in _df.columns]
                        return _df

                    def _v125_text(_value):
                        try:
                            if pd.isna(_value):
                                return ""
                        except Exception:
                            pass
                        if _value is None:
                            return ""
                        _t=str(_value).strip()
                        if _t.endswith(".0"):
                            try:
                                return str(int(float(_t)))
                            except Exception:
                                pass
                        return _t

                    def _v125_num(_value):
                        try:
                            if pd.isna(_value) or str(_value).strip()=="":
                                return 0.0
                        except Exception:
                            pass
                        try:
                            return float(str(_value).replace(",","").replace("₹","").strip())
                        except Exception:
                            return 0.0

                    def _v125_parse(_file,_movement):
                        _df=_v125_read_upload(_file)
                        _required=["VCH_DT","ITEM","REEL_NO","IRATE","ICODE"]
                        _qty_col="QTY_OUT" if _movement=="ISSUE" else "QTY_RETURN"
                        _required.append(_qty_col)
                        _missing=[c for c in _required if c not in _df.columns]
                        if _missing:
                            raise ValueError(
                                f"{_movement.title()} file is missing required column(s): {', '.join(_missing)}"
                            )
                        _rows=[]
                        for _idx,_r in _df.iterrows():
                            _dt=pd.to_datetime(_r.get("VCH_DT"),errors="coerce",dayfirst=True)
                            _qty=_v125_num(_r.get(_qty_col))
                            if pd.isna(_dt) or _qty<=0:
                                continue
                            _rate=_v125_num(_r.get("IRATE"))
                            _job_dt=pd.to_datetime(_r.get("JOB_DT"),errors="coerce",dayfirst=True)
                            _rows.append({
                                "Movement":_movement,
                                "Date":_dt.date(),
                                "Voucher No":_v125_text(_r.get("VCH_NO")),
                                "Supplier":_v125_text(_r.get("SUPPLIER")),
                                "ACODE":_v125_text(_r.get("ACODE")),
                                "Item":_v125_text(_r.get("ITEM")),
                                "Qty Kg":_qty,
                                "Qty Ton":_qty/1000.0,
                                "Reel No":_v125_text(_r.get("REEL_NO")),
                                "Company Reel":_v125_text(_r.get("CO_REEL")),
                                "Reel Mill":_v125_text(_r.get("REEL_MILL")),
                                "Rate ₹/Kg":_rate,
                                "Movement Value ₹":_qty*_rate,
                                "Job No":_v125_text(_r.get("JOB_NO")),
                                "Job Date":(
                                    _job_dt.date() if not pd.isna(_job_dt) else None
                                ),
                                "Reel Size":_v125_num(_r.get("REEL_SIZE")),
                                "GSM":_v125_num(_r.get("GSM")),
                                "ICODE":_v125_text(_r.get("ICODE")),
                                "Customer Part No":_v125_text(_r.get("CPARTNO")),
                                "Source Row":int(_idx)+2,
                                "Source File":str(getattr(_file,"name","")).strip(),
                            })
                        return pd.DataFrame(_rows)

                    _v125_issue_df=None
                    _v125_return_df=None
                    _v125_errors=[]
                    if _v125_issue_file is not None:
                        try:
                            _v125_issue_df=_v125_parse(_v125_issue_file,"ISSUE")
                        except Exception as _exc:
                            _v125_errors.append(str(_exc))
                    if _v125_return_file is not None:
                        try:
                            _v125_return_df=_v125_parse(_v125_return_file,"RETURN")
                        except Exception as _exc:
                            _v125_errors.append(str(_exc))

                    for _err in _v125_errors:
                        st.error(_err)

                    if (
                        not _v125_errors
                        and _v125_issue_df is not None
                        and _v125_return_df is not None
                    ):
                        if _v125_issue_df.empty or _v125_return_df.empty:
                            st.error("One of the two uploaded files contains no valid movement rows.")
                        else:
                            _v125_all=pd.concat(
                                [_v125_issue_df,_v125_return_df],
                                ignore_index=True
                            )
                            _v125_dates=sorted(_v125_all["Date"].unique().tolist())
                            _v125_issue_t=float(_v125_issue_df["Qty Ton"].sum())
                            _v125_return_t=float(_v125_return_df["Qty Ton"].sum())
                            _v125_net_t=_v125_issue_t-_v125_return_t
                            _v125_issue_value=float(_v125_issue_df["Movement Value ₹"].sum())
                            _v125_return_value=float(_v125_return_df["Movement Value ₹"].sum())
                            _v125_net_value=_v125_issue_value-_v125_return_value

                            p1,p2,p3,p4,p5=st.columns(5)
                            p1.metric("Issue Rows",f"{len(_v125_issue_df):,}")
                            p2.metric("Return Rows",f"{len(_v125_return_df):,}")
                            p3.metric("Reel Issue",f"{_v125_issue_t:,.3f} T")
                            p4.metric("Reel Return",f"{_v125_return_t:,.3f} T")
                            p5.metric("Net Issue",f"{_v125_net_t:,.3f} T")

                            p1,p2,p3,p4=st.columns(4)
                            p1.metric("Movement Dates",f"{len(_v125_dates):,}")
                            p2.metric("Issue Value",v5_money(_v125_issue_value))
                            p3.metric("Return Value",v5_money(_v125_return_value))
                            p4.metric("Net Issue Value",v5_money(_v125_net_value))

                            st.caption(
                                f"Date range: {min(_v125_dates).strftime('%d/%m/%Y')} to "
                                f"{max(_v125_dates).strftime('%d/%m/%Y')}. "
                                "Values are movement values from QTY × IRATE, not consumption value."
                            )

                            _v125_preview=_v125_all[[
                                "Movement","Date","Voucher No","Reel No","Company Reel",
                                "ICODE","Item","GSM","Reel Size","Qty Kg","Qty Ton",
                                "Rate ₹/Kg","Movement Value ₹","Job No"
                            ]].head(100)
                            st.dataframe(
                                _v125_preview,
                                hide_index=True,use_container_width=True,
                                column_config={
                                    "Qty Kg":st.column_config.NumberColumn(format="%.0f"),
                                    "Qty Ton":st.column_config.NumberColumn(format="%.3f T"),
                                    "Rate ₹/Kg":st.column_config.NumberColumn(format="₹%.2f"),
                                    "Movement Value ₹":st.column_config.NumberColumn(format="₹%.2f"),
                                }
                            )
                            if len(_v125_all)>100:
                                st.caption(f"Preview shows first 100 of {len(_v125_all):,} transaction rows.")

                            _v125_existing=read_df(
                                """SELECT COUNT(*) AS rows
                                   FROM production_reel_transactions
                                   WHERE work_date BETWEEN ? AND ?
                                     AND movement_type IN ('ISSUE','RETURN')""",
                                (
                                    min(_v125_dates).isoformat(),
                                    max(_v125_dates).isoformat()
                                )
                            )
                            _v125_existing_count=(
                                int(_v125_existing.iloc[0]["rows"] or 0)
                                if not _v125_existing.empty else 0
                            )
                            if _v125_existing_count and not _v125_replace:
                                st.warning(
                                    f"{_v125_existing_count:,} Finsys Issue/Return transaction row(s) "
                                    "already exist in this date range. Tick Replace to import again safely."
                                )

                            if st.button(
                                "Import Finsys Reel Issue + Return",
                                type="primary",
                                use_container_width=True,
                                disabled=bool(_v125_existing_count and not _v125_replace),
                                key="v125_import_pair"
                            ):
                                _conn=get_pg_conn()
                                try:
                                    _cur=_conn.cursor()
                                    if _v125_replace:
                                        _cur.execute(
                                            """DELETE FROM production_reel_transactions
                                               WHERE work_date BETWEEN %s AND %s
                                                 AND movement_type IN ('ISSUE','RETURN')""",
                                            (
                                                min(_v125_dates).isoformat(),
                                                max(_v125_dates).isoformat()
                                            )
                                        )
                                    for _,_rr in _v125_all.iterrows():
                                        _cur.execute(
                                            """INSERT INTO production_reel_transactions(
                                               movement_type,work_date,vch_no,supplier,acode,item,
                                               quantity_kg,quantity_ton,reel_no,co_reel,reel_mill,
                                               irate,movement_value,job_no,job_date,reel_size,gsm,
                                               icode,cpartno,source_file,source_row,entered_by,updated_at
                                               ) VALUES (
                                               %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                               %s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP
                                               )
                                               ON CONFLICT(movement_type,work_date,source_file,source_row)
                                               DO UPDATE SET
                                               vch_no=excluded.vch_no,supplier=excluded.supplier,
                                               acode=excluded.acode,item=excluded.item,
                                               quantity_kg=excluded.quantity_kg,
                                               quantity_ton=excluded.quantity_ton,
                                               reel_no=excluded.reel_no,co_reel=excluded.co_reel,
                                               reel_mill=excluded.reel_mill,irate=excluded.irate,
                                               movement_value=excluded.movement_value,
                                               job_no=excluded.job_no,job_date=excluded.job_date,
                                               reel_size=excluded.reel_size,gsm=excluded.gsm,
                                               icode=excluded.icode,cpartno=excluded.cpartno,
                                               entered_by=excluded.entered_by,
                                               updated_at=CURRENT_TIMESTAMP""",
                                            (
                                                str(_rr["Movement"]),
                                                _rr["Date"].isoformat(),
                                                str(_rr["Voucher No"]),
                                                str(_rr["Supplier"]),
                                                str(_rr["ACODE"]),
                                                str(_rr["Item"]),
                                                float(_rr["Qty Kg"]),
                                                float(_rr["Qty Ton"]),
                                                str(_rr["Reel No"]),
                                                str(_rr["Company Reel"]),
                                                str(_rr["Reel Mill"]),
                                                float(_rr["Rate ₹/Kg"]),
                                                float(_rr["Movement Value ₹"]),
                                                str(_rr["Job No"]),
                                                _rr["Job Date"].isoformat() if _rr["Job Date"] else None,
                                                float(_rr["Reel Size"]),
                                                float(_rr["GSM"]),
                                                str(_rr["ICODE"]),
                                                str(_rr["Customer Part No"]),
                                                str(_rr["Source File"]),
                                                int(_rr["Source Row"]),
                                                _current_user["username"]
                                            )
                                        )
                                    _conn.commit()
                                    _cur.close()
                                except Exception:
                                    _conn.rollback()
                                    raise
                                finally:
                                    _conn.close()

                                record_audit_event(
                                    _current_user["username"],
                                    "FINSYS_REEL_ISSUE_RETURN_IMPORT",
                                    "Operations",
                                    "Production Reel Transactions",
                                    f"{min(_v125_dates).isoformat()}|{max(_v125_dates).isoformat()}",
                                    (
                                        f"IssueRows={len(_v125_issue_df)}; ReturnRows={len(_v125_return_df)}; "
                                        f"IssueTon={_v125_issue_t:.3f}; ReturnTon={_v125_return_t:.3f}; "
                                        f"NetIssueTon={_v125_net_t:.3f}; IssueValue={_v125_issue_value:.2f}; "
                                        f"ReturnValue={_v125_return_value:.2f}; Replace={bool(_v125_replace)}"
                                    )
                                )
                                st.success(
                                    f"Imported {len(_v125_issue_df):,} issue rows and "
                                    f"{len(_v125_return_df):,} return rows successfully."
                                )
                                st.rerun()

'''
s=s.replace(anchor,dual+anchor,1)

# Daily report: load detailed movement totals and use them for Issue/Return.
daily_query_anchor='''        _v123_mp=read_df(
'''
daily_query_insert='''        _v125_move_day=read_df(
            """SELECT movement_type,
                      SUM(quantity_ton) AS qty_ton,
                      SUM(movement_value) AS movement_value
               FROM production_reel_transactions
               WHERE work_date=?
               GROUP BY movement_type""",
            (_v123_day.isoformat(),)
        )
'''
if daily_query_anchor not in s:
    raise RuntimeError("Daily manpower query anchor not found")
s=s.replace(daily_query_anchor,daily_query_insert+daily_query_anchor,1)

daily_calc_anchor='''            _v123_expected=_v123_opening+_v123_net-_v123_closing
'''
daily_calc_new='''            _v125_issue_value=0.0
            _v125_return_value=0.0
            if not _v125_move_day.empty:
                for _,_mv in _v125_move_day.iterrows():
                    if str(_mv["movement_type"])=="ISSUE":
                        _v123_issue=float(_mv["qty_ton"] or 0)
                        _v125_issue_value=float(_mv["movement_value"] or 0)
                    elif str(_mv["movement_type"])=="RETURN":
                        _v123_return=float(_mv["qty_ton"] or 0)
                        _v125_return_value=float(_mv["movement_value"] or 0)
                _v123_net=_v123_issue-_v123_return
            _v125_net_issue_value=_v125_issue_value-_v125_return_value

            _v123_expected=_v123_opening+_v123_net-_v123_closing
'''
if daily_calc_anchor not in s:
    raise RuntimeError("Daily material calculation anchor not found")
s=s.replace(daily_calc_anchor,daily_calc_new,1)

daily_metrics_anchor='''            c1,c2,c3,c4=st.columns(4)
            c1.metric("Actual Consumption",f"{_v123_consumption:,.3f} T")
            c2.metric("Consumption Value",v5_money(_v123_value))
            c3.metric("Avg Paper Rate",f"₹{_v123_avg_rate:,.2f}/Kg")
            c4.metric("Flow Variance",f"{_v123_flow_variance:,.3f} T")
'''
daily_metrics_new='''            c1,c2,c3,c4=st.columns(4)
            c1.metric("Issue Value",v5_money(_v125_issue_value))
            c2.metric("Return Value",v5_money(_v125_return_value))
            c3.metric("Net Issue Value",v5_money(_v125_net_issue_value))
            c4.metric(
                "Actual Consumption",
                f"{_v123_consumption:,.3f} T" if _v123_consumption>0 else "PENDING"
            )

            c1,c2,c3=st.columns(3)
            c1.metric("Consumption Value",v5_money(_v123_value))
            c2.metric("Avg Paper Rate",f"₹{_v123_avg_rate:,.2f}/Kg")
            c3.metric("Flow Variance",f"{_v123_flow_variance:,.3f} T")
            if _v123_consumption<=0 and (_v123_issue>0 or _v123_return>0):
                st.info(
                    "Issue and Return are loaded. Actual Consumption is still pending and is not being assumed from Net Issue."
                )
'''
if daily_metrics_anchor not in s:
    raise RuntimeError("Daily metrics anchor not found")
s=s.replace(daily_metrics_anchor,daily_metrics_new,1)

# Monthly report: load transaction totals by date.
monthly_mp_anchor='''        _v123_mp_month=read_df(
'''
monthly_move_insert='''        _v125_move_month=read_df(
            """SELECT work_date,
                      SUM(CASE WHEN movement_type='ISSUE' THEN quantity_ton ELSE 0 END) AS raw_issue_ton,
                      SUM(CASE WHEN movement_type='RETURN' THEN quantity_ton ELSE 0 END) AS raw_return_ton,
                      SUM(CASE WHEN movement_type='ISSUE' THEN movement_value ELSE 0 END) AS raw_issue_value,
                      SUM(CASE WHEN movement_type='RETURN' THEN movement_value ELSE 0 END) AS raw_return_value
               FROM production_reel_transactions
               WHERE work_date BETWEEN ? AND ?
               GROUP BY work_date
               ORDER BY work_date""",
            (_v123_first.isoformat(),_v123_last.isoformat())
        )
'''
if monthly_mp_anchor not in s:
    raise RuntimeError("Monthly manpower query anchor not found")
s=s.replace(monthly_mp_anchor,monthly_move_insert+monthly_mp_anchor,1)

dates_anchor='''            if not _v123_reel_day.empty:
                _v123_dates.update(_v123_reel_day["work_date"].tolist())
            _v123_daily=pd.DataFrame({"work_date":sorted(_v123_dates)})
'''
dates_new='''            if not _v123_reel_day.empty:
                _v123_dates.update(_v123_reel_day["work_date"].tolist())
            if not _v125_move_month.empty:
                _v125_move_month["work_date"]=_v125_move_month["work_date"].astype(str)
                _v123_dates.update(_v125_move_month["work_date"].tolist())
            _v123_daily=pd.DataFrame({"work_date":sorted(_v123_dates)})
'''
if dates_anchor not in s:
    raise RuntimeError("Monthly dates anchor not found")
s=s.replace(dates_anchor,dates_new,1)

merge_anchor='''            for _c in [
                "production_ton","target_ton","waste_ton","breakdown_hours",
'''
merge_insert='''            if not _v125_move_month.empty:
                _v123_daily=_v123_daily.merge(
                    _v125_move_month,on="work_date",how="left"
                )
            else:
                for _c in [
                    "raw_issue_ton","raw_return_ton","raw_issue_value","raw_return_value"
                ]:
                    _v123_daily[_c]=0.0

'''
if merge_anchor not in s:
    raise RuntimeError("Monthly numeric loop anchor not found")
s=s.replace(merge_anchor,merge_insert+merge_anchor,1)

assign_anchor='''            _v123_daily["Opening WIP Ton"]=_v123_daily["opening_wip_ton"]
            _v123_daily["Reel Issue Ton"]=_v123_daily["reel_issue_ton"]
            _v123_daily["Reel Return Ton"]=_v123_daily["reel_return_ton"]
'''
assign_new='''            for _c in [
                "raw_issue_ton","raw_return_ton","raw_issue_value","raw_return_value"
            ]:
                if _c not in _v123_daily.columns:
                    _v123_daily[_c]=0.0
                _v123_daily[_c]=pd.to_numeric(
                    _v123_daily[_c],errors="coerce"
                ).fillna(0.0)

            _v123_daily["Opening WIP Ton"]=_v123_daily["opening_wip_ton"]
            _v123_daily["Reel Issue Ton"]=_v123_daily.apply(
                lambda r:(
                    float(r["raw_issue_ton"])
                    if float(r["raw_issue_ton"])>0
                    else float(r["reel_issue_ton"])
                ),axis=1
            )
            _v123_daily["Reel Return Ton"]=_v123_daily.apply(
                lambda r:(
                    float(r["raw_return_ton"])
                    if float(r["raw_return_ton"])>0
                    else float(r["reel_return_ton"])
                ),axis=1
            )
            _v123_daily["Issue Value"]=_v123_daily["raw_issue_value"]
            _v123_daily["Return Value"]=_v123_daily["raw_return_value"]
            _v123_daily["Net Issue Value"]=(
                _v123_daily["Issue Value"]-_v123_daily["Return Value"]
            )
'''
if assign_anchor not in s:
    raise RuntimeError("Monthly issue/return assignment anchor not found")
s=s.replace(assign_anchor,assign_new,1)

# Add movement value totals to KPI calculation and table.
totals_anchor='''            _v123_net_total=_v123_issue_total-_v123_return_total
            _v123_consumption_total=float(_v123_daily["Consumption Ton"].sum())
'''
totals_new='''            _v123_net_total=_v123_issue_total-_v123_return_total
            _v125_issue_value_total=float(_v123_daily["Issue Value"].sum())
            _v125_return_value_total=float(_v123_daily["Return Value"].sum())
            _v125_net_issue_value_total=_v125_issue_value_total-_v125_return_value_total
            _v123_consumption_total=float(_v123_daily["Consumption Ton"].sum())
'''
if totals_anchor not in s:
    raise RuntimeError("Monthly totals anchor not found")
s=s.replace(totals_anchor,totals_new,1)

kpi_anchor='''            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("Consumption",f"{_v123_consumption_total:,.2f} T")
'''
kpi_new='''            c1,c2,c3=st.columns(3)
            c1.metric("Issue Value",v5_money(_v125_issue_value_total))
            c2.metric("Return Value",v5_money(_v125_return_value_total))
            c3.metric("Net Issue Value",v5_money(_v125_net_issue_value_total))

            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric(
                "Consumption",
                f"{_v123_consumption_total:,.2f} T" if _v123_consumption_total>0 else "PENDING"
            )
'''
if kpi_anchor not in s:
    raise RuntimeError("Monthly KPI anchor not found")
s=s.replace(kpi_anchor,kpi_new,1)

display_anchor='''                "Date","Opening WIP Ton","Reel Issue Ton","Reel Return Ton","Net Issue Ton",
                "Consumption Ton","Closing WIP Ton","Consumption Value","Avg Rate ₹/Kg",
'''
display_new='''                "Date","Opening WIP Ton","Reel Issue Ton","Reel Return Ton","Net Issue Ton",
                "Issue Value","Return Value","Net Issue Value",
                "Consumption Ton","Closing WIP Ton","Consumption Value","Avg Rate ₹/Kg",
'''
if display_anchor not in s:
    raise RuntimeError("Monthly display columns anchor not found")
s=s.replace(display_anchor,display_new,1)

config_anchor='''                    "Net Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                    "Consumption Ton":st.column_config.NumberColumn(format="%.3f T"),
'''
config_new='''                    "Net Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                    "Issue Value":st.column_config.NumberColumn(format="₹%.2f"),
                    "Return Value":st.column_config.NumberColumn(format="₹%.2f"),
                    "Net Issue Value":st.column_config.NumberColumn(format="₹%.2f"),
                    "Consumption Ton":st.column_config.NumberColumn(format="%.3f T"),
'''
if config_anchor not in s:
    raise RuntimeError("Monthly display config anchor not found")
s=s.replace(config_anchor,config_new,1)

p.write_text(s,encoding="utf-8")
print("Applied V12.5 paired Finsys reel issue/return importer")
