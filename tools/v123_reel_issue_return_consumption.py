from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
MARK="# V12.3 REEL ISSUE RETURN CONSUMPTION FLOW"
if MARK in s:
    print("V12.3 already applied")
    raise SystemExit(0)

# ------------------------------------------------------------------
# 1) Extend reel storage safely. Existing quantity_ton remains the
#    backward-compatible consumption field.
# ------------------------------------------------------------------
schema_anchor='''            _v118_conn.commit()
            _v118_cur.close()
            _v118_conn.close()
'''
schema_new='''            # V12.3 REEL ISSUE RETURN CONSUMPTION FLOW
            for _v123_stmt in [
                "ALTER TABLE production_reel_consumption ADD COLUMN IF NOT EXISTS opening_wip_ton NUMERIC(14,4) NOT NULL DEFAULT 0",
                "ALTER TABLE production_reel_consumption ADD COLUMN IF NOT EXISTS reel_issue_ton NUMERIC(14,4) NOT NULL DEFAULT 0",
                "ALTER TABLE production_reel_consumption ADD COLUMN IF NOT EXISTS reel_return_ton NUMERIC(14,4) NOT NULL DEFAULT 0",
                "ALTER TABLE production_reel_consumption ADD COLUMN IF NOT EXISTS net_issue_ton NUMERIC(14,4) NOT NULL DEFAULT 0",
                "ALTER TABLE production_reel_consumption ADD COLUMN IF NOT EXISTS closing_wip_ton NUMERIC(14,4) NOT NULL DEFAULT 0",
                "ALTER TABLE production_reel_consumption ADD COLUMN IF NOT EXISTS consumption_ton NUMERIC(14,4) NOT NULL DEFAULT 0"
            ]:
                _v118_cur.execute(_v123_stmt)
            # Preserve older valid consumption rows without inventing issue/return history.
            _v118_cur.execute(
                """UPDATE production_reel_consumption
                   SET consumption_ton=quantity_ton
                   WHERE COALESCE(consumption_ton,0)=0 AND COALESCE(quantity_ton,0)>0"""
            )
            _v118_conn.commit()
            _v118_cur.close()
            _v118_conn.close()
'''
if schema_anchor not in s:
    raise RuntimeError("Reel schema commit anchor not found")
s=s.replace(schema_anchor,schema_new,1)

s=s.replace(
    '"Production is day-wise by machine. Corrugation uses daily reel consumption; downstream machines use daily material-conversion flow.",',
    '"Production is day-wise by machine. Corrugation tracks reel issue, return, WIP and consumption; downstream machines use daily material-conversion flow.",',
    1
)
s=s.replace(
    '"Production reports below use only data saved in this application: reel consumption, daily production and manpower allocation."',
    '"Production reports below use only data saved in this application: reel issue/return/consumption, daily production and manpower allocation."',
    1
)
s=s.replace(
    '"Enter each reel / paper line for the full production day. "'
    '\n                    "Paper Consumed, Paper Value and Average Paper Rate are calculated automatically."',
    '"Enter reel issue, return, WIP and actual consumption for the full production day. "'
    '\n                    "Net Issue, expected consumption, value and rate are calculated automatically."',
    1
)

# ------------------------------------------------------------------
# 2) Replace Corrugation reel-entry block with material-flow entry.
# ------------------------------------------------------------------
reel_start=s.find('''                _reels_existing = read_df(
''')
reel_end=s.find('''                _existing_good=float(er.get("good_output_ton") or er.get("production_ton") or 0)
''',reel_start)
if reel_start==-1 or reel_end==-1:
    raise RuntimeError("Corrugation reel-entry block boundaries not found")

