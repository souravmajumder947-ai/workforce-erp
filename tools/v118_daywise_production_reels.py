from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V11.8 DAY-WISE PRODUCTION + REEL CONSUMPTION"
if MARK in s:
    print("V11.8 day-wise production already applied")
    raise SystemExit(0)

old_intro = '''    with tab_prod:
        st.markdown("### Production Entry")
        st.caption(
            "Select Date → Shift → Machine. Existing entries are loaded automatically and can be safely updated."
        )
        c1,c2,c3=st.columns(3)
        pdate=c1.date_input("Production Date",value=global_work_date,format="DD/MM/YYYY",key="v66_prod_date")
        shift=c2.selectbox("Shift",["A","B"],key="v66_prod_shift")
        machine_df=get_machine_list_cached()
        machine_options=machine_df["machine"].astype(str).tolist() if not machine_df.empty else []
        machine=c3.selectbox("Machine",machine_options,key="v66_prod_machine") if machine_options else None
'''

new_intro = '''    with tab_prod:
        # V11.8 DAY-WISE PRODUCTION + REEL CONSUMPTION
        st.markdown("### Daily Production Entry")
        st.caption(
            "One production record per Date + Machine. Attendance and manpower can remain shift-wise, "
            "but production is captured as the complete 24-hour production day."
        )

        # Reel-consumption detail is stored separately and rolls up into the daily Corrugation record.
        try:
            _v118_conn = get_pg_conn()
            _v118_cur = _v118_conn.cursor()
            _v118_cur.execute(
                """
                CREATE TABLE IF NOT EXISTS production_reel_consumption(
                    id BIGSERIAL PRIMARY KEY,
                    work_date DATE NOT NULL,
                    machine TEXT NOT NULL,
                    line_no INTEGER NOT NULL,
                    reel_reference TEXT,
                    paper_grade TEXT,
                    quantity_ton NUMERIC(14,4) NOT NULL DEFAULT 0,
                    value_amount NUMERIC(16,2) NOT NULL DEFAULT 0,
                    remark TEXT,
                    entered_by TEXT,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(work_date,machine,line_no)
                )
                """
            )
            _v118_conn.commit()
            _v118_cur.close()
            _v118_conn.close()
        except Exception as _v118_schema_exc:
            try:
                _v118_conn.rollback()
                _v118_conn.close()
            except Exception:
                pass
            st.error(f"Unable to prepare reel-consumption storage: {_v118_schema_exc}")
            st.stop()

        c1,c2=st.columns([1,1.4])
        pdate=c1.date_input(
            "Production Date",value=global_work_date,format="DD/MM/YYYY",key="v118_prod_date"
        )
        machine_df=get_machine_list_cached()
        machine_options=machine_df["machine"].astype(str).tolist() if not machine_df.empty else []
        machine=c2.selectbox(
            "Machine",machine_options,key="v118_prod_machine"
        ) if machine_options else None
        production_shift="DAY"
'''

if old_intro not in s:
    raise RuntimeError("Production intro anchor not found")
s=s.replace(old_intro,new_intro,1)

old_existing = '''            existing=read_df(
                "SELECT * FROM production WHERE work_date=? AND shift=? AND machine=?",
                (pdate.isoformat(),shift,machine)
            )
            er=existing.iloc[0].to_dict() if not existing.empty else {}
            std,shift_target=get_machine_shift_target(machine,shift)

            _prod_master_row = machine_df[machine_df["machine"].astype(str) == str(machine)]
'''

new_existing = '''            existing=read_df(
                "SELECT * FROM production WHERE work_date=? AND shift='DAY' AND machine=?",
                (pdate.isoformat(),machine)
            )
            legacy_shift_rows=read_df(
                "SELECT shift,production_ton,good_output_ton,waste_ton FROM production "
                "WHERE work_date=? AND machine=? AND shift IN ('A','B') ORDER BY shift",
                (pdate.isoformat(),machine)
            )
            er=existing.iloc[0].to_dict() if not existing.empty else {}

            _prod_master_row = machine_df[machine_df["machine"].astype(str) == str(machine)]
'''

