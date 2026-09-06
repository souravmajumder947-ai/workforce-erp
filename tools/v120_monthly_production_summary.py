from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

MARK="# V12.0 MONTHLY PRODUCTION SUMMARY"
if MARK in s:
    print("V12.0 monthly production summary already applied")
    raise SystemExit(0)

old_tabs='''    tab_prod,tab_mp=st.tabs(["Production Entry","Manpower Allocation"])
'''
new_tabs='''    # V12.0 MONTHLY PRODUCTION SUMMARY
    tab_prod,tab_monthly,tab_mp=st.tabs([
        "Production Entry","Monthly Production Summary","Manpower Allocation"
    ])
'''
if old_tabs not in s:
    raise RuntimeError("Operations tabs anchor not found")
s=s.replace(old_tabs,new_tabs,1)

anchor='''    with tab_mp:
        c1,c2,c3=st.columns(3)
'''
monthly=r'''    with tab_monthly:
        st.markdown("### Monthly Production Summary")
        st.caption(
            "Complete day-wise production view for management. Production remains one record per Date + Machine."
        )

        _v120_month = st.selectbox(
            "Production Month",
            _month_opts,
            index=_month_opts.index(global_payroll_month),
            format_func=lambda d:d.strftime("%b %Y"),
            key="v120_prod_month"
        )
        _v120_first,_v120_last=_month_range(_v120_month)

        _v120_month_df=read_df(
            """SELECT p.work_date,p.machine,p.production_ton,p.target_ton,p.waste_ton,
                      p.material_processed_ton,p.good_output_ton,p.yield_pct,p.waste_pct,
                      p.breakdown_hours,p.remark
               FROM production p
               WHERE p.shift='DAY'
                 AND p.work_date BETWEEN ? AND ?
               ORDER BY p.work_date,p.machine""",
            (_v120_first.isoformat(),_v120_last.isoformat())
        )

        if _v120_month_df.empty:
            st.info(f"No day-wise production records found for {_v120_month.strftime('%B %Y')}.")
        else:
            _v120_month_df["Date"]=pd.to_datetime(
                _v120_month_df["work_date"],errors="coerce"
            ).dt.date
            _v120_month_df["Production Ton"]=pd.to_numeric(
                _v120_month_df["good_output_ton"],errors="coerce"
            ).fillna(
                pd.to_numeric(_v120_month_df["production_ton"],errors="coerce").fillna(0)
            )
            _v120_month_df["Paper Used Ton"]=pd.to_numeric(
                _v120_month_df["material_processed_ton"],errors="coerce"
            ).fillna(0)
            _v120_month_df["Reel Wastage Ton"]=pd.to_numeric(
                _v120_month_df["waste_ton"],errors="coerce"
            ).fillna(0)
            _v120_month_df["Target Ton"]=pd.to_numeric(
                _v120_month_df["target_ton"],errors="coerce"
            ).fillna(0)
            _v120_month_df["Yield %"]=pd.to_numeric(
                _v120_month_df["yield_pct"],errors="coerce"
            ).fillna(0)
            _v120_month_df["Waste %"]=pd.to_numeric(
                _v120_month_df["waste_pct"],errors="coerce"
            ).fillna(0)

            # Historical Finsys DPR stores extra source metrics in the auditable remark.
            def _v120_remark_value(text,label,default=0.0):
                raw=str(text or "")
                token=f"{label}="
                if token not in raw:
                    return float(default)
                try:
                    value=raw.split(token,1)[1].split(";",1)[0].strip()
                    return float(value)
                except Exception:
                    return float(default)

            _v120_month_df["Production Hrs"]=_v120_month_df["remark"].apply(
                lambda x:_v120_remark_value(x,"Total Hrs",0)
            )
            _v120_month_df["Plan Qty"]=_v120_month_df["remark"].apply(
                lambda x:_v120_remark_value(x,"Plan Qty",0)
            )
            _v120_month_df["Production Qty"]=_v120_month_df["remark"].apply(
                lambda x:_v120_remark_value(x,"Prodn Qty",0)
            )
            _v120_month_df["Rejection Qty"]=_v120_month_df["remark"].apply(
                lambda x:_v120_remark_value(x,"Rejn Qty",0)
            )
            _v120_month_df["Net Boxes"]=_v120_month_df["remark"].apply(
                lambda x:_v120_remark_value(x,"Net Boxes",0)
            )
            _v120_month_df["Production Meters"]=_v120_month_df["remark"].apply(
                lambda x:_v120_remark_value(x,"Prod.Mtr",0)
            )
            _v120_month_df["Achievement %"]=_v120_month_df.apply(
                lambda r:(float(r["Production Ton"])/float(r["Target Ton"])*100.0)
                if float(r["Target Ton"] or 0)>0 else 0.0,
                axis=1
            )

            _v120_prod_days=int(_v120_month_df["Date"].nunique())
            _v120_output=float(_v120_month_df["Production Ton"].sum())
            _v120_paper=float(_v120_month_df["Paper Used Ton"].sum())
            _v120_waste=float(_v120_month_df["Reel Wastage Ton"].sum())
            _v120_target=float(_v120_month_df["Target Ton"].sum())
            _v120_achievement=(_v120_output/_v120_target*100.0) if _v120_target>0 else 0.0
            _v120_yield=(_v120_output/_v120_paper*100.0) if _v120_paper>0 else 0.0
            _v120_waste_pct=(_v120_waste/_v120_paper*100.0) if _v120_paper else 0.0
            _v120_hours=float(_v120_month_df["Production Hrs"].sum())
            _v120_plan=float(_v120_month_df["Plan Qty"].sum())
            _v120_qty=float(_v120_month_df["Production Qty"].sum())
            _v120_rej=float(_v120_month_df["Rejection Qty"].sum())
            _v120_boxes=float(_v120_month_df["Net Boxes"].sum())
            _v120_meters=float(_v120_month_df["Production Meters"].sum())

            r1,r2,r3,r4,r5,r6=st.columns(6)
            r1.metric("Production Days",f"{_v120_prod_days:,}")
            r2.metric("Good Production",f"{_v120_output:,.2f} T")
            r3.metric("Paper Used",f"{_v120_paper:,.2f} T")
            r4.metric("Reel Wastage",f"{_v120_waste:,.2f} T")
            r5.metric("Yield",f"{_v120_yield:.2f}%")
            r6.metric("Waste %",f"{_v120_waste_pct:.2f}%")

            r1,r2,r3,r4,r5,r6=st.columns(6)
            r1.metric("Production Hours",f"{_v120_hours:,.2f}")
            r2.metric("Plan Qty",f"{_v120_plan:,.0f}")
            r3.metric("Production Qty",f"{_v120_qty:,.0f}")
            r4.metric("Rejection Qty",f"{_v120_rej:,.0f}")
            r5.metric("Net Boxes",f"{_v120_boxes:,.0f}")
            r6.metric("Production Meters",f"{_v120_meters:,.0f}")

            r1,r2,r3=st.columns(3)
            r1.metric("Monthly Target",f"{_v120_target:,.2f} T")
            r2.metric("Monthly Actual",f"{_v120_output:,.2f} T")
            r3.metric("Target Achievement",f"{_v120_achievement:.2f}%")

            st.markdown("#### Date-wise Production")
            _v120_display=_v120_month_df[[
                "Date","machine","Production Ton","Paper Used Ton","Reel Wastage Ton",
                "Yield %","Waste %","Production Hrs","Target Ton","Achievement %",
                "Plan Qty","Production Qty","Rejection Qty","Net Boxes","Production Meters"
            ]].copy()
            _v120_display=_v120_display.rename(columns={
                "machine":"Machine"
            })
            st.dataframe(
                _v120_display,
                hide_index=True,
                use_container_width=True,
                height=420,
                column_config={
                    "Production Ton":st.column_config.NumberColumn(format="%.2f T"),
                    "Paper Used Ton":st.column_config.NumberColumn(format="%.2f T"),
                    "Reel Wastage Ton":st.column_config.NumberColumn(format="%.2f T"),
                    "Yield %":st.column_config.NumberColumn(format="%.2f%%"),
                    "Waste %":st.column_config.NumberColumn(format="%.2f%%"),
                    "Production Hrs":st.column_config.NumberColumn(format="%.2f"),
                    "Target Ton":st.column_config.NumberColumn(format="%.2f T"),
                    "Achievement %":st.column_config.NumberColumn(format="%.2f%%"),
                    "Plan Qty":st.column_config.NumberColumn(format="%.0f"),
                    "Production Qty":st.column_config.NumberColumn(format="%.0f"),
                    "Rejection Qty":st.column_config.NumberColumn(format="%.0f"),
                    "Net Boxes":st.column_config.NumberColumn(format="%.0f"),
                    "Production Meters":st.column_config.NumberColumn(format="%.0f"),
                }
            )

            _v120_chart=_v120_month_df.groupby("Date",as_index=False).agg({
                "Production Ton":"sum",
                "Paper Used Ton":"sum",
                "Reel Wastage Ton":"sum",
                "Target Ton":"sum",
            })
            _v120_chart["Waste %"]=_v120_chart.apply(
                lambda r:(float(r["Reel Wastage Ton"])/float(r["Paper Used Ton"])*100.0)
                if float(r["Paper Used Ton"] or 0)!=0 else 0.0,
                axis=1
            )

            st.markdown("#### Monthly Production Trends")
            c1,c2=st.columns(2,gap="small")
            with c1:
                st.caption("Daily Production vs Target")
                _long=_v120_chart[["Date","Production Ton","Target Ton"]].melt(
                    "Date",var_name="Series",value_name="Ton"
                )
                chart=alt.Chart(_long).mark_line(point=True).encode(
                    x=alt.X("Date:T",title="Date"),
                    y=alt.Y("Ton:Q",title="Ton"),
                    color=alt.Color("Series:N",title=""),
                    tooltip=["Date:T","Series:N",alt.Tooltip("Ton:Q",format=".2f")]
                ).properties(height=280)
                st.altair_chart(chart,use_container_width=True)

            with c2:
                st.caption("Paper Consumption")
                chart=alt.Chart(_v120_chart).mark_bar().encode(
                    x=alt.X("Date:T",title="Date"),
                    y=alt.Y("Paper Used Ton:Q",title="Paper Used Ton"),
                    tooltip=["Date:T",alt.Tooltip("Paper Used Ton:Q",format=".2f")]
                ).properties(height=280)
                st.altair_chart(chart,use_container_width=True)

            c1,c2=st.columns(2,gap="small")
            with c1:
                st.caption("Daily Waste %")
                chart=alt.Chart(_v120_chart).mark_line(point=True).encode(
                    x=alt.X("Date:T",title="Date"),
                    y=alt.Y("Waste %:Q",title="Waste %"),
                    tooltip=["Date:T",alt.Tooltip("Waste %:Q",format=".2f")]
                ).properties(height=280)
                st.altair_chart(chart,use_container_width=True)

            with c2:
                st.caption("Daily Production Output")
                chart=alt.Chart(_v120_chart).mark_area(opacity=0.35).encode(
                    x=alt.X("Date:T",title="Date"),
                    y=alt.Y("Production Ton:Q",title="Good Production Ton"),
                    tooltip=["Date:T",alt.Tooltip("Production Ton:Q",format=".2f")]
                ).properties(height=280)
                st.altair_chart(chart,use_container_width=True)

    with tab_mp:
        c1,c2,c3=st.columns(3)
'''
if anchor not in s:
    raise RuntimeError("Manpower tab anchor not found")
s=s.replace(anchor,monthly,1)

p.write_text(s,encoding="utf-8")
print("Applied V12.0 monthly production summary")
