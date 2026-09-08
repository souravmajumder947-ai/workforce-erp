from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
MARK="# V12.8 SIMPLE PRODUCTION REPORTS"
if MARK in s:
    print("V12.8 already applied")
    raise SystemExit(0)

# ------------------------------------------------------------------
# 1) Simplify Corrugation reel entry: no WIP, no flow-variance concepts.
# ------------------------------------------------------------------
start=s.find('''                _reels_existing = read_df(
''')
end=s.find('''                _existing_good=float(er.get("good_output_ton") or er.get("production_ton") or 0)
''', start)
if start==-1 or end==-1:
    raise RuntimeError("Corrugation reel entry block not found")

simple_reel=r'''                # V12.8 SIMPLE PRODUCTION REPORTS
                _reels_existing = read_df(
                    """SELECT line_no,reel_reference,paper_grade,
                              reel_issue_ton,reel_return_ton,consumption_ton,
                              quantity_ton,value_amount,remark
                       FROM production_reel_consumption
                       WHERE work_date=? AND machine=?
                       ORDER BY line_no""",
                    (pdate.isoformat(),machine)
                )

                if _reels_existing.empty:
                    _legacy_qty=float(er.get("material_processed_ton") or 0)
                    _legacy_value=float(er.get("paper_cost") or 0)
                    _reel_seed=pd.DataFrame([{
                        "Reel / ERP Code":"",
                        "Paper Description / GSM":"",
                        "Reel Issue Ton":0.0,
                        "Reel Return Ton":0.0,
                        "Actual Consumption Ton":_legacy_qty,
                        "Consumption Value ₹":_legacy_value,
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
                        "reel_reference":"Reel / ERP Code",
                        "paper_grade":"Paper Description / GSM",
                        "reel_issue_ton":"Reel Issue Ton",
                        "reel_return_ton":"Reel Return Ton",
                        "consumption_ton":"Actual Consumption Ton",
                        "value_amount":"Consumption Value ₹",
                        "remark":"Remark"
                    })[[
                        "Reel / ERP Code","Paper Description / GSM",
                        "Reel Issue Ton","Reel Return Ton",
                        "Actual Consumption Ton","Consumption Value ₹","Remark"
                    ]].copy()

                st.markdown("#### Reel Issue / Return / Consumption")
                st.caption(
                    "Keep it simple: enter Issue, Return and actual Consumption. "
                    "Net Issue = Issue − Return. Consumption is never assumed from Net Issue."
                )
                reel_editor=st.data_editor(
                    _reel_seed,
                    hide_index=True,use_container_width=True,num_rows="dynamic",
                    key=f"v128_reel_editor_{pdate.isoformat()}_{machine}",
                    column_config={
                        "Reel / ERP Code":st.column_config.TextColumn("Reel / ERP Code"),
                        "Paper Description / GSM":st.column_config.TextColumn("Paper Description / GSM"),
                        "Reel Issue Ton":st.column_config.NumberColumn(
                            "Reel Issue Ton",min_value=0.0,step=0.001,format="%.3f"
                        ),
                        "Reel Return Ton":st.column_config.NumberColumn(
                            "Reel Return Ton",min_value=0.0,step=0.001,format="%.3f"
                        ),
                        "Actual Consumption Ton":st.column_config.NumberColumn(
                            "Actual Consumption Ton",min_value=0.0,step=0.001,format="%.3f"
                        ),
                        "Consumption Value ₹":st.column_config.NumberColumn(
                            "Consumption Value ₹",min_value=0.0,step=1.0,format="₹%.2f"
                        ),
                        "Remark":st.column_config.TextColumn("Remark"),
                    }
                )

                _reel_work=reel_editor.copy()
                for _c in [
                    "Reel Issue Ton","Reel Return Ton",
                    "Actual Consumption Ton","Consumption Value ₹"
                ]:
                    _reel_work[_c]=pd.to_numeric(_reel_work[_c],errors="coerce").fillna(0.0)

                _reel_work=_reel_work[
                    (_reel_work["Reel Issue Ton"]>0)
                    | (_reel_work["Reel Return Ton"]>0)
                    | (_reel_work["Actual Consumption Ton"]>0)
                    | (_reel_work["Consumption Value ₹"]>0)
                    | (_reel_work["Reel / ERP Code"].fillna("").astype(str).str.strip()!="")
                    | (_reel_work["Paper Description / GSM"].fillna("").astype(str).str.strip()!="")
                ].copy()

                if not _reel_work.empty:
                    _reel_work["Net Issue Ton"]=(
                        _reel_work["Reel Issue Ton"]-_reel_work["Reel Return Ton"]
                    )
                    _reel_work["Effective Consumption Ton"]=_reel_work["Actual Consumption Ton"]
                    _reel_work["Value ₹"]=_reel_work["Consumption Value ₹"]
                    _reel_work["Rate ₹/Kg"]=_reel_work.apply(
                        lambda r:(
                            float(r["Consumption Value ₹"])/
                            (float(r["Actual Consumption Ton"])*1000.0)
                            if float(r["Actual Consumption Ton"])>0 else 0.0
                        ),axis=1
                    )
                else:
                    for _c in [
                        "Net Issue Ton","Effective Consumption Ton","Value ₹","Rate ₹/Kg"
                    ]:
                        _reel_work[_c]=pd.Series(dtype=float)

                # Compatibility columns for existing save logic; no WIP is used.
                _reel_work["Reel / Reference"]=_reel_work.get("Reel / ERP Code","")
                _reel_work["Paper Grade"]=_reel_work.get("Paper Description / GSM","")
                _reel_work["Opening WIP Ton"]=0.0
                _reel_work["Closing WIP Ton"]=0.0
                _reel_work["Expected Consumption Ton"]=0.0
                _reel_work["Flow Variance Ton"]=0.0

                paper_consumed=float(
                    _reel_work["Actual Consumption Ton"].sum()
                ) if not _reel_work.empty else 0.0
                paper_value=float(
                    _reel_work["Consumption Value ₹"].sum()
                ) if not _reel_work.empty else 0.0
                total_reel_issue=float(
                    _reel_work["Reel Issue Ton"].sum()
                ) if not _reel_work.empty else 0.0
                total_reel_return=float(
                    _reel_work["Reel Return Ton"].sum()
                ) if not _reel_work.empty else 0.0
                total_net_issue=total_reel_issue-total_reel_return
                total_opening_wip=0.0
                total_closing_wip=0.0
                total_expected_consumption=0.0
                total_flow_variance=0.0
                avg_paper_rate=(
                    paper_value/(paper_consumed*1000.0)
                    if paper_consumed>0 else 0.0
                )
                _reel_flow_errors=[]

                k1,k2,k3,k4=st.columns(4)
                k1.metric("Reel Issue",f"{total_reel_issue:.3f} T")
                k2.metric("Reel Return",f"{total_reel_return:.3f} T")
                k3.metric("Net Issue",f"{total_net_issue:.3f} T")
                k4.metric(
                    "Actual Consumption",
                    f"{paper_consumed:.3f} T" if paper_consumed>0 else "PENDING"
                )

                if not _reel_work.empty:
                    st.dataframe(
                        _reel_work[[
                            "Reel / ERP Code","Paper Description / GSM",
                            "Reel Issue Ton","Reel Return Ton","Net Issue Ton",
                            "Actual Consumption Ton","Consumption Value ₹","Rate ₹/Kg","Remark"
                        ]],
                        hide_index=True,use_container_width=True,
                        column_config={
                            "Reel Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Reel Return Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Net Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Actual Consumption Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Consumption Value ₹":st.column_config.NumberColumn(format="₹%.2f"),
                            "Rate ₹/Kg":st.column_config.NumberColumn(format="₹%.2f"),
                        }
                    )

'''
s=s[:start]+simple_reel+s[end:]