if old_existing not in s:
    raise RuntimeError("Existing production anchor not found")
s=s.replace(old_existing,new_existing,1)

old_status = '''            pinfo1,pinfo2,pinfo3,pinfo4 = st.columns(4)
            pinfo1.metric("Division","Greater Noida Plant")
            pinfo2.metric("Department",_prod_department)
            pinfo3.metric("Machine",str(machine))
            pinfo4.metric("Entry Status","Update Existing" if not existing.empty else "New Entry")
            if not existing.empty:
                st.info(
                    f"An entry already exists for {pdate.strftime('%d/%m/%Y')} · Shift {shift} · {machine}. "
                    "Saving will update that same production record, not create a duplicate."
                )
'''

new_status = '''            pinfo1,pinfo2,pinfo3,pinfo4 = st.columns(4)
            pinfo1.metric("Division","Greater Noida Plant")
            pinfo2.metric("Department",_prod_department)
            pinfo3.metric("Machine",str(machine))
            pinfo4.metric("Entry Status","Update Existing" if not existing.empty else "New Daily Entry")
            if not existing.empty:
                st.info(
                    f"A daily entry already exists for {pdate.strftime('%d/%m/%Y')} · {machine}. "
                    "Saving will update that same Date + Machine record."
                )
            if not legacy_shift_rows.empty:
                st.warning(
                    "Legacy Shift A / B production rows exist for this Date + Machine. "
                    "They are kept for history and are not automatically merged into the new daily record."
                )
'''

if old_status not in s:
    raise RuntimeError("Production status anchor not found")
s=s.replace(old_status,new_status,1)

start = s.find('            if target_type=="FIXED_TON":\n                # V11.7 CORRUGATION MATERIAL BALANCE ENTRY')
if start == -1:
    raise RuntimeError("Corrugation block start not found")
end = s.find('\n            else:\n                target_pct=float(profile.get("conversion_target_pct") or 100)', start)
if end == -1:
    raise RuntimeError("Corrugation block end not found")