new_reel=r'''                _reels_existing = read_df(
                    """SELECT line_no,reel_reference,paper_grade,
                              opening_wip_ton,reel_issue_ton,reel_return_ton,net_issue_ton,
                              closing_wip_ton,consumption_ton,quantity_ton,value_amount,remark
                       FROM production_reel_consumption
                       WHERE work_date=? AND machine=?
                       ORDER BY line_no""",
                    (pdate.isoformat(),machine)
                )

                if _reels_existing.empty:
                    _legacy_qty=float(er.get("material_processed_ton") or 0)
                    _legacy_value=float(er.get("paper_cost") or 0)
                    if _legacy_qty>0 or _legacy_value>0:
                        _reel_seed=pd.DataFrame([{
                            "Reel / Reference":"Legacy Daily Total",
                            "Paper Grade":"",
                            "Opening WIP Ton":0.0,
                            "Reel Issue Ton":0.0,
                            "Reel Return Ton":0.0,
                            "Closing WIP Ton":0.0,
                            "Actual Consumption Ton":_legacy_qty,
                            "Value ₹":_legacy_value,
                            "Remark":"Existing consumption retained; issue/return history not available"
                        }])
                    else:
                        _reel_seed=pd.DataFrame([{
                            "Reel / Reference":"",
                            "Paper Grade":"",
                            "Opening WIP Ton":0.0,
                            "Reel Issue Ton":0.0,
                            "Reel Return Ton":0.0,
                            "Closing WIP Ton":0.0,
                            "Actual Consumption Ton":0.0,
                            "Value ₹":0.0,
                            "Remark":""
                        }])
                else:
                    _reel_seed=_reels_existing.copy()
                    _reel_seed["consumption_ton"]=pd.to_numeric(
                        _reel_seed["consumption_ton"],errors="coerce"
                    ).fillna(0.0)
                    _reel_seed["quantity_ton"]=pd.to_numeric(
                        _reel_seed["quantity_ton"],errors="coerce"
                    ).fillna(0.0)
                    _reel_seed["consumption_ton"]=_reel_seed["consumption_ton"].where(
                        _reel_seed["consumption_ton"]>0,_reel_seed["quantity_ton"]
                    )
                    _reel_seed=_reel_seed.rename(columns={
                        "reel_reference":"Reel / Reference",
                        "paper_grade":"Paper Grade",
                        "opening_wip_ton":"Opening WIP Ton",
                        "reel_issue_ton":"Reel Issue Ton",
                        "reel_return_ton":"Reel Return Ton",
                        "closing_wip_ton":"Closing WIP Ton",
                        "consumption_ton":"Actual Consumption Ton",
                        "value_amount":"Value ₹",
                        "remark":"Remark"
                    })[[
                        "Reel / Reference","Paper Grade","Opening WIP Ton",
                        "Reel Issue Ton","Reel Return Ton","Closing WIP Ton",
                        "Actual Consumption Ton","Value ₹","Remark"
                    ]].copy()

                st.markdown("#### Reel Issue / Return / Consumption")
                st.caption(
                    "Formula: Net Issue = Reel Issue − Reel Return. "
                    "Expected Consumption = Opening WIP + Net Issue − Closing WIP. "
                    "If you already have actual consumption from stores/ERP, enter it in Actual Consumption Ton."
                )
                reel_editor=st.data_editor(
                    _reel_seed,
                    hide_index=True,
                    use_container_width=True,
                    num_rows="dynamic",
                    key=f"v123_reel_flow_editor_{pdate.isoformat()}_{machine}",
                    column_config={
                        "Reel / Reference":st.column_config.TextColumn("Reel / ERP Code"),
                        "Paper Grade":st.column_config.TextColumn("Paper Description / GSM"),
                        "Opening WIP Ton":st.column_config.NumberColumn(
                            "Opening WIP Ton",min_value=0.0,step=0.001,format="%.3f"
                        ),
                        "Reel Issue Ton":st.column_config.NumberColumn(
                            "Reel Issue Ton",min_value=0.0,step=0.001,format="%.3f"
                        ),
                        "Reel Return Ton":st.column_config.NumberColumn(
                            "Reel Return Ton",min_value=0.0,step=0.001,format="%.3f"
                        ),
                        "Closing WIP Ton":st.column_config.NumberColumn(
                            "Closing WIP Ton",min_value=0.0,step=0.001,format="%.3f"
                        ),
                        "Actual Consumption Ton":st.column_config.NumberColumn(
                            "Actual Consumption Ton",min_value=0.0,step=0.001,format="%.3f",
                            help="Enter actual consumption if available. Leave 0 to use the material-flow calculation."
                        ),
                        "Value ₹":st.column_config.NumberColumn(
                            "Consumption Value ₹",min_value=0.0,step=1.0,format="₹%.2f"
                        ),
                        "Remark":st.column_config.TextColumn("Remark"),
                    }
                )

                _reel_work=reel_editor.copy()
                for _v123_col in [
                    "Opening WIP Ton","Reel Issue Ton","Reel Return Ton",
                    "Closing WIP Ton","Actual Consumption Ton","Value ₹"
                ]:
                    _reel_work[_v123_col]=pd.to_numeric(
                        _reel_work[_v123_col],errors="coerce"
                    ).fillna(0.0)

                _reel_work=_reel_work[
                    (_reel_work["Opening WIP Ton"]>0)
                    | (_reel_work["Reel Issue Ton"]>0)
                    | (_reel_work["Reel Return Ton"]>0)
                    | (_reel_work["Closing WIP Ton"]>0)
                    | (_reel_work["Actual Consumption Ton"]>0)
                    | (_reel_work["Value ₹"]>0)
                    | (_reel_work["Reel / Reference"].fillna("").astype(str).str.strip()!="")
                    | (_reel_work["Paper Grade"].fillna("").astype(str).str.strip()!="")
                ].copy()

                if not _reel_work.empty:
                    _reel_work["Net Issue Ton"]=(
                        _reel_work["Reel Issue Ton"]-_reel_work["Reel Return Ton"]
                    )
                    _reel_work["Expected Consumption Ton"]=(
                        _reel_work["Opening WIP Ton"]
                        +_reel_work["Net Issue Ton"]
                        -_reel_work["Closing WIP Ton"]
                    )
                    _reel_work["Effective Consumption Ton"]=_reel_work.apply(
                        lambda r:(
                            float(r["Actual Consumption Ton"])
                            if float(r["Actual Consumption Ton"])>0
                            else max(float(r["Expected Consumption Ton"]),0.0)
                        ),
                        axis=1
                    )
                    _reel_work["Flow Variance Ton"]=(
                        _reel_work["Expected Consumption Ton"]
                        -_reel_work["Effective Consumption Ton"]
                    )
                    _reel_work["Rate ₹/Kg"]=_reel_work.apply(
                        lambda r:(
                            float(r["Value ₹"])/(float(r["Effective Consumption Ton"])*1000.0)
                            if float(r["Effective Consumption Ton"])>0 else 0.0
                        ),
                        axis=1
                    )
                else:
                    for _v123_col in [
                        "Net Issue Ton","Expected Consumption Ton","Effective Consumption Ton",
                        "Flow Variance Ton","Rate ₹/Kg"
                    ]:
                        _reel_work[_v123_col]=pd.Series(dtype=float)

                _reel_flow_errors=[]
                if not _reel_work.empty:
                    _v123_negative_expected=_reel_work[
                        _reel_work["Expected Consumption Ton"] < -0.0005
                    ]
                    if not _v123_negative_expected.empty:
                        _reel_flow_errors.append(
                            "One or more reel lines have negative expected consumption. "
                            "Check Opening WIP, Issue, Return and Closing WIP."
                        )

                paper_consumed=float(
                    _reel_work["Effective Consumption Ton"].sum()
                ) if not _reel_work.empty else 0.0
                paper_value=float(
                    _reel_work["Value ₹"].sum()
                ) if not _reel_work.empty else 0.0
                total_opening_wip=float(
                    _reel_work["Opening WIP Ton"].sum()
                ) if not _reel_work.empty else 0.0
                total_reel_issue=float(
                    _reel_work["Reel Issue Ton"].sum()
                ) if not _reel_work.empty else 0.0
                total_reel_return=float(
                    _reel_work["Reel Return Ton"].sum()
                ) if not _reel_work.empty else 0.0
                total_net_issue=total_reel_issue-total_reel_return
                total_closing_wip=float(
                    _reel_work["Closing WIP Ton"].sum()
                ) if not _reel_work.empty else 0.0
                total_expected_consumption=(
                    total_opening_wip+total_net_issue-total_closing_wip
                )
                total_flow_variance=total_expected_consumption-paper_consumed
                avg_paper_rate=(
                    paper_value/(paper_consumed*1000.0)
                    if paper_consumed>0 else 0.0
                )

                f1,f2,f3,f4,f5=st.columns(5)
                f1.metric("Opening WIP",f"{total_opening_wip:.3f} T")
                f2.metric("Reel Issue",f"{total_reel_issue:.3f} T")
                f3.metric("Reel Return",f"{total_reel_return:.3f} T")
                f4.metric("Net Issue",f"{total_net_issue:.3f} T")
                f5.metric("Closing WIP",f"{total_closing_wip:.3f} T")

                if not _reel_work.empty:
                    st.caption(
                        "Live material-flow check. Flow Variance = Expected Consumption − Actual/Effective Consumption."
                    )
                    st.dataframe(
                        _reel_work[[
                            "Reel / Reference","Paper Grade","Opening WIP Ton",
                            "Reel Issue Ton","Reel Return Ton","Net Issue Ton",
                            "Closing WIP Ton","Expected Consumption Ton",
                            "Effective Consumption Ton","Value ₹","Rate ₹/Kg","Flow Variance Ton","Remark"
                        ]],
                        hide_index=True,use_container_width=True,
                        column_config={
                            "Reel / Reference":st.column_config.TextColumn("Reel / ERP Code"),
                            "Paper Grade":st.column_config.TextColumn("Paper Description / GSM"),
                            "Opening WIP Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Reel Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Reel Return Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Net Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Closing WIP Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Expected Consumption Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Effective Consumption Ton":st.column_config.NumberColumn("Consumption Ton",format="%.3f T"),
                            "Value ₹":st.column_config.NumberColumn("Consumption Value ₹",format="₹%.2f"),
                            "Rate ₹/Kg":st.column_config.NumberColumn(format="₹%.2f"),
                            "Flow Variance Ton":st.column_config.NumberColumn(format="%.3f T"),
                        }
                    )
                if abs(total_flow_variance)>0.01:
                    st.warning(
                        f"Reel flow variance is {total_flow_variance:.3f} T. "
                        "This is allowed when actual consumption differs from stock-flow calculation, but should be reviewed."
                    )

'''
s=s[:reel_start]+new_reel+s[reel_end:]