# Allow production to be saved even when consumption is pending.
old='''                    if (good_output>0 or waste_ton>0) and paper_consumed<=0:
                        _fixed_errors.append(
                            "Add reel / paper consumption before saving production output."
                        )
'''
if old in s:
    s=s.replace(old,'',1)

old='''                    if (not _is_finsys_history) and good_output+waste_ton > paper_consumed + 0.01:
                        _fixed_errors.append(
                            "Good Output + Waste/Rejection cannot be greater than total Reel Consumption."
                        )
'''
new='''                    if (
                        paper_consumed>0
                        and (not _is_finsys_history)
                        and good_output+waste_ton > paper_consumed + 0.01
                    ):
                        _fixed_errors.append(
                            "Good Output + Waste/Rejection cannot be greater than Actual Consumption."
                        )
'''
if old in s:
    s=s.replace(old,new,1)

# ------------------------------------------------------------------
# 2) Replace Daily Report with a simple, conditional MD view.
# ------------------------------------------------------------------
daily_start=s.find('''    with tab_daily_report:
        st.markdown("### Daily Corrugation Production Report")
''')
daily_end=s.find('''    with tab_monthly:
        st.markdown("### Monthly MD Corrugation Report")
''', daily_start)
if daily_start==-1 or daily_end==-1:
    raise RuntimeError("Daily report block not found")

