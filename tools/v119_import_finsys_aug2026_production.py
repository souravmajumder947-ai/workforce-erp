from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V11.9 FINSYS AUGUST 2026 DAILY PRODUCTION IMPORT"
if MARK in s:
    print("V11.9 Finsys August production import already applied")
    raise SystemExit(0)

anchor = '''def can_view_salary(role):
    return str(role) in {"Owner", "Admin", "HR", "Manager"}
'''

helper = r'''# V11.9 FINSYS AUGUST 2026 DAILY PRODUCTION IMPORT
# Source: Corrugation Production Report (DPR Report), 01-31 Aug 2026.
# The report has no production rows for 02 Aug and 15 Aug, so no records are invented for those dates.
_FINSYS_AUG2026_CORRUGATION_DAILY = [
    # date, total_minutes, plan_qty, prodn_qty, rejn_qty, net_boxes, prod_mtr, prodn_wt_kg, paper_used_kg, reel_wstg_kg, wstg_pct
    ("2026-08-01",1251.00,235375,50384,2564,242996,94416,105794,102222,-1062,-1.04),
    ("2026-08-03",1269.00,50416,51114,3071,120131,94659,100012,102426,-888,-0.87),
    ("2026-08-04",1416.00,50231,45940,2844,83136,95500,102372,107655,1104,1.03),
    ("2026-08-05",1108.00,48882,39949,2149,79556,83243,88911,91576,-1675,-1.83),
    ("2026-08-06",1395.00,124377,65914,8115,203413,101401,104349,108946,1074,0.99),
    ("2026-08-07",1266.00,99255,55032,3576,141564,91398,97919,96594,-5106,-5.29),
    ("2026-08-08",1269.00,68610,51006,2626,105044,98452,99138,100770,-6000,-5.96),
    ("2026-08-09",669.00,38790,21534,1109,44289,42814,43381,45701,1468,3.21),
    ("2026-08-10",1290.00,104270,51689,3209,115726,96827,102280,106652,135,0.13),
    ("2026-08-11",1238.00,73892,47329,3154,133130,81539,85672,99309,2346,2.36),
    ("2026-08-12",2728.00,189450,58538,4902,199983,96382,116912,107982,4978,4.61),
    ("2026-08-13",1347.00,76898,47461,3179,100906,86139,93689,99927,2041,2.04),
    ("2026-08-14",989.00,88740,33586,3268,96302,64490,66051,62487,-3552,-5.68),
    ("2026-08-16",254.00,9053,10400,709,20151,21085,21455,22680,655,2.89),
    ("2026-08-17",2614.00,64513,52388,4161,200400,96740,105310,100249,-839,-0.84),
    ("2026-08-18",1313.00,136625,49753,4671,157994,95992,104005,105455,-645,-0.61),
    ("2026-08-19",1297.00,142768,44662,4537,194510,81937,85317,90045,-41,-0.05),
    ("2026-08-20",1237.00,58047,46920,3234,100582,91607,102702,101657,-1495,-1.47),
    ("2026-08-21",1261.00,60351,47304,3907,94373,93707,98357,100012,-2523,-2.52),
    ("2026-08-22",1112.00,55914,41425,4768,99788,77437,76303,81678,827,1.01),
    ("2026-08-23",570.00,20275,20542,1680,56705,36534,37688,39032,489,1.25),
    ("2026-08-24",1376.00,52839,57291,3986,208886,98756,113426,109994,-1138,-1.04),
    ("2026-08-25",1161.00,79860,46271,3507,107423,90181,90029,95403,1492,1.56),
    ("2026-08-26",1133.00,81723,37609,3487,89264,69411,78731,84677,2079,2.46),
    ("2026-08-27",1338.00,82143,48634,4082,152017,88699,106647,103135,-3391,-3.29),
    ("2026-08-28",573.00,26544,23708,1125,56901,43348,42732,42284,-825,-1.95),
    ("2026-08-29",1136.00,54645,40307,2986,79586,80308,85848,92154,2770,3.01),
    ("2026-08-30",1384.00,126550,58257,3350,141466,101641,97214,105254,4425,4.21),
    ("2026-08-31",651.00,23080,23927,1627,52233,41605,44582,57666,10951,18.99),
]

def ensure_finsys_aug2026_corrugation_daily_import():
    """Idempotently load August 2026 Finsys daily Corrugation totals into live production."""
    conn = get_pg_conn()
    inserted = 0
    updated = 0
    preserved = 0
    try:
        cur = conn.cursor()
        for row in _FINSYS_AUG2026_CORRUGATION_DAILY:
            (
                work_date,total_minutes,plan_qty,prodn_qty,rejn_qty,net_boxes,
                prod_mtr,prodn_wt_kg,paper_used_kg,reel_wstg_kg,wstg_pct
            ) = row
            prodn_wt_t = float(prodn_wt_kg) / 1000.0
            paper_used_t = float(paper_used_kg) / 1000.0
            reel_wstg_t = float(reel_wstg_kg) / 1000.0
            yield_pct = (prodn_wt_t / paper_used_t * 100.0) if paper_used_t else 0.0
            source_remark = (
                "FINSYS DPR IMPORT | Aug 2026 | "
                f"Total Hrs={float(total_minutes)/60.0:.2f}; Plan Qty={int(plan_qty)}; "
                f"Prodn Qty={int(prodn_qty)}; Rejn Qty={int(rejn_qty)}; Net Boxes={int(net_boxes)}; "
                f"Prod.Mtr={int(prod_mtr)}; Prodn Wt={prodn_wt_t:.3f}T; "
                f"Paper Used={paper_used_t:.3f}T; Reel Wstg={reel_wstg_t:.3f}T; "
                f"Report Wstg%={float(wstg_pct):.2f}"
            )

            cur.execute(
                """SELECT remark FROM production
                   WHERE work_date=%s AND shift='DAY' AND machine='Corrugation'
                   LIMIT 1""",
                (work_date,)
            )
            existing = cur.fetchone()
            if existing and not str(existing[0] or "").startswith("FINSYS DPR IMPORT"):
                preserved += 1
                continue

            cur.execute(
                """INSERT INTO production(
                       work_date,shift,machine,production_ton,target_ton,waste_ton,breakdown_hours,
                       paper_cost,ink_cost,glue_cost,other_material_cost,target_type,
                       opening_wip_ton,material_received_ton,material_available_ton,
                       material_processed_ton,good_output_ton,closing_wip_ton,
                       conversion_pct,yield_pct,waste_pct,remark
                   ) VALUES (
                       %s,'DAY','Corrugation',%s,110.0,%s,0,
                       0,0,0,0,'FIXED_TON',
                       0,0,%s,%s,%s,0,
                       0,%s,%s,%s
                   )
                   ON CONFLICT(work_date,shift,machine) DO UPDATE SET
                       production_ton=excluded.production_ton,
                       target_ton=excluded.target_ton,
                       waste_ton=excluded.waste_ton,
                       breakdown_hours=excluded.breakdown_hours,
                       target_type=excluded.target_type,
                       material_available_ton=excluded.material_available_ton,
                       material_processed_ton=excluded.material_processed_ton,
                       good_output_ton=excluded.good_output_ton,
                       yield_pct=excluded.yield_pct,
                       waste_pct=excluded.waste_pct,
                       remark=excluded.remark""",
                (
                    work_date,prodn_wt_t,reel_wstg_t,paper_used_t,paper_used_t,
                    prodn_wt_t,yield_pct,float(wstg_pct),source_remark
                )
            )
            if existing:
                updated += 1
            else:
                inserted += 1

        cur.execute(
            """INSERT INTO app_settings(setting_key,setting_value)
               VALUES ('finsys_corrugation_aug2026_import_v1',%s)
               ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value""",
            (f"loaded:{len(_FINSYS_AUG2026_CORRUGATION_DAILY)}; inserted:{inserted}; updated:{updated}; preserved:{preserved}",)
        )
        conn.commit()
        cur.close()
        return {"inserted": inserted, "updated": updated, "preserved": preserved, "source_rows": len(_FINSYS_AUG2026_CORRUGATION_DAILY)}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def can_view_salary(role):
    return str(role) in {"Owner", "Admin", "HR", "Manager"}
'''