# ------------------------------------------------------------------
# 3) Save validation + transaction now persist full reel flow.
# ------------------------------------------------------------------
validation_anchor='''                    if not _reel_work.empty:
                        _bad_qty=_reel_work[
                            pd.to_numeric(_reel_work["Qty Consumed Ton"],errors="coerce").fillna(0)<=0
                        ]
                        if not _bad_qty.empty:
                            _fixed_errors.append(
                                "Every saved reel / paper line must have Qty Consumed Ton greater than 0."
                            )

                    if _fixed_errors:
'''
validation_new='''                    if _reel_flow_errors:
                        _fixed_errors.extend(_reel_flow_errors)
                    if not _reel_work.empty:
                        _blank_reference=_reel_work[
                            (_reel_work["Reel / Reference"].fillna("").astype(str).str.strip()=="")
                            & (_reel_work["Paper Grade"].fillna("").astype(str).str.strip()=="")
                        ]
                        if not _blank_reference.empty:
                            _fixed_errors.append(
                                "Each reel movement line must have a Reel / ERP Code or Paper Description / GSM."
                            )

                    if _fixed_errors:
'''
if validation_anchor not in s:
    raise RuntimeError("Old reel validation anchor not found")
s=s.replace(validation_anchor,validation_new,1)

insert_anchor='''                                    """INSERT INTO production_reel_consumption(
                                       work_date,machine,line_no,reel_reference,paper_grade,
                                       quantity_ton,value_amount,remark,entered_by,updated_at
                                       ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)""",
                                    (
                                        pdate.isoformat(),machine,_line_no,
                                        str(_rr.get("Reel / Reference") or "").strip(),
                                        str(_rr.get("Paper Grade") or "").strip(),
                                        float(_rr.get("Qty Consumed Ton") or 0),
                                        float(_rr.get("Value ₹") or 0),
                                        str(_rr.get("Remark") or "").strip(),
                                        _current_user["username"]
                                    )
'''
insert_new='''                                    """INSERT INTO production_reel_consumption(
                                       work_date,machine,line_no,reel_reference,paper_grade,
                                       opening_wip_ton,reel_issue_ton,reel_return_ton,net_issue_ton,
                                       closing_wip_ton,consumption_ton,quantity_ton,
                                       value_amount,remark,entered_by,updated_at
                                       ) VALUES (
                                       %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP
                                       )""",
                                    (
                                        pdate.isoformat(),machine,_line_no,
                                        str(_rr.get("Reel / Reference") or "").strip(),
                                        str(_rr.get("Paper Grade") or "").strip(),
                                        float(_rr.get("Opening WIP Ton") or 0),
                                        float(_rr.get("Reel Issue Ton") or 0),
                                        float(_rr.get("Reel Return Ton") or 0),
                                        float(_rr.get("Net Issue Ton") or 0),
                                        float(_rr.get("Closing WIP Ton") or 0),
                                        float(_rr.get("Effective Consumption Ton") or 0),
                                        float(_rr.get("Effective Consumption Ton") or 0),
                                        float(_rr.get("Value ₹") or 0),
                                        str(_rr.get("Remark") or "").strip(),
                                        _current_user["username"]
                                    )
'''
if insert_anchor not in s:
    raise RuntimeError("Reel INSERT anchor not found")
s=s.replace(insert_anchor,insert_new,1)

audit_anchor='''                                f"Daily; ReelLines={len(_reel_work)}; PaperConsumed={paper_consumed:.3f}; "
                                f"PaperValue={paper_value:.2f}; AvgRateKg={avg_paper_rate:.2f}; "
'''
audit_new='''                                f"Daily; ReelLines={len(_reel_work)}; OpeningWIP={total_opening_wip:.3f}; "
                                f"ReelIssue={total_reel_issue:.3f}; ReelReturn={total_reel_return:.3f}; "
                                f"NetIssue={total_net_issue:.3f}; ClosingWIP={total_closing_wip:.3f}; "
                                f"PaperConsumed={paper_consumed:.3f}; FlowVariance={total_flow_variance:.3f}; "
                                f"PaperValue={paper_value:.2f}; AvgRateKg={avg_paper_rate:.2f}; "
'''
if audit_anchor not in s:
    raise RuntimeError("Production audit anchor not found")
s=s.replace(audit_anchor,audit_new,1)

# ------------------------------------------------------------------
# 4) Replace Daily MD report with Issue -> Return -> Consumption flow.
# ------------------------------------------------------------------
daily_start=s.find('''    with tab_daily_report:
        st.markdown("### Daily Corrugation Production Report")
''')
daily_end=s.find('''    with tab_monthly:
        st.markdown("### Monthly MD Corrugation Report")
''',daily_start)
if daily_start==-1 or daily_end==-1:
    raise RuntimeError("Daily report boundaries not found")