daily=r'''    with tab_daily_report:
        st.markdown("### Daily Corrugation Report")
        _v128_day=global_work_date
        st.caption(f"Date: {_v128_day.strftime('%d/%m/%Y')} · controlled by sidebar Working Date")

        _v128_move=read_df(
            """SELECT movement_type,
                      SUM(quantity_ton) AS qty_ton,
                      SUM(movement_value) AS movement_value
               FROM production_reel_transactions
               WHERE work_date=?
               GROUP BY movement_type""",
            (_v128_day.isoformat(),)
        )
        _v128_prod=read_df(
            """SELECT production_ton,target_ton,waste_ton,breakdown_hours,
                      paper_cost,material_processed_ton,good_output_ton
               FROM production
               WHERE work_date=? AND shift='DAY' AND machine='Corrugation'
               LIMIT 1""",
            (_v128_day.isoformat(),)
        )
        _v128_mp=read_df(
            """SELECT shift,COUNT(DISTINCT employee_id) AS people
               FROM manpower_allocation
               WHERE work_date=? AND machine='Corrugation'
               GROUP BY shift""",
            (_v128_day.isoformat(),)
        )

        _issue=_return=_issue_value=_return_value=0.0
        if not _v128_move.empty:
            for _,_r in _v128_move.iterrows():
                if str(_r["movement_type"])=="ISSUE":
                    _issue=float(_r["qty_ton"] or 0)
                    _issue_value=float(_r["movement_value"] or 0)
                elif str(_r["movement_type"])=="RETURN":
                    _return=float(_r["qty_ton"] or 0)
                    _return_value=float(_r["movement_value"] or 0)
        _net=_issue-_return
        _net_value=_issue_value-_return_value

        _pr=_v128_prod.iloc[0].to_dict() if not _v128_prod.empty else {}
        _cons=float(_pr.get("material_processed_ton") or 0)
        _cons_value=float(_pr.get("paper_cost") or 0)
        _output=float(_pr.get("good_output_ton") or _pr.get("production_ton") or 0)
        _target=float(_pr.get("target_ton") or 0)
        _waste=float(_pr.get("waste_ton") or 0)
        _break=float(_pr.get("breakdown_hours") or 0)
        _achievement=(_output/_target*100.0) if _target>0 else 0.0
        _yield=(_output/_cons*100.0) if _cons>0 else 0.0
        _waste_pct=(_waste/_cons*100.0) if _cons>0 else 0.0
        _avg_rate=(_cons_value/(_cons*1000.0)) if _cons>0 else 0.0

        _a=_b=0
        if not _v128_mp.empty:
            for _,_r in _v128_mp.iterrows():
                if str(_r["shift"])=="A": _a=int(_r["people"] or 0)
                elif str(_r["shift"])=="B": _b=int(_r["people"] or 0)
        _people=_a+_b
        _tpp=(_output/_people) if _people>0 else 0.0

        if _issue<=0 and _return<=0 and _output<=0 and _cons<=0:
            st.info(f"No Corrugation data is saved for {_v128_day.strftime('%d/%m/%Y')}.")
        else:
            st.markdown("#### 1. Reel Movement")
            c1,c2,c3=st.columns(3)
            c1.metric("Reel Issue",f"{_issue:,.3f} T")
            c2.metric("Reel Return",f"{_return:,.3f} T")
            c3.metric("Net Issue",f"{_net:,.3f} T")

            c1,c2,c3=st.columns(3)
            c1.metric("Issue Value",v5_money(_issue_value))
            c2.metric("Return Value",v5_money(_return_value))
            c3.metric("Net Issue Value",v5_money(_net_value))

            if _cons>0:
                st.markdown("#### 2. Consumption")
                c1,c2,c3=st.columns(3)
                c1.metric("Actual Consumption",f"{_cons:,.3f} T")
                c2.metric("Consumption Value",v5_money(_cons_value))
                c3.metric("Avg Paper Rate",f"₹{_avg_rate:,.2f}/Kg")
            else:
                st.info("Actual Consumption has not been entered yet.")

            if _output>0 or _target>0 or _waste>0 or _break>0:
                st.markdown("#### 3. Production")
                c1,c2,c3,c4=st.columns(4)
                c1.metric("Good Production",f"{_output:,.2f} T")
                c2.metric("Target",f"{_target:,.2f} T")
                c3.metric("Achievement",f"{_achievement:,.2f}%")
                c4.metric("Breakdown",f"{_break:,.2f} Hrs")

                c1,c2,c3=st.columns(3)
                c1.metric("Waste / Rejection",f"{_waste:,.2f} T")
                c2.metric("Waste %",f"{_waste_pct:,.2f}%" if _cons>0 else "PENDING")
                c3.metric("Yield",f"{_yield:,.2f}%" if _cons>0 else "PENDING")
            else:
                st.info("Production data has not been entered for this date.")

            if _people>0:
                st.markdown("#### 4. Manpower Productivity")
                c1,c2,c3,c4=st.columns(4)
                c1.metric("Shift A",f"{_a:,}")
                c2.metric("Shift B",f"{_b:,}")
                c3.metric("Total Person-Shifts",f"{_people:,}")
                c4.metric("Corrugation Ton / Person",f"{_tpp:,.2f} T")
            else:
                st.info("Corrugation manpower allocation has not been entered for this date.")

'''
s=s[:daily_start]+daily+s[daily_end:]