new_corr = '''            if target_type=="FIXED_TON":
                # V11.8 CORRUGATION DAILY REEL CONSUMPTION
                daily_target=float(profile.get("daily_target_ton") or 0)
                st.info(
                    f"🎯 **Corrugation Daily Target** · **{daily_target:.2f} T / production day**"
                )
                st.caption(
                    "Enter each reel / paper line for the full production day. "
                    "Paper Consumed, Paper Value and Average Paper Rate are calculated automatically."
                )

                _reels_existing = read_df(
                    """SELECT line_no,reel_reference,paper_grade,quantity_ton,value_amount,remark
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
                            "Qty Consumed Ton":_legacy_qty,
                            "Value ₹":_legacy_value,
                            "Remark":"Loaded from existing daily production"
                        }])
                    else:
                        _reel_seed=pd.DataFrame([{
                            "Reel / Reference":"",
                            "Paper Grade":"",
                            "Qty Consumed Ton":0.0,
                            "Value ₹":0.0,
                            "Remark":""
                        }])
                else:
                    _reel_seed=_reels_existing.rename(columns={
                        "reel_reference":"Reel / Reference",
                        "paper_grade":"Paper Grade",
                        "quantity_ton":"Qty Consumed Ton",
                        "value_amount":"Value ₹",
                        "remark":"Remark"
                    })[["Reel / Reference","Paper Grade","Qty Consumed Ton","Value ₹","Remark"]].copy()

                st.markdown("#### Reel / Paper Consumption")
                reel_editor=st.data_editor(
                    _reel_seed,
                    hide_index=True,
                    use_container_width=True,
                    num_rows="dynamic",
                    key=f"v118_reel_editor_{pdate.isoformat()}_{machine}",
                    column_config={
                        "Reel / Reference":st.column_config.TextColumn("Reel / Reference"),
                        "Paper Grade":st.column_config.TextColumn("Paper Grade / GSM"),
                        "Qty Consumed Ton":st.column_config.NumberColumn(
                            "Qty Consumed Ton",min_value=0.0,step=0.001,format="%.3f"
                        ),
                        "Value ₹":st.column_config.NumberColumn(
                            "Value ₹",min_value=0.0,step=1.0,format="₹%.2f"
                        ),
                        "Remark":st.column_config.TextColumn("Remark"),
                    }
                )

                _reel_work=reel_editor.copy()
                _reel_work["Qty Consumed Ton"]=pd.to_numeric(
                    _reel_work["Qty Consumed Ton"],errors="coerce"
                ).fillna(0.0)
                _reel_work["Value ₹"]=pd.to_numeric(
                    _reel_work["Value ₹"],errors="coerce"
                ).fillna(0.0)
                _reel_work=_reel_work[
                    (_reel_work["Qty Consumed Ton"]>0)
                    | (_reel_work["Value ₹"]>0)
                    | (_reel_work["Reel / Reference"].fillna("").astype(str).str.strip()!="")
                    | (_reel_work["Paper Grade"].fillna("").astype(str).str.strip()!="")
                ].copy()

                paper_consumed=float(_reel_work["Qty Consumed Ton"].sum()) if not _reel_work.empty else 0.0
                paper_value=float(_reel_work["Value ₹"].sum()) if not _reel_work.empty else 0.0
                avg_paper_rate=(
                    paper_value/(paper_consumed*1000.0)
                    if paper_consumed>0 else 0.0
                )

                _existing_good=float(er.get("good_output_ton") or er.get("production_ton") or 0)
                _existing_waste=float(er.get("waste_ton") or 0)
                _existing_remark=str(er.get("remark") or "")
                _existing_break_reason=""
                _existing_prod_remark=_existing_remark
                if "Breakdown Reason:" in _existing_remark:
                    _parts=_existing_remark.split("Breakdown Reason:",1)
                    _existing_prod_remark=_parts[0].strip(" |")
                    _existing_break_reason=_parts[1].strip()

                with st.form("v118_daily_corrugation_form"):
                    c1,c2,c3=st.columns(3)
                    good_output=c1.number_input(
                        "Good Corrugated Output Ton",min_value=0.0,
                        value=_existing_good,step=0.1
                    )
                    waste_ton=c2.number_input(
                        "Waste / Rejection Ton",min_value=0.0,
                        value=_existing_waste,step=0.1
                    )
                    breakdown_hours=c3.number_input(
                        "Breakdown Hours",min_value=0.0,max_value=24.0,
                        value=float(er.get("breakdown_hours") or 0),step=0.25
                    )
                    breakdown_reason=st.text_input(
                        "Breakdown Reason",
                        value=_existing_break_reason,
                        placeholder="Required when Breakdown Hours is greater than 0"
                    )
                    remark=st.text_input(
                        "Production Remark",
                        value=_existing_prod_remark,
                        placeholder="Optional production / quality remark"
                    )
                    save_prod=st.form_submit_button(
                        "Save / Update Daily Corrugation Production",
                        type="primary",use_container_width=True
                    )

                achievement=(good_output/daily_target*100.0) if daily_target>0 else 0.0
                yield_pct=(good_output/paper_consumed*100.0) if paper_consumed>0 else 0.0
                waste_pct=(waste_ton/paper_consumed*100.0) if paper_consumed>0 else 0.0
                material_variance=paper_consumed-good_output-waste_ton
                paper_cost_per_output=paper_value/good_output if good_output>0 else 0.0

                r1,r2,r3,r4=st.columns(4)
                r1.metric("Paper Consumed",f"{paper_consumed:.3f} T")
                r2.metric("Paper Value",v5_money(paper_value))
                r3.metric("Avg Paper Rate",f"₹{avg_paper_rate:.2f} / Kg")
                r4.metric("Paper Cost / Output Ton",v5_money(paper_cost_per_output))

                k1,k2,k3,k4,k5=st.columns(5)
                k1.metric("Daily Target",f"{daily_target:.2f} T")
                k2.metric("Achievement",f"{achievement:.2f}%")
                k3.metric("Yield",f"{yield_pct:.2f}%")
                k4.metric("Waste",f"{waste_pct:.2f}%")
                k5.metric("Material Variance",f"{material_variance:.3f} T")

                if paper_consumed>0 and abs(material_variance)>0.01:
                    st.warning(
                        f"Material balance variance is {material_variance:.3f} T. "
                        "Paper Consumed should normally equal Good Output + Waste/Rejection."
                    )

                if save_prod:
                    _fixed_errors=[]
                    if (good_output>0 or waste_ton>0) and paper_consumed<=0:
                        _fixed_errors.append(
                            "Add reel / paper consumption before saving production output."
                        )
                    if good_output+waste_ton > paper_consumed + 0.01:
                        _fixed_errors.append(
                            "Good Output + Waste/Rejection cannot be greater than total Reel Consumption."
                        )
                    if breakdown_hours>0 and not str(breakdown_reason or "").strip():
                        _fixed_errors.append(
                            "Breakdown Reason is required when Breakdown Hours is greater than 0."
                        )
                    if not _reel_work.empty:
                        _bad_qty=_reel_work[
                            pd.to_numeric(_reel_work["Qty Consumed Ton"],errors="coerce").fillna(0)<=0
                        ]
                        if not _bad_qty.empty:
                            _fixed_errors.append(
                                "Every saved reel / paper line must have Qty Consumed Ton greater than 0."
                            )

                    if _fixed_errors:
                        for _err in _fixed_errors:
                            st.error(_err)
                    else:
                        _save_remark=str(remark or "").strip()
                        if breakdown_hours>0:
                            _br=str(breakdown_reason or "").strip()
                            _save_remark=(
                                f"{_save_remark} | Breakdown Reason: {_br}"
                                if _save_remark else f"Breakdown Reason: {_br}"
                            )

                        conn=get_pg_conn()
                        try:
                            cur=conn.cursor()
                            cur.execute(
                                """INSERT INTO production(
                                   work_date,shift,machine,production_ton,target_ton,waste_ton,breakdown_hours,
                                   paper_cost,ink_cost,glue_cost,other_material_cost,target_type,
                                   opening_wip_ton,material_received_ton,material_available_ton,
                                   material_processed_ton,good_output_ton,closing_wip_ton,
                                   conversion_pct,yield_pct,waste_pct,remark
                                   ) VALUES (%s,'DAY',%s,%s,%s,%s,%s,%s,0,0,0,'FIXED_TON',
                                             0,0,%s,%s,%s,0,0,%s,%s,%s)
                                   ON CONFLICT(work_date,shift,machine) DO UPDATE SET
                                   production_ton=excluded.production_ton,
                                   target_ton=excluded.target_ton,
                                   waste_ton=excluded.waste_ton,
                                   breakdown_hours=excluded.breakdown_hours,
                                   paper_cost=excluded.paper_cost,
                                   target_type='FIXED_TON',
                                   material_available_ton=excluded.material_available_ton,
                                   material_processed_ton=excluded.material_processed_ton,
                                   good_output_ton=excluded.good_output_ton,
                                   yield_pct=excluded.yield_pct,
                                   waste_pct=excluded.waste_pct,
                                   remark=excluded.remark""",
                                (
                                    pdate.isoformat(),machine,good_output,daily_target,waste_ton,
                                    breakdown_hours,paper_value,paper_consumed,paper_consumed,
                                    good_output,yield_pct,waste_pct,_save_remark
                                )
                            )
                            cur.execute(
                                "DELETE FROM production_reel_consumption WHERE work_date=%s AND machine=%s",
                                (pdate.isoformat(),machine)
                            )
                            for _line_no,(_, _rr) in enumerate(_reel_work.reset_index(drop=True).iterrows(),start=1):
                                cur.execute(
                                    """INSERT INTO production_reel_consumption(
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
                                )
                            conn.commit()
                            cur.close()
                        except Exception:
                            conn.rollback()
                            raise
                        finally:
                            conn.close()

                        record_audit_event(
                            _current_user["username"],"PRODUCTION_SAVE","Operations",
                            "Production",f"{pdate.isoformat()}|DAY|{machine}",
                            (
                                f"Daily; ReelLines={len(_reel_work)}; PaperConsumed={paper_consumed:.3f}; "
                                f"PaperValue={paper_value:.2f}; AvgRateKg={avg_paper_rate:.2f}; "
                                f"GoodOutput={good_output:.2f}; Target={daily_target:.2f}; "
                                f"Achievement={achievement:.2f}%; Waste={waste_ton:.2f}; "
                                f"Yield={yield_pct:.2f}%; WastePct={waste_pct:.2f}%; "
                                f"MaterialVariance={material_variance:.3f}; Breakdown={breakdown_hours:.2f}"
                            )
                        )
                        st.success("Daily Corrugation production saved successfully.")
                        st.rerun()
'''