daily_block=r'''    with tab_daily_report:
        st.markdown("### Daily Corrugation Production Report")
        st.caption(
            "MD material flow: Opening WIP → Reel Issue → Reel Return → Net Issue → Consumption → Closing WIP → Production → Ton/Person."
        )

        _v123_day=st.date_input(
            "Report Date",value=global_work_date,format="DD/MM/YYYY",key="v123_daily_report_date"
        )
        _v123_prod=read_df(
            """SELECT work_date,production_ton,target_ton,waste_ton,breakdown_hours,
                      paper_cost,material_processed_ton,good_output_ton,remark
               FROM production
               WHERE work_date=? AND shift='DAY' AND machine='Corrugation'
               LIMIT 1""",
            (_v123_day.isoformat(),)
        )
        _v123_reels=read_df(
            """SELECT line_no,reel_reference,paper_grade,
                      opening_wip_ton,reel_issue_ton,reel_return_ton,net_issue_ton,
                      closing_wip_ton,consumption_ton,quantity_ton,value_amount,remark
               FROM production_reel_consumption
               WHERE work_date=? AND machine='Corrugation'
               ORDER BY line_no""",
            (_v123_day.isoformat(),)
        )
        _v123_mp=read_df(
            """SELECT shift,COUNT(DISTINCT employee_id) AS people
               FROM manpower_allocation
               WHERE work_date=? AND machine='Corrugation'
               GROUP BY shift ORDER BY shift""",
            (_v123_day.isoformat(),)
        )

        if _v123_prod.empty and _v123_reels.empty:
            st.info(f"No Corrugation data is saved for {_v123_day.strftime('%d/%m/%Y')}.")
        else:
            _v123_pr=_v123_prod.iloc[0].to_dict() if not _v123_prod.empty else {}
            if not _v123_reels.empty:
                for _c in [
                    "opening_wip_ton","reel_issue_ton","reel_return_ton","net_issue_ton",
                    "closing_wip_ton","consumption_ton","quantity_ton","value_amount"
                ]:
                    _v123_reels[_c]=pd.to_numeric(_v123_reels[_c],errors="coerce").fillna(0.0)
                _v123_reels["effective_consumption"]=_v123_reels["consumption_ton"].where(
                    _v123_reels["consumption_ton"]>0,_v123_reels["quantity_ton"]
                )
                _v123_opening=float(_v123_reels["opening_wip_ton"].sum())
                _v123_issue=float(_v123_reels["reel_issue_ton"].sum())
                _v123_return=float(_v123_reels["reel_return_ton"].sum())
                _v123_net=_v123_issue-_v123_return
                _v123_consumption=float(_v123_reels["effective_consumption"].sum())
                _v123_closing=float(_v123_reels["closing_wip_ton"].sum())
                _v123_value=float(_v123_reels["value_amount"].sum())
            else:
                _v123_opening=_v123_issue=_v123_return=_v123_net=_v123_closing=0.0
                _v123_consumption=float(_v123_pr.get("material_processed_ton") or 0)
                _v123_value=float(_v123_pr.get("paper_cost") or 0)

            _v123_expected=_v123_opening+_v123_net-_v123_closing
            _v123_flow_variance=_v123_expected-_v123_consumption
            _v123_avg_rate=(
                _v123_value/(_v123_consumption*1000.0) if _v123_consumption>0 else 0.0
            )
            _v123_output=float(
                _v123_pr.get("good_output_ton") or _v123_pr.get("production_ton") or 0
            )
            _v123_target=float(_v123_pr.get("target_ton") or 0)
            _v123_waste=float(_v123_pr.get("waste_ton") or 0)
            _v123_break=float(_v123_pr.get("breakdown_hours") or 0)
            _v123_achievement=(
                _v123_output/_v123_target*100.0 if _v123_target>0 else 0.0
            )
            _v123_yield=(
                _v123_output/_v123_consumption*100.0 if _v123_consumption>0 else 0.0
            )
            _v123_waste_pct=(
                _v123_waste/_v123_consumption*100.0 if _v123_consumption>0 else 0.0
            )
            _v123_paper_cost_ton=(
                _v123_value/_v123_output if _v123_output>0 else 0.0
            )

            _v123_a=_v123_b=0
            if not _v123_mp.empty:
                for _,_mr in _v123_mp.iterrows():
                    if str(_mr["shift"])=="A":
                        _v123_a=int(_mr["people"] or 0)
                    elif str(_mr["shift"])=="B":
                        _v123_b=int(_mr["people"] or 0)
            _v123_people=_v123_a+_v123_b
            _v123_tpp=(
                _v123_output/_v123_people if _v123_people>0 else 0.0
            )

            st.markdown(f"#### {_v123_day.strftime('%d %B %Y')} · Material Flow")
            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("Opening WIP",f"{_v123_opening:,.3f} T")
            c2.metric("Reel Issue",f"{_v123_issue:,.3f} T")
            c3.metric("Reel Return",f"{_v123_return:,.3f} T")
            c4.metric("Net Issue",f"{_v123_net:,.3f} T")
            c5.metric("Closing WIP",f"{_v123_closing:,.3f} T")

            c1,c2,c3,c4=st.columns(4)
            c1.metric("Actual Consumption",f"{_v123_consumption:,.3f} T")
            c2.metric("Consumption Value",v5_money(_v123_value))
            c3.metric("Avg Paper Rate",f"₹{_v123_avg_rate:,.2f}/Kg")
            c4.metric("Flow Variance",f"{_v123_flow_variance:,.3f} T")

            c1,c2,c3,c4=st.columns(4)
            c1.metric("Good Production",f"{_v123_output:,.2f} T")
            c2.metric("Daily Target",f"{_v123_target:,.2f} T")
            c3.metric("Achievement",f"{_v123_achievement:,.2f}%")
            c4.metric("Paper Cost / Output Ton",v5_money(_v123_paper_cost_ton))

            c1,c2,c3,c4=st.columns(4)
            c1.metric("Waste / Rejection",f"{_v123_waste:,.2f} T")
            c2.metric("Waste %",f"{_v123_waste_pct:,.2f}%")
            c3.metric("Yield",f"{_v123_yield:,.2f}%")
            c4.metric("Breakdown",f"{_v123_break:,.2f} Hrs")

            c1,c2,c3,c4=st.columns(4)
            c1.metric("Shift A Manpower",f"{_v123_a:,}")
            c2.metric("Shift B Manpower",f"{_v123_b:,}")
            c3.metric("Total Person-Shifts",f"{_v123_people:,}")
            c4.metric(
                "Corrugation Ton / Person",
                f"{_v123_tpp:,.2f} T" if _v123_people>0 else "MANPOWER PENDING"
            )

            if abs(_v123_flow_variance)>0.01:
                st.warning(
                    f"Material flow variance is {_v123_flow_variance:.3f} T. "
                    "Review WIP or actual consumption before final management reporting."
                )
            if _v123_people==0:
                st.info("Ton / Person will appear after Corrugation manpower allocation is saved.")

            if not _v123_reels.empty:
                _v123_detail=_v123_reels.rename(columns={
                    "line_no":"Line","reel_reference":"Reel / ERP Code",
                    "paper_grade":"Paper Description / GSM",
                    "opening_wip_ton":"Opening WIP Ton",
                    "reel_issue_ton":"Reel Issue Ton",
                    "reel_return_ton":"Reel Return Ton",
                    "closing_wip_ton":"Closing WIP Ton",
                    "value_amount":"Value ₹","remark":"Remark"
                }).copy()
                _v123_detail["Net Issue Ton"]=(
                    _v123_detail["Reel Issue Ton"]-_v123_detail["Reel Return Ton"]
                )
                _v123_detail["Consumption Ton"]=_v123_reels["effective_consumption"].values
                _v123_detail["Expected Consumption Ton"]=(
                    _v123_detail["Opening WIP Ton"]
                    +_v123_detail["Net Issue Ton"]
                    -_v123_detail["Closing WIP Ton"]
                )
                _v123_detail["Flow Variance Ton"]=(
                    _v123_detail["Expected Consumption Ton"]-_v123_detail["Consumption Ton"]
                )
                _v123_detail["Rate ₹/Kg"]=_v123_detail.apply(
                    lambda r:(
                        float(r["Value ₹"])/(float(r["Consumption Ton"])*1000.0)
                        if float(r["Consumption Ton"])>0 else 0.0
                    ),axis=1
                )
                st.markdown("#### Reel-wise Material Flow")
                st.dataframe(
                    _v123_detail[[
                        "Line","Reel / ERP Code","Paper Description / GSM",
                        "Opening WIP Ton","Reel Issue Ton","Reel Return Ton","Net Issue Ton",
                        "Consumption Ton","Closing WIP Ton","Value ₹","Rate ₹/Kg",
                        "Flow Variance Ton","Remark"
                    ]],
                    hide_index=True,use_container_width=True,
                    column_config={
                        "Opening WIP Ton":st.column_config.NumberColumn(format="%.3f T"),
                        "Reel Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                        "Reel Return Ton":st.column_config.NumberColumn(format="%.3f T"),
                        "Net Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                        "Consumption Ton":st.column_config.NumberColumn(format="%.3f T"),
                        "Closing WIP Ton":st.column_config.NumberColumn(format="%.3f T"),
                        "Value ₹":st.column_config.NumberColumn(format="₹%.2f"),
                        "Rate ₹/Kg":st.column_config.NumberColumn(format="₹%.2f"),
                        "Flow Variance Ton":st.column_config.NumberColumn(format="%.3f T"),
                    }
                )

'''
s=s[:daily_start]+daily_block+s[daily_end:]