# ------------------------------------------------------------------
# 3) Replace Monthly Report with a compact management summary.
# ------------------------------------------------------------------
monthly_start=s.find('''    with tab_monthly:
        st.markdown("### Monthly MD Corrugation Report")
''')
monthly_end=s.find('''    with tab_mp:
        c1,c2,c3=st.columns(3)
''', monthly_start)
if monthly_start==-1 or monthly_end==-1:
    raise RuntimeError("Monthly report block not found")

monthly=r'''    with tab_monthly:
        st.markdown("### Monthly Corrugation Report")
        _v128_default_month=date(global_work_date.year,global_work_date.month,1)
        _v128_default_month=(
            _v128_default_month if _v128_default_month in _month_opts else _month_opts[-1]
        )
        _v128_month=st.selectbox(
            "Production Month",_month_opts,
            index=_month_opts.index(_v128_default_month),
            format_func=lambda d:d.strftime("%b %Y"),
            key="v128_month"
        )
        _v128_first,_v128_last=_month_range(_v128_month)
        st.caption(f"Reporting period: {_v128_month.strftime('%B %Y')}")

        _mov=read_df(
            """SELECT work_date,
                      SUM(CASE WHEN movement_type='ISSUE' THEN quantity_ton ELSE 0 END) AS issue_ton,
                      SUM(CASE WHEN movement_type='RETURN' THEN quantity_ton ELSE 0 END) AS return_ton,
                      SUM(CASE WHEN movement_type='ISSUE' THEN movement_value ELSE 0 END) AS issue_value,
                      SUM(CASE WHEN movement_type='RETURN' THEN movement_value ELSE 0 END) AS return_value
               FROM production_reel_transactions
               WHERE work_date BETWEEN ? AND ?
               GROUP BY work_date ORDER BY work_date""",
            (_v128_first.isoformat(),_v128_last.isoformat())
        )
        _prod=read_df(
            """SELECT work_date,production_ton,target_ton,waste_ton,breakdown_hours,
                      paper_cost,material_processed_ton,good_output_ton
               FROM production
               WHERE shift='DAY' AND machine='Corrugation'
                 AND work_date BETWEEN ? AND ?
               ORDER BY work_date""",
            (_v128_first.isoformat(),_v128_last.isoformat())
        )
        _mp=read_df(
            """SELECT work_date,shift,COUNT(DISTINCT employee_id) AS people
               FROM manpower_allocation
               WHERE machine='Corrugation'
                 AND work_date BETWEEN ? AND ?
               GROUP BY work_date,shift""",
            (_v128_first.isoformat(),_v128_last.isoformat())
        )

        _dates=set()
        if not _mov.empty:
            _mov["work_date"]=_mov["work_date"].astype(str); _dates.update(_mov["work_date"].tolist())
        if not _prod.empty:
            _prod["work_date"]=_prod["work_date"].astype(str); _dates.update(_prod["work_date"].tolist())
        if not _mp.empty:
            _mp["work_date"]=_mp["work_date"].astype(str); _dates.update(_mp["work_date"].tolist())

        if not _dates:
            st.info(f"No Corrugation data is available for {_v128_month.strftime('%B %Y')}.")
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

            _d["Reel Issue Ton"]=_d["issue_ton"]
            _d["Reel Return Ton"]=_d["return_ton"]
            _d["Net Issue Ton"]=_d["Reel Issue Ton"]-_d["Reel Return Ton"]
            _d["Issue Value"]=_d["issue_value"]
            _d["Return Value"]=_d["return_value"]
            _d["Net Issue Value"]=_d["Issue Value"]-_d["Return Value"]
            _d["Consumption Ton"]=_d["material_processed_ton"]
            _d["Consumption Value"]=_d["paper_cost"]
            _d["Production Ton"]=_d.apply(
                lambda r:float(r["good_output_ton"]) if float(r["good_output_ton"])>0 else float(r["production_ton"]),
                axis=1
            )
            _d["Target Ton"]=_d["target_ton"]
            _d["Waste Ton"]=_d["waste_ton"]
            _d["Breakdown Hrs"]=_d["breakdown_hours"]
            _d["Achievement %"]=_d.apply(
                lambda r:(float(r["Production Ton"])/float(r["Target Ton"])*100.0) if float(r["Target Ton"])>0 else 0.0,
                axis=1
            )
            _d["Yield %"]=_d.apply(
                lambda r:(float(r["Production Ton"])/float(r["Consumption Ton"])*100.0) if float(r["Consumption Ton"])>0 else 0.0,
                axis=1
            )
            _d["Waste %"]=_d.apply(
                lambda r:(float(r["Waste Ton"])/float(r["Consumption Ton"])*100.0) if float(r["Consumption Ton"])>0 else 0.0,
                axis=1
            )
            _d["Shift A"]=0; _d["Shift B"]=0
            if not _mp.empty:
                for _,_r in _mp.iterrows():
                    _mask=_d["work_date"]==str(_r["work_date"])
                    if str(_r["shift"])=="A": _d.loc[_mask,"Shift A"]=int(_r["people"] or 0)
                    elif str(_r["shift"])=="B": _d.loc[_mask,"Shift B"]=int(_r["people"] or 0)
            _d["Total Manpower"]=_d["Shift A"]+_d["Shift B"]
            _d["Ton / Person"]=_d.apply(
                lambda r:(float(r["Production Ton"])/float(r["Total Manpower"])) if float(r["Total Manpower"])>0 else 0.0,
                axis=1
            )
            _d["Date"]=pd.to_datetime(_d["work_date"],errors="coerce").dt.date

            _issue=float(_d["Reel Issue Ton"].sum())
            _return=float(_d["Reel Return Ton"].sum())
            _net=_issue-_return
            _issue_val=float(_d["Issue Value"].sum())
            _return_val=float(_d["Return Value"].sum())
            _net_val=_issue_val-_return_val
            _cons=float(_d["Consumption Ton"].sum())
            _cons_val=float(_d["Consumption Value"].sum())
            _output=float(_d["Production Ton"].sum())
            _target=float(_d["Target Ton"].sum())
            _waste=float(_d["Waste Ton"].sum())
            _break=float(_d["Breakdown Hrs"].sum())
            _people=int(_d["Total Manpower"].sum())
            _ach=(_output/_target*100.0) if _target>0 else 0.0
            _yield=(_output/_cons*100.0) if _cons>0 else 0.0
            _waste_pct=(_waste/_cons*100.0) if _cons>0 else 0.0
            _avg_rate=(_cons_val/(_cons*1000.0)) if _cons>0 else 0.0
            _tpp=(_output/_people) if _people>0 else 0.0

            st.markdown("#### Reel Movement")
            c1,c2,c3=st.columns(3)
            c1.metric("Total Reel Issue",f"{_issue:,.3f} T")
            c2.metric("Total Reel Return",f"{_return:,.3f} T")
            c3.metric("Net Issue",f"{_net:,.3f} T")
            c1,c2,c3=st.columns(3)
            c1.metric("Issue Value",v5_money(_issue_val))
            c2.metric("Return Value",v5_money(_return_val))
            c3.metric("Net Issue Value",v5_money(_net_val))

            if _cons>0:
                st.markdown("#### Consumption")
                c1,c2,c3=st.columns(3)
                c1.metric("Actual Consumption",f"{_cons:,.3f} T")
                c2.metric("Consumption Value",v5_money(_cons_val))
                c3.metric("Avg Paper Rate",f"₹{_avg_rate:,.2f}/Kg")

            if _output>0 or _target>0:
                st.markdown("#### Production")
                c1,c2,c3,c4=st.columns(4)
                c1.metric("Production",f"{_output:,.2f} T")
                c2.metric("Target",f"{_target:,.2f} T")
                c3.metric("Achievement",f"{_ach:,.2f}%")
                c4.metric("Breakdown",f"{_break:,.2f} Hrs")
                c1,c2,c3=st.columns(3)
                c1.metric("Waste",f"{_waste:,.2f} T")
                c2.metric("Waste %",f"{_waste_pct:,.2f}%" if _cons>0 else "PENDING")
                c3.metric("Yield",f"{_yield:,.2f}%" if _cons>0 else "PENDING")

            if _people>0:
                st.markdown("#### Manpower Productivity")
                c1,c2=st.columns(2)
                c1.metric("Total Person-Shifts",f"{_people:,}")
                c2.metric("Corrugation Ton / Person",f"{_tpp:,.2f} T")

            st.markdown("#### Date-wise Summary")
            _cols=[
                "Date","Reel Issue Ton","Reel Return Ton","Net Issue Ton",
                "Issue Value","Return Value","Net Issue Value"
            ]
            if _cons>0: _cols+=["Consumption Ton","Consumption Value"]
            if _output>0 or _target>0: _cols+=["Production Ton","Target Ton","Achievement %","Waste Ton"]
            if _people>0: _cols+=["Total Manpower","Ton / Person"]
            _display=_d[_cols].copy()
            st.dataframe(
                _display,hide_index=True,use_container_width=True,height=500,
                column_config={
                    "Reel Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                    "Reel Return Ton":st.column_config.NumberColumn(format="%.3f T"),
                    "Net Issue Ton":st.column_config.NumberColumn(format="%.3f T"),
                    "Issue Value":st.column_config.NumberColumn(format="₹%.2f"),
                    "Return Value":st.column_config.NumberColumn(format="₹%.2f"),
                    "Net Issue Value":st.column_config.NumberColumn(format="₹%.2f"),
                    "Consumption Ton":st.column_config.NumberColumn(format="%.3f T"),
                    "Consumption Value":st.column_config.NumberColumn(format="₹%.2f"),
                    "Production Ton":st.column_config.NumberColumn(format="%.2f T"),
                    "Target Ton":st.column_config.NumberColumn(format="%.2f T"),
                    "Achievement %":st.column_config.NumberColumn(format="%.2f%%"),
                    "Waste Ton":st.column_config.NumberColumn(format="%.2f T"),
                    "Ton / Person":st.column_config.NumberColumn(format="%.2f T"),
                }
            )

            _bytes=make_excel_report(
                _display,
                "Corrugation Monthly Report",
                f"Greater Noida Plant | {_v128_month.strftime('%b %Y')}"
            )
            st.download_button(
                "Download Monthly Corrugation Report",
                data=_bytes,
                file_name=f"Corrugation_Report_{_v128_month.strftime('%Y_%m')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",use_container_width=True,
                key="v128_download_monthly"
            )

'''
s=s[:monthly_start]+monthly+s[monthly_end:]

p.write_text(s,encoding="utf-8")
print("Applied V12.8 simplified Corrugation entry and reports")
