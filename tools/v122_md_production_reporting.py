from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
MARK="# V12.2 MD PRODUCTION REPORTING MODEL"
if MARK in s:
    print("V12.2 already applied")
    raise SystemExit(0)

old_tabs='''    # V12.0 MONTHLY PRODUCTION SUMMARY
    tab_prod,tab_monthly,tab_mp=st.tabs([
        "Production Entry","Monthly Production Summary","Manpower Allocation"
    ])

    st.caption(
        "The previously imported August 2026 Finsys production report was removed because the source report was confirmed incorrect. "
        "Manual/live production entries are preserved."
    )
'''
new_tabs='''    # V12.2 MD PRODUCTION REPORTING MODEL
    tab_prod,tab_daily_report,tab_monthly,tab_mp=st.tabs([
        "Production Entry","Daily Production Report","Monthly MD Report","Manpower Allocation"
    ])

    st.caption(
        "Production reports below use only data saved in this application: reel consumption, daily production and manpower allocation."
    )
'''
if old_tabs not in s:
    raise RuntimeError("Operations tabs anchor not found")
s=s.replace(old_tabs,new_tabs,1)

# Improve reel-entry labels for the user's actual operating data.
s=s.replace(
    '"Reel / Reference":st.column_config.TextColumn("Reel / Reference"),',
    '"Reel / Reference":st.column_config.TextColumn("Reel / ERP Code"),',
    1
)
s=s.replace(
    '"Paper Grade":st.column_config.TextColumn("Paper Grade / GSM"),',
    '"Paper Grade":st.column_config.TextColumn("Paper Description / GSM"),',
    1
)

# Add live reel-rate detail preview after overall average rate calculation.
rate_anchor='''                avg_paper_rate=(
                    paper_value/(paper_consumed*1000.0)
                    if paper_consumed>0 else 0.0
                )

                _existing_good=float(er.get("good_output_ton") or er.get("production_ton") or 0)
'''
rate_insert='''                avg_paper_rate=(
                    paper_value/(paper_consumed*1000.0)
                    if paper_consumed>0 else 0.0
                )

                if not _reel_work.empty:
                    _reel_preview=_reel_work.copy()
                    _reel_preview["Rate ₹/Kg"]=_reel_preview.apply(
                        lambda r:(
                            float(r["Value ₹"])/(float(r["Qty Consumed Ton"])*1000.0)
                            if float(r["Qty Consumed Ton"] or 0)>0 else 0.0
                        ),
                        axis=1
                    )
                    st.caption("Live reel calculation — Rate is calculated automatically from Value ÷ Quantity.")
                    st.dataframe(
                        _reel_preview[[
                            "Reel / Reference","Paper Grade","Qty Consumed Ton","Value ₹","Rate ₹/Kg","Remark"
                        ]],
                        hide_index=True,use_container_width=True,
                        column_config={
                            "Reel / Reference":st.column_config.TextColumn("Reel / ERP Code"),
                            "Paper Grade":st.column_config.TextColumn("Paper Description / GSM"),
                            "Qty Consumed Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Value ₹":st.column_config.NumberColumn(format="₹%.2f"),
                            "Rate ₹/Kg":st.column_config.NumberColumn(format="₹%.2f"),
                        }
                    )

                _existing_good=float(er.get("good_output_ton") or er.get("production_ton") or 0)
'''
if rate_anchor not in s:
    raise RuntimeError("Reel rate anchor not found")
s=s.replace(rate_anchor,rate_insert,1)

# Replace the old monthly block with a daily MD report + simple monthly MD report.
start=s.find('''    with tab_monthly:
        st.markdown("### Monthly Production Summary")
''')
end=s.find('''    with tab_mp:
        c1,c2,c3=st.columns(3)
''', start)
if start == -1 or end == -1:
    raise RuntimeError("Monthly report block boundaries not found")