# ------------------------------------------------------------------
# 5) Replace monthly MD report with clean issue/return/consumption report.
# ------------------------------------------------------------------
monthly_start=s.find('''    with tab_monthly:
        st.markdown("### Monthly MD Corrugation Report")
''')
monthly_end=s.find('''    with tab_mp:
        c1,c2,c3=st.columns(3)
''',monthly_start)
if monthly_start==-1 or monthly_end==-1:
    raise RuntimeError("Monthly MD report boundaries not found")

monthly_block=r'''    with tab_monthly:
        st.markdown("### Monthly MD Corrugation Report")
        st.caption(
            "Complete monthly material flow and productivity report from this app: "
            "Issue, Return, Consumption, WIP, Production, Waste and Ton/Person."
        )

        _v123_month=st.selectbox(
            "Production Month",_month_opts,
            index=_month_opts.index(global_payroll_month),
            format_func=lambda d:d.strftime("%b %Y"),
            key="v123_monthly_report_month"
        )
        _v123_first,_v123_last=_month_range(_v123_month)

        _v123_prod_month=read_df(
            """SELECT work_date,production_ton,target_ton,waste_ton,breakdown_hours,
                      paper_cost,material_processed_ton,good_output_ton
               FROM production
               WHERE shift='DAY' AND machine='Corrugation'
                 AND work_date BETWEEN ? AND ?
               ORDER BY work_date""",
            (_v123_first.isoformat(),_v123_last.isoformat())
        )
        _v123_reel_rows=read_df(
            """SELECT work_date,line_no,reel_reference,paper_grade,
                      opening_wip_ton,reel_issue_ton,reel_return_ton,net_issue_ton,
                      closing_wip_ton,consumption_ton,quantity_ton,value_amount,remark
               FROM production_reel_consumption
               WHERE machine='Corrugation'
                 AND work_date BETWEEN ? AND ?
               ORDER BY work_date,line_no""",
            (_v123_first.isoformat(),_v123_last.isoformat())
        )
        _v123_mp_month=read_df(
            """SELECT work_date,shift,COUNT(DISTINCT employee_id) AS people
               FROM manpower_allocation
               WHERE machine='Corrugation'
                 AND work_date BETWEEN ? AND ?
               GROUP BY work_date,shift
               ORDER BY work_date,shift""",
            (_v123_first.isoformat(),_v123_last.isoformat())
        )

        if _v123_prod_month.empty and _v123_reel_rows.empty:
            st.info(f"No Corrugation data is saved for {_v123_month.strftime('%B %Y')}.")
        else:
            # Build day-wise reel material flow.
            if not _v123_reel_rows.empty:
                for _c in [
                    "opening_wip_ton","reel_issue_ton","reel_return_ton","net_issue_ton",
                    "closing_wip_ton","consumption_ton","quantity_ton","value_amount"
                ]:
                    _v123_reel_rows[_c]=pd.to_numeric(
                        _v123_reel_rows[_c],errors="coerce"
                    ).fillna(0.0)
                _v123_reel_rows["effective_consumption"]=_v123_reel_rows["consumption_ton"].where(
                    _v123_reel_rows["consumption_ton"]>0,_v123_reel_rows["quantity_ton"]
                )
                _v123_reel_rows["work_date"]=_v123_reel_rows["work_date"].astype(str)
                _v123_reel_day=_v123_reel_rows.groupby("work_date",as_index=False).agg({
                    "opening_wip_ton":"sum",
                    "reel_issue_ton":"sum",
                    "reel_return_ton":"sum",
                    "closing_wip_ton":"sum",
                    "effective_consumption":"sum",
                    "value_amount":"sum",
                })
            else:
                _v123_reel_day=pd.DataFrame(columns=[
                    "work_date","opening_wip_ton","reel_issue_ton","reel_return_ton",
                    "closing_wip_ton","effective_consumption","value_amount"
                ])

            _v123_dates=set()
            if not _v123_prod_month.empty:
                _v123_prod_month["work_date"]=_v123_prod_month["work_date"].astype(str)
                _v123_dates.update(_v123_prod_month["work_date"].tolist())
            if not _v123_reel_day.empty:
                _v123_dates.update(_v123_reel_day["work_date"].tolist())
            _v123_daily=pd.DataFrame({"work_date":sorted(_v123_dates)})

            if not _v123_prod_month.empty:
                _v123_daily=_v123_daily.merge(_v123_prod_month,on="work_date",how="left")
            else:
                for _c in [
                    "production_ton","target_ton","waste_ton","breakdown_hours",
                    "paper_cost","material_processed_ton","good_output_ton"
                ]:
                    _v123_daily[_c]=0.0

            if not _v123_reel_day.empty:
                _v123_daily=_v123_daily.merge(_v123_reel_day,on="work_date",how="left")
            else:
                for _c in [
                    "opening_wip_ton","reel_issue_ton","reel_return_ton",
                    "closing_wip_ton","effective_consumption","value_amount"
                ]:
                    _v123_daily[_c]=0.0

            for _c in [
                "production_ton","target_ton","waste_ton","breakdown_hours",
                "paper_cost","material_processed_ton","good_output_ton",
                "opening_wip_ton","reel_issue_ton","reel_return_ton",
                "closing_wip_ton","effective_consumption","value_amount"
            ]:
                if _c not in _v123_daily.columns:
                    _v123_daily[_c]=0.0
                _v123_daily[_c]=pd.to_numeric(_v123_daily[_c],errors="coerce").fillna(0.0)

            _v123_daily["Opening WIP Ton"]=_v123_daily["opening_wip_ton"]
            _v123_daily["Reel Issue Ton"]=_v123_daily["reel_issue_ton"]
            _v123_daily["Reel Return Ton"]=_v123_daily["reel_return_ton"]
            _v123_daily["Net Issue Ton"]=(
                _v123_daily["Reel Issue Ton"]-_v123_daily["Reel Return Ton"]
            )
            _v123_daily["Closing WIP Ton"]=_v123_daily["closing_wip_ton"]
            _v123_daily["Consumption Ton"]=_v123_daily.apply(
                lambda r:(
                    float(r["effective_consumption"])
                    if float(r["effective_consumption"])>0
                    else float(r["material_processed_ton"])
                ),axis=1
            )
            _v123_daily["Consumption Value"]=_v123_daily.apply(
                lambda r:(
                    float(r["value_amount"])
                    if float(r["value_amount"])>0 else float(r["paper_cost"])
                ),axis=1
            )
            _v123_daily["Expected Consumption Ton"]=(
                _v123_daily["Opening WIP Ton"]
                +_v123_daily["Net Issue Ton"]
                -_v123_daily["Closing WIP Ton"]
            )
            _v123_daily["Flow Variance Ton"]=(
                _v123_daily["Expected Consumption Ton"]-_v123_daily["Consumption Ton"]
            )
            _v123_daily["Production Ton"]=_v123_daily.apply(
                lambda r:(
                    float(r["good_output_ton"])
                    if float(r["good_output_ton"])>0 else float(r["production_ton"])
                ),axis=1
            )
            _v123_daily["Target Ton"]=_v123_daily["target_ton"]
            _v123_daily["Waste Ton"]=_v123_daily["waste_ton"]
            _v123_daily["Breakdown Hrs"]=_v123_daily["breakdown_hours"]
            _v123_daily["Avg Rate ₹/Kg"]=_v123_daily.apply(
                lambda r:(
                    float(r["Consumption Value"])/(float(r["Consumption Ton"])*1000.0)
                    if float(r["Consumption Ton"])>0 else 0.0
                ),axis=1
            )
            _v123_daily["Achievement %"]=_v123_daily.apply(
                lambda r:(
                    float(r["Production Ton"])/float(r["Target Ton"])*100.0
                    if float(r["Target Ton"])>0 else 0.0
                ),axis=1
            )
            _v123_daily["Yield %"]=_v123_daily.apply(
                lambda r:(
                    float(r["Production Ton"])/float(r["Consumption Ton"])*100.0
                    if float(r["Consumption Ton"])>0 else 0.0
                ),axis=1
            )
            _v123_daily["Waste %"]=_v123_daily.apply(
                lambda r:(
                    float(r["Waste Ton"])/float(r["Consumption Ton"])*100.0
                    if float(r["Consumption Ton"])>0 else 0.0
                ),axis=1
            )

            _v123_daily["Shift A Manpower"]=0
            _v123_daily["Shift B Manpower"]=0
            if not _v123_mp_month.empty:
                _v123_mp_month["work_date"]=_v123_mp_month["work_date"].astype(str)
                for _,_mr in _v123_mp_month.iterrows():
                    _mask=_v123_daily["work_date"]==str(_mr["work_date"])
                    if str(_mr["shift"])=="A":
                        _v123_daily.loc[_mask,"Shift A Manpower"]=int(_mr["people"] or 0)
                    elif str(_mr["shift"])=="B":
                        _v123_daily.loc[_mask,"Shift B Manpower"]=int(_mr["people"] or 0)
            _v123_daily["Total Person-Shifts"]=(
                _v123_daily["Shift A Manpower"]+_v123_daily["Shift B Manpower"]
            )
            _v123_daily["Corrugation Ton / Person"]=_v123_daily.apply(
                lambda r:(
                    float(r["Production Ton"])/float(r["Total Person-Shifts"])
                    if float(r["Total Person-Shifts"])>0 else 0.0
                ),axis=1
            )
            _v123_daily["Date"]=pd.to_datetime(
                _v123_daily["work_date"],errors="coerce"
            ).dt.date

            _v123_days=int((_v123_daily["Production Ton"]>0).sum())
            _v123_issue_total=float(_v123_daily["Reel Issue Ton"].sum())
            _v123_return_total=float(_v123_daily["Reel Return Ton"].sum())
            _v123_net_total=_v123_issue_total-_v123_return_total
            _v123_consumption_total=float(_v123_daily["Consumption Ton"].sum())
            _v123_value_total=float(_v123_daily["Consumption Value"].sum())
            _v123_output_total=float(_v123_daily["Production Ton"].sum())
            _v123_target_total=float(_v123_daily["Target Ton"].sum())
            _v123_waste_total=float(_v123_daily["Waste Ton"].sum())
            _v123_break_total=float(_v123_daily["Breakdown Hrs"].sum())
            _v123_people_total=int(_v123_daily["Total Person-Shifts"].sum())
            _v123_avg_rate=(
                _v123_value_total/(_v123_consumption_total*1000.0)
                if _v123_consumption_total>0 else 0.0
            )
            _v123_achievement=(
                _v123_output_total/_v123_target_total*100.0
                if _v123_target_total>0 else 0.0
            )
            _v123_yield=(
                _v123_output_total/_v123_consumption_total*100.0
                if _v123_consumption_total>0 else 0.0
            )
            _v123_waste_pct=(
                _v123_waste_total/_v123_consumption_total*100.0
                if _v123_consumption_total>0 else 0.0
            )
            _v123_tpp=(
                _v123_output_total/_v123_people_total
                if _v123_people_total>0 else 0.0
            )
            _v123_paper_cost_ton=(
                _v123_value_total/_v123_output_total
                if _v123_output_total>0 else 0.0
            )

            # Opening/closing WIP for the month: first/last recorded balance per paper/reel key,
            # not a sum of every day's WIP (which would double-count stock).
            _v123_month_opening=0.0
            _v123_month_closing=0.0
            if not _v123_reel_rows.empty:
                _v123_stock=_v123_reel_rows.copy()
                _v123_stock["stock_key"]=(
                    _v123_stock["reel_reference"].fillna("").astype(str).str.strip()
                    +"|"+_v123_stock["paper_grade"].fillna("").astype(str).str.strip()
                )
                _v123_stock=_v123_stock.sort_values(["stock_key","work_date","line_no"])
                _v123_first_rows=_v123_stock.groupby("stock_key",as_index=False).first()
                _v123_last_rows=_v123_stock.groupby("stock_key",as_index=False).last()
                _v123_month_opening=float(_v123_first_rows["opening_wip_ton"].sum())
                _v123_month_closing=float(_v123_last_rows["closing_wip_ton"].sum())

            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("Opening WIP",f"{_v123_month_opening:,.2f} T")
            c2.metric("Reel Issue",f"{_v123_issue_total:,.2f} T")
            c3.metric("Reel Return",f"{_v123_return_total:,.2f} T")
            c4.metric("Net Issue",f"{_v123_net_total:,.2f} T")
            c5.metric("Closing WIP",f"{_v123_month_closing:,.2f} T")

            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("Consumption",f"{_v123_consumption_total:,.2f} T")
            c2.metric("Consumption Value",v5_money(_v123_value_total))
            c3.metric("Avg Paper Rate",f"₹{_v123_avg_rate:,.2f}/Kg")
            c4.metric("Production",f"{_v123_output_total:,.2f} T")
            c5.metric("Paper Cost / Output Ton",v5_money(_v123_paper_cost_ton))

            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("Production Days",f"{_v123_days:,}")
            c2.metric("Target",f"{_v123_target_total:,.2f} T")
            c3.metric("Achievement",f"{_v123_achievement:,.2f}%")
            c4.metric("Waste %",f"{_v123_waste_pct:,.2f}%")
            c5.metric("Yield",f"{_v123_yield:,.2f}%")

            c1,c2,c3,c4=st.columns(4)
            c1.metric("Waste / Rejection",f"{_v123_waste_total:,.2f} T")
            c2.metric("Breakdown",f"{_v123_break_total:,.2f} Hrs")
            c3.metric("Person-Shifts",f"{_v123_people_total:,}")
            c4.metric(
                "Corrugation Ton / Person",
                f"{_v123_tpp:,.2f} T" if _v123_people_total>0 else "MANPOWER PENDING"
            )
            st.caption(
                "Monthly Ton / Person = Total Corrugation Production ÷ Total Corrugation person-shifts."
            )

            st.markdown("#### Date-wise MD Report")
            _v123_display=_v123_daily[[
                "Date","Opening WIP Ton","Reel Issue Ton","Reel Return Ton","Net Issue Ton",
                "Consumption Ton","Closing WIP Ton","Consumption Value","Avg Rate ₹/Kg",
                "Production Ton","Target Ton","Achievement %","Waste Ton","Waste %",
                "Yield %","Breakdown Hrs","Shift A Manpower","Shift B Manpower",
                "Total Person-Shifts","Corrugation Ton / Person","Flow Variance Ton"
            ]].copy()
            st.dataframe(
                _v123_display,hide_index=True,use_container_width=True,height=500,
                column_config={
                    "Opening WIP Ton":st.column_config.NumberColumn(format="%.3f T"),
                    "Reel Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                    "Reel Return Ton":st.column_config.NumberColumn(format="%.3f T"),
                    "Net Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                    "Consumption Ton":st.column_config.NumberColumn(format="%.3f T"),
                    "Closing WIP Ton":st.column_config.NumberColumn(format="%.3f T"),
                    "Consumption Value":st.column_config.NumberColumn(format="₹%.2f"),
                    "Avg Rate ₹/Kg":st.column_config.NumberColumn(format="₹%.2f"),
                    "Production Ton":st.column_config.NumberColumn(format="%.2f T"),
                    "Target Ton":st.column_config.NumberColumn(format="%.2f T"),
                    "Achievement %":st.column_config.NumberColumn(format="%.2f%%"),
                    "Waste Ton":st.column_config.NumberColumn(format="%.2f T"),
                    "Waste %":st.column_config.NumberColumn(format="%.2f%%"),
                    "Yield %":st.column_config.NumberColumn(format="%.2f%%"),
                    "Breakdown Hrs":st.column_config.NumberColumn(format="%.2f"),
                    "Corrugation Ton / Person":st.column_config.NumberColumn(format="%.2f T"),
                    "Flow Variance Ton":st.column_config.NumberColumn(format="%.3f T"),
                }
            )

            st.markdown("#### MD Trends")
            c1,c2=st.columns(2,gap="small")
            with c1:
                _v123_flow_chart=_v123_daily[[
                    "Date","Reel Issue Ton","Reel Return Ton","Consumption Ton"
                ]].melt("Date",var_name="Series",value_name="Ton")
                chart=alt.Chart(_v123_flow_chart).mark_line(point=True).encode(
                    x=alt.X("Date:T",title="Date"),
                    y=alt.Y("Ton:Q",title="Ton"),
                    color=alt.Color("Series:N",title=""),
                    tooltip=["Date:T","Series:N",alt.Tooltip("Ton:Q",format=".2f")]
                ).properties(height=280,title="Issue / Return / Consumption")
                st.altair_chart(chart,use_container_width=True)
            with c2:
                _v123_prod_chart=_v123_daily[["Date","Production Ton","Target Ton"]].melt(
                    "Date",var_name="Series",value_name="Ton"
                )
                chart=alt.Chart(_v123_prod_chart).mark_line(point=True).encode(
                    x=alt.X("Date:T",title="Date"),
                    y=alt.Y("Ton:Q",title="Ton"),
                    color=alt.Color("Series:N",title=""),
                    tooltip=["Date:T","Series:N",alt.Tooltip("Ton:Q",format=".2f")]
                ).properties(height=280,title="Production vs Target")
                st.altair_chart(chart,use_container_width=True)

            c1,c2=st.columns(2,gap="small")
            with c1:
                chart=alt.Chart(_v123_daily).mark_line(point=True).encode(
                    x=alt.X("Date:T",title="Date"),
                    y=alt.Y("Yield %:Q",title="Yield %"),
                    tooltip=["Date:T",alt.Tooltip("Yield %:Q",format=".2f")]
                ).properties(height=280,title="Yield Trend")
                st.altair_chart(chart,use_container_width=True)
            with c2:
                _v123_tpp_chart=_v123_daily[_v123_daily["Total Person-Shifts"]>0]
                if _v123_tpp_chart.empty:
                    st.info("Ton / Person trend will appear after manpower allocation.")
                else:
                    chart=alt.Chart(_v123_tpp_chart).mark_line(point=True).encode(
                        x=alt.X("Date:T",title="Date"),
                        y=alt.Y("Corrugation Ton / Person:Q",title="Ton / Person"),
                        tooltip=["Date:T",alt.Tooltip("Corrugation Ton / Person:Q",format=".2f")]
                    ).properties(height=280,title="Corrugation Ton / Person")
                    st.altair_chart(chart,use_container_width=True)

            _v123_report_bytes=make_excel_report(
                _v123_display,
                "Corrugation Monthly MD Report",
                f"Greater Noida Plant | {_v123_month.strftime('%b %Y')}"
            )
            st.download_button(
                "Download Monthly Corrugation Report",
                data=_v123_report_bytes,
                file_name=f"Corrugation_MD_Report_{_v123_month.strftime('%Y_%m')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",use_container_width=True,
                key="v123_download_monthly_corrugation"
            )

            with st.expander("View Reel-wise Monthly Material Flow"):
                if _v123_reel_rows.empty:
                    st.info("No reel-level rows are saved for this month.")
                else:
                    _v123_detail=_v123_reel_rows.copy()
                    _v123_detail["Date"]=pd.to_datetime(
                        _v123_detail["work_date"],errors="coerce"
                    ).dt.date
                    _v123_detail["Net Issue Ton"]=(
                        _v123_detail["reel_issue_ton"]-_v123_detail["reel_return_ton"]
                    )
                    _v123_detail["Consumption Ton"]=_v123_detail["effective_consumption"]
                    _v123_detail["Expected Consumption Ton"]=(
                        _v123_detail["opening_wip_ton"]
                        +_v123_detail["Net Issue Ton"]
                        -_v123_detail["closing_wip_ton"]
                    )
                    _v123_detail["Flow Variance Ton"]=(
                        _v123_detail["Expected Consumption Ton"]-_v123_detail["Consumption Ton"]
                    )
                    _v123_detail["Rate ₹/Kg"]=_v123_detail.apply(
                        lambda r:(
                            float(r["value_amount"])/(float(r["Consumption Ton"])*1000.0)
                            if float(r["Consumption Ton"])>0 else 0.0
                        ),axis=1
                    )
                    _v123_detail=_v123_detail.rename(columns={
                        "line_no":"Line","reel_reference":"Reel / ERP Code",
                        "paper_grade":"Paper Description / GSM",
                        "opening_wip_ton":"Opening WIP Ton",
                        "reel_issue_ton":"Reel Issue Ton",
                        "reel_return_ton":"Reel Return Ton",
                        "closing_wip_ton":"Closing WIP Ton",
                        "value_amount":"Value ₹","remark":"Remark"
                    })
                    st.dataframe(
                        _v123_detail[[
                            "Date","Line","Reel / ERP Code","Paper Description / GSM",
                            "Opening WIP Ton","Reel Issue Ton","Reel Return Ton","Net Issue Ton",
                            "Consumption Ton","Closing WIP Ton","Value ₹","Rate ₹/Kg",
                            "Flow Variance Ton","Remark"
                        ]],
                        hide_index=True,use_container_width=True,
                        column_config={
                            "Opening WIP Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Reel Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Reel Return Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Net Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Consumption Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Closing WIP Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Value ₹":st.column_config.NumberColumn(format="₹%.2f"),
                            "Rate ₹/Kg":st.column_config.NumberColumn(format="₹%.2f"),
                            "Flow Variance Ton":st.column_config.NumberColumn(format="%.3f T"),
                        }
                    )

'''
s=s[:monthly_start]+monthly_block+s[monthly_end:]

p.write_text(s,encoding="utf-8")
print("Applied V12.3 reel issue/return/consumption reporting")