if anchor not in s:
    raise RuntimeError("Helper insertion anchor not found")
s = s.replace(anchor, helper, 1)

op_anchor = '''elif page == "Operations":
    # V11.6 PRODUCTION ENTRY FIRST
'''
op_new = '''elif page == "Operations":
    # Load the approved historical August 2026 DPR into the live production table.
    try:
        _v119_import_result = ensure_finsys_aug2026_corrugation_daily_import()
    except Exception as _v119_import_exc:
        _v119_import_result = None
        st.error(f"August 2026 production history import failed: {_v119_import_exc}")

    # V11.6 PRODUCTION ENTRY FIRST
'''
if op_anchor not in s:
    raise RuntimeError("Operations page anchor not found")
s = s.replace(op_anchor, op_new, 1)

# Historical Finsys DPR can contain signed reel-wastage values; allow those imported rows to display safely.
old_waste = '''                    waste_ton=c2.number_input(
                        "Waste / Rejection Ton",min_value=0.0,
                        value=_existing_waste,step=0.1
                    )
'''
new_waste = '''                    _is_finsys_history = _existing_remark.startswith("FINSYS DPR IMPORT")
                    waste_ton=c2.number_input(
                        "Reel Wastage / Rejection Ton",
                        value=_existing_waste,step=0.1,
                        help=(
                            "Historical Finsys DPR rows may contain signed Reel Wastage values. "
                            "For new manual production, enter the actual wastage/rejection for the day."
                        )
                    )
'''
if old_waste not in s:
    raise RuntimeError("Corrugation waste input anchor not found")
s = s.replace(old_waste,new_waste,1)

old_validation = '''                    if good_output+waste_ton > paper_consumed + 0.01:
                        _fixed_errors.append(
                            "Good Output + Waste/Rejection cannot be greater than total Reel Consumption."
                        )
'''
new_validation = '''                    if waste_ton < 0 and not _is_finsys_history:
                        _fixed_errors.append(
                            "Negative wastage is allowed only for historical Finsys DPR records."
                        )
                    if (not _is_finsys_history) and good_output+waste_ton > paper_consumed + 0.01:
                        _fixed_errors.append(
                            "Good Output + Waste/Rejection cannot be greater than total Reel Consumption."
                        )
'''
if old_validation not in s:
    raise RuntimeError("Corrugation validation anchor not found")
s = s.replace(old_validation,new_validation,1)

# Add a clear status caption in Operations after page header.
status_anchor = '''    tab_prod,tab_mp=st.tabs(["Production Entry","Manpower Allocation"])

    with tab_prod:
'''
status_new = '''    tab_prod,tab_mp=st.tabs(["Production Entry","Manpower Allocation"])

    if _v119_import_result:
        st.caption(
            "August 2026 Finsys DPR history is loaded day-wise for Corrugation: "
            f"{_v119_import_result['source_rows']} production date(s) in source; "
            "02 Aug and 15 Aug had no DPR date record and were not invented."
        )

    with tab_prod:
'''
if status_anchor not in s:
    raise RuntimeError("Operations tabs anchor not found")
s = s.replace(status_anchor,status_new,1)

p.write_text(s, encoding="utf-8")
print("Applied V11.9 Finsys August 2026 day-wise production import")