report_block=r'''    with tab_daily_report:
        st.markdown("### Daily Corrugation Production Report")
        st.caption(
            "Simple management view: reel consumption + production + manpower = Corrugation Ton per Person."
        )

        _v122_day=st.date_input(
            "Report Date",value=global_work_date,format="DD/MM/YYYY",key="v122_daily_report_date"
        )

        _v122_prod=read_df(
            """SELECT work_date,production_ton,target_ton,waste_ton,breakdown_hours,
                      paper_cost,material_processed_ton,good_output_ton,remark
               FROM production
               WHERE work_date=? AND shift='DAY' AND machine='Corrugation'
               LIMIT 1""",
            (_v122_day.isoformat(),)
        )
        _v122_reels=read_df(
            """SELECT line_no,reel_reference,paper_grade,quantity_ton,value_amount,remark
               FROM production_reel_consumption
               WHERE work_date=? AND machine='Corrugation'
               ORDER BY line_no""",
            (_v122_day.isoformat(),)
        )
        _v122_mp=read_df(
            """SELECT shift,COUNT(DISTINCT employee_id) AS people
               FROM manpower_allocation
               WHERE work_date=? AND machine='Corrugation'
               GROUP BY shift ORDER BY shift""",
            (_v122_day.isoformat(),)
        )

        if _v122_prod.empty and _v122_reels.empty:
            st.info(
                f"No Corrugation production/reel data is saved for {_v122_day.strftime('%d/%m/%Y')}."
            )
        else:
            _v122_pr=_v122_prod.iloc[0].to_dict() if not _v122_prod.empty else {}
            _v122_reel_qty=(
                float(pd.to_numeric(_v122_reels["quantity_ton"],errors="coerce").fillna(0).sum())
                if not _v122_reels.empty else float(_v122_pr.get("material_processed_ton") or 0)
            )
            _v122_reel_value=(
                float(pd.to_numeric(_v122_reels["value_amount"],errors="coerce").fillna(0).sum())
                if not _v122_reels.empty else float(_v122_pr.get("paper_cost") or 0)
            )
            _v122_avg_rate=(
                _v122_reel_value/(_v122_reel_qty*1000.0)
                if _v122_reel_qty>0 else 0.0
            )
            _v122_output=float(
                _v122_pr.get("good_output_ton") or _v122_pr.get("production_ton") or 0
            )
            _v122_target=float(_v122_pr.get("target_ton") or 0)
            _v122_waste=float(_v122_pr.get("waste_ton") or 0)
            _v122_break=float(_v122_pr.get("breakdown_hours") or 0)
            _v122_achievement=(
                _v122_output/_v122_target*100.0 if _v122_target>0 else 0.0
            )
            _v122_yield=(
                _v122_output/_v122_reel_qty*100.0 if _v122_reel_qty>0 else 0.0
            )
            _v122_waste_pct=(
                _v122_waste/_v122_reel_qty*100.0 if _v122_reel_qty>0 else 0.0
            )
            _v122_paper_cost_ton=(
                _v122_reel_value/_v122_output if _v122_output>0 else 0.0
            )

            _v122_a=0
            _v122_b=0
            if not _v122_mp.empty:
                for _,_mr in _v122_mp.iterrows():
                    if str(_mr["shift"])=="A":
                        _v122_a=int(_mr["people"] or 0)
                    elif str(_mr["shift"])=="B":
                        _v122_b=int(_mr["people"] or 0)
            _v122_people=_v122_a+_v122_b
            _v122_tpp=(
                _v122_output/_v122_people if _v122_people>0 else 0.0
            )

            st.markdown(f"#### {_v122_day.strftime('%d %B %Y')} · Corrugation")
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Reel Consumption",f"{_v122_reel_qty:,.3f} T")
            c2.metric("Reel Value",v5_money(_v122_reel_value))
            c3.metric("Avg Paper Rate",f"₹{_v122_avg_rate:,.2f}/Kg")
            c4.metric("Paper Cost / Output Ton",v5_money(_v122_paper_cost_ton))

            c1,c2,c3,c4=st.columns(4)
            c1.metric("Good Production",f"{_v122_output:,.2f} T")
            c2.metric("Daily Target",f"{_v122_target:,.2f} T")
            c3.metric("Achievement",f"{_v122_achievement:,.2f}%")
            c4.metric("Breakdown",f"{_v122_break:,.2f} Hrs")

            c1,c2,c3,c4=st.columns(4)
            c1.metric("Waste / Rejection",f"{_v122_waste:,.2f} T")
            c2.metric("Waste %",f"{_v122_waste_pct:,.2f}%")
            c3.metric("Yield",f"{_v122_yield:,.2f}%")
            c4.metric(
                "Corrugation Ton / Person",
                f"{_v122_tpp:,.2f} T" if _v122_people>0 else "MANPOWER PENDING"
            )

            st.markdown("#### Corrugation Manpower")
            m1,m2,m3=st.columns(3)
            m1.metric("Shift A",f"{_v122_a:,}")
            m2.metric("Shift B",f"{_v122_b:,}")
            m3.metric("Total Person-Shifts",f"{_v122_people:,}")
            st.caption(
                "Corrugation Ton / Person = Daily Good Production Ton ÷ Corrugation person-shifts allocated for Shift A + Shift B."
            )
            if _v122_people==0:
                st.warning(
                    "No Corrugation manpower allocation is saved for this date. "
                    "Ton / Person will appear after manpower is allocated."
                )

            if not _v122_reels.empty:
                _v122_reel_display=_v122_reels.rename(columns={
                    "line_no":"Line",
                    "reel_reference":"Reel / ERP Code",
                    "paper_grade":"Paper Description / GSM",
                    "quantity_ton":"Qty Ton",
                    "value_amount":"Value ₹",
                    "remark":"Remark"
                }).copy()
                _v122_reel_display["Rate ₹/Kg"]=_v122_reel_display.apply(
                    lambda r:(
                        float(r["Value ₹"])/(float(r["Qty Ton"])*1000.0)
                        if float(r["Qty Ton"] or 0)>0 else 0.0
                    ),
                    axis=1
                )
                st.markdown("#### Reel Consumption Detail")
                st.dataframe(
                    _v122_reel_display[[
                        "Line","Reel / ERP Code","Paper Description / GSM",
                        "Qty Ton","Value ₹","Rate ₹/Kg","Remark"
                    ]],
                    hide_index=True,use_container_width=True,
                    column_config={
                        "Qty Ton":st.column_config.NumberColumn(format="%.3f T"),
                        "Value ₹":st.column_config.NumberColumn(format="₹%.2f"),
                        "Rate ₹/Kg":st.column_config.NumberColumn(format="₹%.2f"),
                    }
                )

    with tab_monthly:
        st.markdown("### Monthly MD Corrugation Report")
        st.caption(
            "One clean monthly report from app data only. No ERP DPR fields are mixed into this report."
        )

        _v122_month=st.selectbox(
            "Production Month",
            _month_opts,
            index=_month_opts.index(global_payroll_month),
            format_func=lambda d:d.strftime("%b %Y"),
            key="v122_monthly_report_month"
        )
        _v122_first,_v122_last=_month_range(_v122_month)

        _v122_prod_month=read_df(
            """SELECT work_date,production_ton,target_ton,waste_ton,breakdown_hours,
                      paper_cost,material_processed_ton,good_output_ton
               FROM production
               WHERE shift='DAY' AND machine='Corrugation'
                 AND work_date BETWEEN ? AND ?
               ORDER BY work_date""",
            (_v122_first.isoformat(),_v122_last.isoformat())
        )
        _v122_reel_month=read_df(
            """SELECT work_date,
                      SUM(quantity_ton) AS reel_qty_ton,
                      SUM(value_amount) AS reel_value
               FROM production_reel_consumption
               WHERE machine='Corrugation'
                 AND work_date BETWEEN ? AND ?
               GROUP BY work_date ORDER BY work_date""",
            (_v122_first.isoformat(),_v122_last.isoformat())
        )
        _v122_mp_month=read_df(
            """SELECT work_date,shift,COUNT(DISTINCT employee_id) AS people
               FROM manpower_allocation
               WHERE machine='Corrugation'
                 AND work_date BETWEEN ? AND ?
               GROUP BY work_date,shift
               ORDER BY work_date,shift""",
            (_v122_first.isoformat(),_v122_last.isoformat())
        )

        if _v122_prod_month.empty and _v122_reel_month.empty:
            st.info(f"No Corrugation data is saved for {_v122_month.strftime('%B %Y')}.")
        else:
            if _v122_prod_month.empty:
                _v122_base=pd.DataFrame(columns=[
                    "work_date","production_ton","target_ton","waste_ton","breakdown_hours",
                    "paper_cost","material_processed_ton","good_output_ton"
                ])
            else:
                _v122_base=_v122_prod_month.copy()

            _v122_dates=set()
            if not _v122_base.empty:
                _v122_dates.update(_v122_base["work_date"].astype(str).tolist())
            if not _v122_reel_month.empty:
                _v122_dates.update(_v122_reel_month["work_date"].astype(str).tolist())
            _v122_daily=pd.DataFrame({"work_date":sorted(_v122_dates)})

            if not _v122_base.empty:
                _v122_base["work_date"]=_v122_base["work_date"].astype(str)
                _v122_daily=_v122_daily.merge(_v122_base,on="work_date",how="left")
            else:
                for _c in [
                    "production_ton","target_ton","waste_ton","breakdown_hours",
                    "paper_cost","material_processed_ton","good_output_ton"
                ]:
                    _v122_daily[_c]=0.0

            if not _v122_reel_month.empty:
                _v122_reel_month["work_date"]=_v122_reel_month["work_date"].astype(str)
                _v122_daily=_v122_daily.merge(_v122_reel_month,on="work_date",how="left")
            else:
                _v122_daily["reel_qty_ton"]=0.0
                _v122_daily["reel_value"]=0.0

            for _c in [
                "production_ton","target_ton","waste_ton","breakdown_hours",
                "paper_cost","material_processed_ton","good_output_ton",
                "reel_qty_ton","reel_value"
            ]:
                if _c not in _v122_daily.columns:
                    _v122_daily[_c]=0.0
                _v122_daily[_c]=pd.to_numeric(_v122_daily[_c],errors="coerce").fillna(0.0)

            _v122_daily["Reel Qty Ton"]=_v122_daily.apply(
                lambda r:float(r["reel_qty_ton"])
                if float(r["reel_qty_ton"])>0 else float(r["material_processed_ton"]),
                axis=1
            )
            _v122_daily["Reel Value"]=_v122_daily.apply(
                lambda r:float(r["reel_value"])
                if float(r["reel_value"])>0 else float(r["paper_cost"]),
                axis=1
            )
            _v122_daily["Production Ton"]=_v122_daily.apply(
                lambda r:float(r["good_output_ton"])
                if float(r["good_output_ton"])>0 else float(r["production_ton"]),
                axis=1
            )
            _v122_daily["Target Ton"]=_v122_daily["target_ton"]
            _v122_daily["Waste Ton"]=_v122_daily["waste_ton"]
            _v122_daily["Breakdown Hrs"]=_v122_daily["breakdown_hours"]

            _v122_daily["Avg Rate ₹/Kg"]=_v122_daily.apply(
                lambda r:(
                    float(r["Reel Value"])/(float(r["Reel Qty Ton"])*1000.0)
                    if float(r["Reel Qty Ton"])>0 else 0.0
                ),
                axis=1
            )
            _v122_daily["Achievement %"]=_v122_daily.apply(
                lambda r:(
                    float(r["Production Ton"])/float(r["Target Ton"])*100.0
                    if float(r["Target Ton"])>0 else 0.0
                ),
                axis=1
            )
            _v122_daily["Yield %"]=_v122_daily.apply(
                lambda r:(
                    float(r["Production Ton"])/float(r["Reel Qty Ton"])*100.0
                    if float(r["Reel Qty Ton"])>0 else 0.0
                ),
                axis=1
            )
            _v122_daily["Waste %"]=_v122_daily.apply(
                lambda r:(
                    float(r["Waste Ton"])/float(r["Reel Qty Ton"])*100.0
                    if float(r["Reel Qty Ton"])>0 else 0.0
                ),
                axis=1
            )
            _v122_daily["Material Variance Ton"]=_v122_daily.apply(
                lambda r:float(r["Reel Qty Ton"])-float(r["Production Ton"])-float(r["Waste Ton"]),
                axis=1
            )

            _v122_daily["Shift A Manpower"]=0
            _v122_daily["Shift B Manpower"]=0
            if not _v122_mp_month.empty:
                _v122_mp_month["work_date"]=_v122_mp_month["work_date"].astype(str)
                for _idx,_mr in _v122_mp_month.iterrows():
                    _mask=_v122_daily["work_date"]==str(_mr["work_date"])
                    if str(_mr["shift"])=="A":
                        _v122_daily.loc[_mask,"Shift A Manpower"]=int(_mr["people"] or 0)
                    elif str(_mr["shift"])=="B":
                        _v122_daily.loc[_mask,"Shift B Manpower"]=int(_mr["people"] or 0)

            _v122_daily["Total Person-Shifts"]=(
                _v122_daily["Shift A Manpower"]+_v122_daily["Shift B Manpower"]
            )
            _v122_daily["Corrugation Ton / Person"]=_v122_daily.apply(
                lambda r:(
                    float(r["Production Ton"])/float(r["Total Person-Shifts"])
                    if float(r["Total Person-Shifts"])>0 else 0.0
                ),
                axis=1
            )
            _v122_daily["Date"]=pd.to_datetime(
                _v122_daily["work_date"],errors="coerce"
            ).dt.date

            _v122_days=int((_v122_daily["Production Ton"]>0).sum())
            _v122_total_reel=float(_v122_daily["Reel Qty Ton"].sum())
            _v122_total_value=float(_v122_daily["Reel Value"].sum())
            _v122_total_output=float(_v122_daily["Production Ton"].sum())
            _v122_total_target=float(_v122_daily["Target Ton"].sum())
            _v122_total_waste=float(_v122_daily["Waste Ton"].sum())
            _v122_total_break=float(_v122_daily["Breakdown Hrs"].sum())
            _v122_total_people=int(_v122_daily["Total Person-Shifts"].sum())
            _v122_avg_rate=(
                _v122_total_value/(_v122_total_reel*1000.0)
                if _v122_total_reel>0 else 0.0
            )
            _v122_month_yield=(
                _v122_total_output/_v122_total_reel*100.0
                if _v122_total_reel>0 else 0.0
            )
            _v122_month_waste=(
                _v122_total_waste/_v122_total_reel*100.0
                if _v122_total_reel>0 else 0.0
            )
            _v122_month_achievement=(
                _v122_total_output/_v122_total_target*100.0
                if _v122_total_target>0 else 0.0
            )
            _v122_month_tpp=(
                _v122_total_output/_v122_total_people
                if _v122_total_people>0 else 0.0
            )
            _v122_paper_cost_ton=(
                _v122_total_value/_v122_total_output
                if _v122_total_output>0 else 0.0
            )

            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("Production Days",f"{_v122_days:,}")
            c2.metric("Reel Consumption",f"{_v122_total_reel:,.2f} T")
            c3.metric("Reel Value",v5_money(_v122_total_value))
            c4.metric("Avg Paper Rate",f"₹{_v122_avg_rate:,.2f}/Kg")
            c5.metric("Paper Cost / Output Ton",v5_money(_v122_paper_cost_ton))

            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("Corrugation Production",f"{_v122_total_output:,.2f} T")
            c2.metric("Target",f"{_v122_total_target:,.2f} T")
            c3.metric("Achievement",f"{_v122_month_achievement:,.2f}%")
            c4.metric("Waste %",f"{_v122_month_waste:,.2f}%")
            c5.metric("Yield",f"{_v122_month_yield:,.2f}%")

            c1,c2,c3,c4=st.columns(4)
            c1.metric("Waste / Rejection",f"{_v122_total_waste:,.2f} T")
            c2.metric("Breakdown",f"{_v122_total_break:,.2f} Hrs")
            c3.metric("Corrugation Person-Shifts",f"{_v122_total_people:,}")
            c4.metric(
                "Corrugation Ton / Person",
                f"{_v122_month_tpp:,.2f} T" if _v122_total_people>0 else "MANPOWER PENDING"
            )

            st.caption(
                "Monthly Corrugation Ton / Person = Total monthly Corrugation Production ÷ Total Corrugation person-shifts. "
                "It is not an average of daily percentages."
            )
            if _v122_total_people==0:
                st.warning(
                    "No Corrugation manpower allocation exists for this month yet. "
                    "The production report is valid, but Ton / Person will stay pending until manpower is allocated."
                )

            st.markdown("#### Date-wise Management Report")
            _v122_display=_v122_daily[[
                "Date","Reel Qty Ton","Reel Value","Avg Rate ₹/Kg",
                "Production Ton","Target Ton","Achievement %",
                "Waste Ton","Waste %","Yield %","Breakdown Hrs",
                "Shift A Manpower","Shift B Manpower","Total Person-Shifts",
                "Corrugation Ton / Person","Material Variance Ton"
            ]].copy()
            st.dataframe(
                _v122_display,hide_index=True,use_container_width=True,height=470,
                column_config={
                    "Reel Qty Ton":st.column_config.NumberColumn(format="%.3f T"),
                    "Reel Value":st.column_config.NumberColumn(format="₹%.2f"),
                    "Avg Rate ₹/Kg":st.column_config.NumberColumn(format="₹%.2f"),
                    "Production Ton":st.column_config.NumberColumn(format="%.2f T"),
                    "Target Ton":st.column_config.NumberColumn(format="%.2f T"),
                    "Achievement %":st.column_config.NumberColumn(format="%.2f%%"),
                    "Waste Ton":st.column_config.NumberColumn(format="%.2f T"),
                    "Waste %":st.column_config.NumberColumn(format="%.2f%%"),
                    "Yield %":st.column_config.NumberColumn(format="%.2f%%"),
                    "Breakdown Hrs":st.column_config.NumberColumn(format="%.2f"),
                    "Corrugation Ton / Person":st.column_config.NumberColumn(format="%.2f T"),
                    "Material Variance Ton":st.column_config.NumberColumn(format="%.3f T"),
                }
            )

            st.markdown("#### MD Trends")
            c1,c2=st.columns(2,gap="small")
            with c1:
                _v122_long=_v122_daily[["Date","Production Ton","Target Ton"]].melt(
                    "Date",var_name="Series",value_name="Ton"
                )
                chart=alt.Chart(_v122_long).mark_line(point=True).encode(
                    x=alt.X("Date:T",title="Date"),
                    y=alt.Y("Ton:Q",title="Ton"),
                    color=alt.Color("Series:N",title=""),
                    tooltip=["Date:T","Series:N",alt.Tooltip("Ton:Q",format=".2f")]
                ).properties(height=280,title="Production vs Target")
                st.altair_chart(chart,use_container_width=True)
            with c2:
                _v122_long2=_v122_daily[["Date","Reel Qty Ton","Production Ton"]].melt(
                    "Date",var_name="Series",value_name="Ton"
                )
                chart=alt.Chart(_v122_long2).mark_line(point=True).encode(
                    x=alt.X("Date:T",title="Date"),
                    y=alt.Y("Ton:Q",title="Ton"),
                    color=alt.Color("Series:N",title=""),
                    tooltip=["Date:T","Series:N",alt.Tooltip("Ton:Q",format=".2f")]
                ).properties(height=280,title="Reel Consumption vs Production")
                st.altair_chart(chart,use_container_width=True)

            c1,c2=st.columns(2,gap="small")
            with c1:
                chart=alt.Chart(_v122_daily).mark_line(point=True).encode(
                    x=alt.X("Date:T",title="Date"),
                    y=alt.Y("Waste %:Q",title="Waste %"),
                    tooltip=["Date:T",alt.Tooltip("Waste %:Q",format=".2f")]
                ).properties(height=280,title="Waste % Trend")
                st.altair_chart(chart,use_container_width=True)
            with c2:
                _v122_tpp_chart=_v122_daily[_v122_daily["Total Person-Shifts"]>0].copy()
                if _v122_tpp_chart.empty:
                    st.info("Ton / Person trend will appear after Corrugation manpower allocation is entered.")
                else:
                    chart=alt.Chart(_v122_tpp_chart).mark_line(point=True).encode(
                        x=alt.X("Date:T",title="Date"),
                        y=alt.Y("Corrugation Ton / Person:Q",title="Ton / Person"),
                        tooltip=["Date:T",alt.Tooltip("Corrugation Ton / Person:Q",format=".2f")]
                    ).properties(height=280,title="Corrugation Ton / Person Trend")
                    st.altair_chart(chart,use_container_width=True)

            _v122_report_bytes=make_excel_report(
                _v122_display,
                "Corrugation Monthly MD Report",
                f"Greater Noida Plant | {_v122_month.strftime('%b %Y')}"
            )
            st.download_button(
                "Download Monthly Corrugation Report",
                data=_v122_report_bytes,
                file_name=f"Corrugation_MD_Report_{_v122_month.strftime('%Y_%m')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",use_container_width=True,
                key="v122_download_monthly_corrugation"
            )

            with st.expander("View Complete Monthly Reel Detail"):
                _v122_all_reels=read_df(
                    """SELECT work_date,line_no,reel_reference,paper_grade,
                              quantity_ton,value_amount,remark
                       FROM production_reel_consumption
                       WHERE machine='Corrugation'
                         AND work_date BETWEEN ? AND ?
                       ORDER BY work_date,line_no""",
                    (_v122_first.isoformat(),_v122_last.isoformat())
                )
                if _v122_all_reels.empty:
                    st.info("No reel-level rows are saved for this month.")
                else:
                    _v122_all_reels=_v122_all_reels.rename(columns={
                        "work_date":"Date","line_no":"Line",
                        "reel_reference":"Reel / ERP Code",
                        "paper_grade":"Paper Description / GSM",
                        "quantity_ton":"Qty Ton","value_amount":"Value ₹",
                        "remark":"Remark"
                    })
                    _v122_all_reels["Rate ₹/Kg"]=_v122_all_reels.apply(
                        lambda r:(
                            float(r["Value ₹"])/(float(r["Qty Ton"])*1000.0)
                            if float(r["Qty Ton"] or 0)>0 else 0.0
                        ),
                        axis=1
                    )
                    st.dataframe(
                        _v122_all_reels[[
                            "Date","Line","Reel / ERP Code","Paper Description / GSM",
                            "Qty Ton","Value ₹","Rate ₹/Kg","Remark"
                        ]],
                        hide_index=True,use_container_width=True,
                        column_config={
                            "Qty Ton":st.column_config.NumberColumn(format="%.3f T"),
                            "Value ₹":st.column_config.NumberColumn(format="₹%.2f"),
                            "Rate ₹/Kg":st.column_config.NumberColumn(format="₹%.2f"),
                        }
                    )

'''
s=s[:start]+report_block+s[end:]

p.write_text(s,encoding="utf-8")
print("Applied V12.2 MD production reporting model")