s = s[:start] + new_corr + s[end:]

# Day-wise conversion-machine workflow: remove Shift from all keys and use DAY.
repls = [
    ('suggested_opening=get_previous_closing_wip(machine,pdate,shift)',
     'suggested_opening=get_previous_closing_wip(machine,pdate,production_shift)'),
    ('pdate.isoformat(),shift,machine,good_output,0.0,waste_ton,breakdown_hours,',
     'pdate.isoformat(),production_shift,machine,good_output,0.0,waste_ton,breakdown_hours,'),
    ('"Production", f"{pdate.isoformat()}|{shift}|{machine}",',
     '"Production", f"{pdate.isoformat()}|DAY|{machine}",'),
]
for a,b in repls:
    if a in s:
        s=s.replace(a,b,1)

# Replace the conversion INSERT so DAY is explicit and the tuple does not rely on removed shift UI.
old_conv_values = '''                               ) VALUES (?,?,?,?,?,?,?,0,0,0,0,?,?,?,?,?,?,?,?,?,?,?)
                               ON CONFLICT(work_date,shift,machine) DO UPDATE SET'''
new_conv_values = '''                               ) VALUES (?,?,?,?,?,?,?,0,0,0,0,?,?,?,?,?,?,?,?,?,?,?)
                               ON CONFLICT(work_date,shift,machine) DO UPDATE SET'''
