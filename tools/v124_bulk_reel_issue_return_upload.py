from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
MARK="# V12.4 BULK REEL ISSUE RETURN UPLOAD"
if MARK in s:
    print("V12.4 bulk reel upload already applied")
    raise SystemExit(0)

anchor='''                st.markdown("#### Reel Issue / Return / Consumption")
'''
if anchor not in s:
    raise RuntimeError("Reel material-flow section anchor not found")

bulk=r'''                # V12.4 BULK REEL ISSUE RETURN UPLOAD
                with st.expander("📥 Bulk Upload Reel Issue / Return", expanded=False):
                    st.caption(
                        "Upload the complete day or month in one CSV/XLSX file. "
                        "A Date column is mandatory because Daily and Monthly MD reports are date-wise."
                    )

                    _v124_template=pd.DataFrame([{
                        "Date":"01/09/2026",
                        "Reel / ERP Code":"ERP001",
                        "Paper Description / GSM":"Kraft 150 GSM",
                        "Opening WIP Ton":0.000,
                        "Reel Issue Ton":15.000,
                        "Reel Return Ton":1.500,
                        "Closing WIP Ton":0.700,
                        "Actual Consumption Ton":12.800,
                        "Consumption Value ₹":710000.00,
                        "Remark":""
                    }])
                    st.download_button(
                        "Download Bulk Upload Template",
                        data=_v124_template.to_csv(index=False).encode("utf-8-sig"),
                        file_name="Reel_Issue_Return_Consumption_Template.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="v124_reel_template_download"
                    )

                    _v124_file=st.file_uploader(
                        "Upload Reel Issue / Return File",
                        type=["csv","xlsx"],
                        key="v124_reel_bulk_file",
                        help=(
                            "Supported source headings include Date, ERP_CODE, INAME, REEL_ISS, "
                            "REEL_RET, NET_ISSUE, REEL_CONS, FLOOR_WIP, UNIT and Value/Amount."
                        )
                    )
                    _v124_unit_mode=st.selectbox(
                        "Quantity Unit",
                        ["Auto from UNIT column","Kg","Ton"],
                        key="v124_reel_unit_mode",
                        help=(
                            "Choose Auto when your source has a UNIT column. "
                            "If the source is in KG, the app converts it to Ton automatically."
                        )
                    )
                    _v124_replace=st.checkbox(
                        "Replace existing reel movement lines for dates contained in this upload",
                        value=False,
                        key="v124_reel_replace",
                        help=(
                            "This replaces only reel movement detail for uploaded dates. "
                            "Saved production output, waste, breakdown and manpower are preserved."
                        )
                    )

                    _v124_parsed=None
                    _v124_parse_errors=[]
                    _v124_existing_dates=[]
                    if _v124_file is not None:
                        try:
                            _v124_file.seek(0)
                            _v124_name=str(getattr(_v124_file,"name","")).lower()
                            if _v124_name.endswith(".csv"):
                                _v124_raw=pd.read_csv(_v124_file)
                            else:
                                _v124_raw=pd.read_excel(_v124_file,engine="openpyxl")

                            _v124_raw.columns=[str(c).strip() for c in _v124_raw.columns]
                            _v124_norm={
                                "".join(ch for ch in str(c).lower() if ch.isalnum()):c
                                for c in _v124_raw.columns
                            }

                            def _v124_pick(*aliases):
                                for _a in aliases:
                                    _k="".join(ch for ch in str(_a).lower() if ch.isalnum())
                                    if _k in _v124_norm:
                                        return _v124_norm[_k]
                                return None

                            _v124_cols={
                                "date":_v124_pick("Date","Work Date","Production Date","Issue Date","Entry Date"),
                                "erp":_v124_pick("Reel / ERP Code","ERP_CODE","ERP Code","Reel Code","Reel Reference","Item Code","Code"),
                                "desc":_v124_pick("Paper Description / GSM","INAME","Item Name","Paper Description","Paper Grade","Paper GSM","Description"),
                                "opening":_v124_pick("Opening WIP Ton","Opening WIP","Opening Floor WIP","Opening Stock"),
                                "issue":_v124_pick("Reel Issue Ton","REEL_ISS","Reel Issue","Issue Qty","Issue"),
                                "return":_v124_pick("Reel Return Ton","REEL_RET","Reel Return","Return Qty","Return"),
                                "net":_v124_pick("Net Issue Ton","NET_ISSUE","Net Issue"),
                                "closing":_v124_pick("Closing WIP Ton","FLOOR_WIP","Floor WIP","Closing WIP","Closing Stock"),
                                "cons":_v124_pick("Actual Consumption Ton","REEL_CONS","Reel Cons","Consumption Ton","Consumption","Consumption Qty"),
                                "value":_v124_pick("Consumption Value ₹","Consumption Value","VALUE","Value","Amount","Value Amount","Consumption Amount"),
                                "unit":_v124_pick("UNIT","Unit","UOM"),
                                "remark":_v124_pick("Remark","Remarks"),
                            }

                            if _v124_cols["date"] is None:
                                _v124_parse_errors.append(
                                    "Date column is missing. A monthly summary without dates cannot be imported "
                                    "into the day-wise production report."
                                )
                            if _v124_cols["issue"] is None and _v124_cols["cons"] is None:
                                _v124_parse_errors.append(
                                    "Reel Issue / REEL_ISS or Actual Consumption / REEL_CONS column is required."
                                )
                            if _v124_cols["erp"] is None and _v124_cols["desc"] is None:
                                _v124_parse_errors.append(
                                    "ERP Code or Paper Description column is required."
                                )
                            if (
                                _v124_unit_mode=="Auto from UNIT column"
                                and _v124_cols["unit"] is None
                            ):
                                _v124_parse_errors.append(
                                    "UNIT column is not present. Select Kg or Ton manually in Quantity Unit."
                                )

                            _v124_rows=[]
                            if not _v124_parse_errors:
                                for _idx,_row in _v124_raw.iterrows():
                                    _date_raw=_row.get(_v124_cols["date"])
                                    if pd.isna(_date_raw) or str(_date_raw).strip()=="":
                                        continue

                                    if isinstance(_date_raw,(datetime,date)):
                                        _work_date=_date_raw.date() if isinstance(_date_raw,datetime) else _date_raw
                                    else:
                                        _date_text=str(_date_raw).strip()
                                        _date_parsed=pd.to_datetime(
                                            _date_text,errors="coerce",dayfirst=True
                                        )
                                        if pd.isna(_date_parsed):
                                            _v124_parse_errors.append(
                                                f"Invalid Date at source row {_idx+2}: {_date_text}"
                                            )
                                            continue
                                        _work_date=_date_parsed.date()

                                    _unit_text=(
                                        str(_row.get(_v124_cols["unit"]) or "").strip().upper()
                                        if _v124_cols["unit"] else ""
                                    )
                                    if _v124_unit_mode=="Kg":
                                        _factor=0.001
                                    elif _v124_unit_mode=="Ton":
                                        _factor=1.0
                                    else:
                                        if "KG" in _unit_text:
                                            _factor=0.001
                                        elif (
                                            "TON" in _unit_text
                                            or "MT" in _unit_text
                                            or _unit_text in {"T","TONNE","TONNES"}
                                        ):
                                            _factor=1.0
                                        else:
                                            _v124_parse_errors.append(
                                                f"Unknown UNIT '{_unit_text}' at source row {_idx+2}. "
                                                "Select Kg or Ton manually."
                                            )
                                            continue

                                    def _v124_num(col):
                                        if col is None:
                                            return 0.0
                                        try:
                                            _val=_row.get(col)
                                            if pd.isna(_val) or str(_val).strip()=="":
                                                return 0.0
                                            return float(str(_val).replace(",","").replace("₹","").strip())
                                        except Exception:
                                            return 0.0

                                    _opening=max(_v124_num(_v124_cols["opening"])*_factor,0.0)
                                    _issue=max(_v124_num(_v124_cols["issue"])*_factor,0.0)
                                    _return=max(_v124_num(_v124_cols["return"])*_factor,0.0)
                                    _closing=max(_v124_num(_v124_cols["closing"])*_factor,0.0)
                                    _actual=max(_v124_num(_v124_cols["cons"])*_factor,0.0)
                                    _value=max(_v124_num(_v124_cols["value"]),0.0)
                                    _net=_issue-_return
                                    _expected=_opening+_net-_closing
                                    if _expected < -0.0005 and _actual<=0:
                                        _v124_parse_errors.append(
                                            f"Negative expected consumption at source row {_idx+2}. "
                                            "Check Issue, Return and WIP values."
                                        )
                                        continue
                                    _effective=_actual if _actual>0 else max(_expected,0.0)

                                    _source_net=(
                                        _v124_num(_v124_cols["net"])*_factor
                                        if _v124_cols["net"] else None
                                    )
                                    _net_variance=(
                                        (_source_net-_net)
                                        if _source_net is not None else 0.0
                                    )

                                    _v124_rows.append({
                                        "Date":_work_date,
                                        "Reel / ERP Code":(
                                            str(_row.get(_v124_cols["erp"]) or "").strip()
                                            if _v124_cols["erp"] else ""
                                        ),
                                        "Paper Description / GSM":(
                                            str(_row.get(_v124_cols["desc"]) or "").strip()
                                            if _v124_cols["desc"] else ""
                                        ),
                                        "Opening WIP Ton":_opening,
                                        "Reel Issue Ton":_issue,
                                        "Reel Return Ton":_return,
                                        "Net Issue Ton":_net,
                                        "Closing WIP Ton":_closing,
                                        "Actual Consumption Ton":_actual,
                                        "Consumption Ton":_effective,
                                        "Consumption Value ₹":_value,
                                        "Flow Variance Ton":_expected-_effective,
                                        "Source Net Variance Ton":_net_variance,
                                        "Remark":(
                                            str(_row.get(_v124_cols["remark"]) or "").strip()
                                            if _v124_cols["remark"] else ""
                                        ),
                                    })

                                _v124_parsed=pd.DataFrame(_v124_rows)
                                if _v124_parsed.empty and not _v124_parse_errors:
                                    _v124_parse_errors.append("No valid movement rows were found in the uploaded file.")

                            if _v124_parse_errors:
                                for _err in _v124_parse_errors[:20]:
                                    st.error(_err)
                            elif _v124_parsed is not None and not _v124_parsed.empty:
                                _v124_dates=sorted(_v124_parsed["Date"].unique().tolist())
                                _v124_date_iso=[d.isoformat() for d in _v124_dates]
                                _v124_existing=read_df(
                                    """SELECT work_date,COUNT(*) AS lines
                                       FROM production_reel_consumption
                                       WHERE machine='Corrugation'
                                         AND work_date = ANY(?::date[])
                                       GROUP BY work_date ORDER BY work_date""",
                                    (_v124_date_iso,)
                                )
                                _v124_existing_dates=(
                                    _v124_existing["work_date"].astype(str).tolist()
                                    if not _v124_existing.empty else []
                                )

                                st.markdown("##### Upload Preview")
                                p1,p2,p3,p4,p5=st.columns(5)
                                p1.metric("Rows",f"{len(_v124_parsed):,}")
                                p2.metric("Dates",f"{len(_v124_dates):,}")
                                p3.metric(
                                    "Reel Issue",
                                    f"{float(_v124_parsed['Reel Issue Ton'].sum()):,.3f} T"
                                )
                                p4.metric(
                                    "Reel Return",
                                    f"{float(_v124_parsed['Reel Return Ton'].sum()):,.3f} T"
                                )
                                p5.metric(
                                    "Consumption",
                                    f"{float(_v124_parsed['Consumption Ton'].sum()):,.3f} T"
                                )
                                st.dataframe(
                                    _v124_parsed.head(100),
                                    hide_index=True,use_container_width=True,
                                    column_config={
                                        "Opening WIP Ton":st.column_config.NumberColumn(format="%.3f T"),
                                        "Reel Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                                        "Reel Return Ton":st.column_config.NumberColumn(format="%.3f T"),
                                        "Net Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                                        "Closing WIP Ton":st.column_config.NumberColumn(format="%.3f T"),
                                        "Actual Consumption Ton":st.column_config.NumberColumn(format="%.3f T"),
                                        "Consumption Ton":st.column_config.NumberColumn(format="%.3f T"),
                                        "Consumption Value ₹":st.column_config.NumberColumn(format="₹%.2f"),
                                        "Flow Variance Ton":st.column_config.NumberColumn(format="%.3f T"),
                                        "Source Net Variance Ton":st.column_config.NumberColumn(format="%.3f T"),
                                    }
                                )
                                if len(_v124_parsed)>100:
                                    st.caption(f"Preview shows first 100 of {len(_v124_parsed):,} rows.")

                                if _v124_existing_dates and not _v124_replace:
                                    st.warning(
                                        f"Existing reel movement data is already present for "
                                        f"{len(_v124_existing_dates)} uploaded date(s). "
                                        "Tick Replace existing reel movement lines to continue safely."
                                    )

                                _v124_can_import=not (
                                    _v124_existing_dates and not _v124_replace
                                )
                                if st.button(
                                    "Import Reel Issue / Return Data",
                                    type="primary",
                                    use_container_width=True,
                                    disabled=not _v124_can_import,
                                    key="v124_import_reel_movements"
                                ):
                                    _conn=get_pg_conn()
                                    try:
                                        _cur=_conn.cursor()
                                        _dates_iso=sorted({
                                            d.isoformat() for d in _v124_parsed["Date"].tolist()
                                        })
                                        if _v124_replace:
                                            _cur.execute(
                                                """DELETE FROM production_reel_consumption
                                                   WHERE machine='Corrugation'
                                                     AND work_date = ANY(%s::date[])""",
                                                (_dates_iso,)
                                            )

                                        # If there was no prior data, delete is unnecessary; start line numbers at 1.
                                        # When existing data is present, import is allowed only in explicit replace mode.
                                        for _day in sorted(_v124_parsed["Date"].unique().tolist()):
                                            _day_rows=_v124_parsed[
                                                _v124_parsed["Date"]==_day
                                            ].reset_index(drop=True)
                                            for _line_no,(_, _rr) in enumerate(
                                                _day_rows.iterrows(),start=1
                                            ):
                                                _cur.execute(
                                                    """INSERT INTO production_reel_consumption(
                                                       work_date,machine,line_no,reel_reference,paper_grade,
                                                       opening_wip_ton,reel_issue_ton,reel_return_ton,net_issue_ton,
                                                       closing_wip_ton,consumption_ton,quantity_ton,
                                                       value_amount,remark,entered_by,updated_at
                                                       ) VALUES (
                                                       %s,'Corrugation',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP
                                                       )
                                                       ON CONFLICT(work_date,machine,line_no) DO UPDATE SET
                                                       reel_reference=excluded.reel_reference,
                                                       paper_grade=excluded.paper_grade,
                                                       opening_wip_ton=excluded.opening_wip_ton,
                                                       reel_issue_ton=excluded.reel_issue_ton,
                                                       reel_return_ton=excluded.reel_return_ton,
                                                       net_issue_ton=excluded.net_issue_ton,
                                                       closing_wip_ton=excluded.closing_wip_ton,
                                                       consumption_ton=excluded.consumption_ton,
                                                       quantity_ton=excluded.quantity_ton,
                                                       value_amount=excluded.value_amount,
                                                       remark=excluded.remark,
                                                       entered_by=excluded.entered_by,
                                                       updated_at=CURRENT_TIMESTAMP""",
                                                    (
                                                        _day.isoformat(),_line_no,
                                                        str(_rr["Reel / ERP Code"] or "").strip(),
                                                        str(_rr["Paper Description / GSM"] or "").strip(),
                                                        float(_rr["Opening WIP Ton"]),
                                                        float(_rr["Reel Issue Ton"]),
                                                        float(_rr["Reel Return Ton"]),
                                                        float(_rr["Net Issue Ton"]),
                                                        float(_rr["Closing WIP Ton"]),
                                                        float(_rr["Consumption Ton"]),
                                                        float(_rr["Consumption Ton"]),
                                                        float(_rr["Consumption Value ₹"]),
                                                        str(_rr["Remark"] or "").strip(),
                                                        _current_user["username"]
                                                    )
                                                )

                                            _day_consumption=float(
                                                _day_rows["Consumption Ton"].sum()
                                            )
                                            _day_value=float(
                                                _day_rows["Consumption Value ₹"].sum()
                                            )

                                            _cur.execute(
                                                """SELECT production_ton,good_output_ton,waste_ton,
                                                          target_ton,breakdown_hours,remark
                                                   FROM production
                                                   WHERE work_date=%s AND shift='DAY'
                                                     AND machine='Corrugation'
                                                   LIMIT 1""",
                                                (_day.isoformat(),)
                                            )
                                            _ep=_cur.fetchone()
                                            _good=0.0
                                            _waste=0.0
                                            _existing_target=0.0
                                            if _ep:
                                                _good=float(_ep[1] or _ep[0] or 0)
                                                _waste=float(_ep[2] or 0)
                                                _existing_target=float(_ep[3] or 0)
                                            _yield=(
                                                _good/_day_consumption*100.0
                                                if _day_consumption>0 else 0.0
                                            )
                                            _waste_pct=(
                                                _waste/_day_consumption*100.0
                                                if _day_consumption>0 else 0.0
                                            )
                                            _target=(
                                                _existing_target
                                                if _existing_target>0 else float(daily_target)
                                            )

                                            _cur.execute(
                                                """INSERT INTO production(
                                                   work_date,shift,machine,production_ton,target_ton,
                                                   waste_ton,breakdown_hours,paper_cost,ink_cost,glue_cost,
                                                   other_material_cost,target_type,opening_wip_ton,
                                                   material_received_ton,material_available_ton,
                                                   material_processed_ton,good_output_ton,closing_wip_ton,
                                                   conversion_pct,yield_pct,waste_pct,remark
                                                   ) VALUES (
                                                   %s,'DAY','Corrugation',0,%s,0,0,%s,0,0,0,'FIXED_TON',
                                                   0,0,%s,%s,0,0,0,0,0,
                                                   'Reel movement bulk upload · production pending'
                                                   )
                                                   ON CONFLICT(work_date,shift,machine) DO UPDATE SET
                                                   paper_cost=excluded.paper_cost,
                                                   target_ton=CASE
                                                       WHEN COALESCE(production.target_ton,0)>0
                                                       THEN production.target_ton
                                                       ELSE excluded.target_ton
                                                   END,
                                                   target_type='FIXED_TON',
                                                   material_available_ton=excluded.material_available_ton,
                                                   material_processed_ton=excluded.material_processed_ton,
                                                   yield_pct=%s,
                                                   waste_pct=%s""",
                                                (
                                                    _day.isoformat(),_target,_day_value,
                                                    _day_consumption,_day_consumption,
                                                    _yield,_waste_pct
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
                                        "REEL_MOVEMENT_BULK_IMPORT",
                                        "Operations",
                                        "Production Reel Movement",
                                        f"{min(_v124_dates).isoformat()}|{max(_v124_dates).isoformat()}",
                                        (
                                            f"Rows={len(_v124_parsed)}; Dates={len(_v124_dates)}; "
                                            f"Issue={float(_v124_parsed['Reel Issue Ton'].sum()):.3f}; "
                                            f"Return={float(_v124_parsed['Reel Return Ton'].sum()):.3f}; "
                                            f"Consumption={float(_v124_parsed['Consumption Ton'].sum()):.3f}; "
                                            f"Value={float(_v124_parsed['Consumption Value ₹'].sum()):.2f}; "
                                            f"ReplaceExisting={bool(_v124_replace)}"
                                        )
                                    )
                                    st.success(
                                        f"Imported {len(_v124_parsed):,} reel movement rows across "
                                        f"{len(_v124_dates):,} date(s)."
                                    )
                                    st.rerun()
                        except Exception as _v124_exc:
                            st.error(f"Unable to read/import reel movement file: {_v124_exc}")

'''
s=s.replace(anchor,bulk+anchor,1)
p.write_text(s,encoding="utf-8")
print("Applied V12.4 bulk reel issue/return upload")