# same placeholder count; production_shift variable is supplied in tuple above.

# Daily summary: only new DAY records.
old_summary_where='''               WHERE p.work_date=? ORDER BY p.shift,p.machine""",
            (pdate.isoformat(),)
'''
new_summary_where='''               WHERE p.work_date=? AND p.shift='DAY' ORDER BY p.machine""",
            (pdate.isoformat(),)
'''
if old_summary_where not in s:
    raise RuntimeError("Production daily-summary filter anchor not found")
s=s.replace(old_summary_where,new_summary_where,1)

# Display Shift as Daily period instead of exposing an irrelevant A/B field.
old_display='''                "work_date":"Date","shift":"Shift","machine":"Machine","department":"Department",'''
new_display='''                "work_date":"Date","shift":"Period","machine":"Machine","department":"Department",'''
if old_display not in s:
    raise RuntimeError("Production display columns anchor not found")
s=s.replace(old_display,new_display,1)

# Existing conversion form info text should say daily.
old_info='''                    f"🔄 **100% Material Conversion Target** · Target completion: **{target_pct:.2f}%** · "
                    "No fixed ton target is used for this machine."
'''
new_info='''                    f"🔄 **Daily Material Conversion Target** · Target completion: **{target_pct:.2f}%** · "
                    "This is one complete production-day record; no A/B production split is required."
'''
if old_info in s:
    s=s.replace(old_info,new_info,1)

# Header description.
s=s.replace(
    '"Enter production first. Corrugation uses a fixed-ton target; downstream machines use material-conversion flow.",',
    '"Production is day-wise by machine. Corrugation uses daily reel consumption; downstream machines use daily material-conversion flow.",',
    1
)

p.write_text(s, encoding="utf-8")
print("Applied V11.8 day-wise production with Corrugation reel consumption")
