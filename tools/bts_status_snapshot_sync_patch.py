from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

anchor = '''        cur.execute("DELETE FROM app_sessions WHERE expires_at <= CURRENT_TIMESTAMP")
        conn.commit()
'''

if anchor not in text:
    raise SystemExit('migrate_postgres end anchor not found')

block = '''        # ------------------------------------------------------------
        # BTS EMPLOYEE STATUS SNAPSHOT - 01 SEP 2026
        # ------------------------------------------------------------
        # User-approved one-time alignment from the read-only BTS Employee
        # Master snapshot. Employee ID is the only matching key.
        # IMPORTANT:
        #   - Existing HRMS employees only; BTS-only rows are NEVER added.
        #   - Only employees present in the authoritative HRMS master snapshot
        #     are included in these lists.
        #   - Name, department, designation, shift, salary and attendance are
        #     NOT changed.
        #   - HRMS employees not visible in the BTS snapshot are left unchanged.
        #   - This is one-time so later manual HR changes are not overwritten
        #     by a stale BTS snapshot on every Streamlit rerun.
        _bts_active_ids_20260901 = [
            '10004', '10006', '10011', '10012', '10023', '10029', '10030', '10040', '10051', '10058', '10059', '10079',
            '10081', '10086', '10091', '10109', '10112', '10114', '10145', '10146', '10163', '10169', '10170', '10172',
            '10176', '10181', '10183', '10186', '10189', '10200', '10207', '10209', '10211', '10218', '10226', '10228',
            '10229', '10233', '10236', '10240', '10245', '10247', '10251', '10261', '10262', '10269', '10272', '10273',
            '10288', '10289', '10290', '10302', '10308', '10312', '10317', '10321', '10327', '10336', '10337', '10338',
            '10341', '10343', '10347', '10348', '10354', '10370', '10371', '10372', '10375', '10379', '10383', '10391',
            '10402', '10403', '10406', '10415', '10420', '10439', '10441', '10444', '10455', '10461', '10463', '10464',
            '10465', '10471', '10476', '10481', '10483', '10485', '10493', '10506', '10514', '10515', '10516', '10542',
            '10543', '10546', '10547', '10550', '10559', '10571', '10576', '10586', '10589', '10591', '10607', '10618',
            '10620', '10626', '10633', '10640', '10642', '10643', '10652', '10658', '10667', '10670', '10676', '10677',
            '10678', '10680', '10682', '10684', '10691', '10697', '10698', '10699', '10706', '10710', '10716', '10717',
            '10741', '10744', '10751', '10752', '10753', '10755', '10762', '10763', '10765', '10774', '10776', '10784',
            '10785', '10792', '10793', '10795', '10796', '10799', '10800', '10808', '10812', '10817', '10818', '10819',
            '10826', '10827', '10828', '10830', '10831', '10832', '10834', '10839', '10841', '10842', '10843', '10849',
            '10850', '10851', '10853', '10854', '10855', '10858', '10869', '10874', '10875', '10877', '10880', '10882',
            '10885', '10887', '10890', '10891', '10892', '10894', '10895', '10907', '10908', '10909', '10910', '10911',
            '10912', '10919', '10921', '10922', '10924', '10925', '10927', '10928', '10933', '10934', '10935', '10936',
            '10937', '10938', '10939', '10940', '10941', '10942', '10943', '10944', '10945', '10946', '10947', '10001',
            '10005', '10201', '10398', '10399', '10488', '10665', '10674', '10701', '10182', '10062', '20086', '20228',
            '10659',
        ]
        _bts_inactive_ids_20260901 = [
            '10565', '10663', '10742', '10770', '10789', '10802', '10829', '10836', '10838', '10844', '10845', '10848',
            '10863', '10864', '10865', '10872', '10881', '10884', '10886', '10896', '10897', '10898', '10916', '10920',
            '10923', '10926', '10903', '10904', '10905', '10906',
        ]

        cur.execute("""
            INSERT INTO app_settings(setting_key, setting_value)
            VALUES ('bts_employee_status_snapshot_20260901_v1', 'pending')
            ON CONFLICT(setting_key) DO NOTHING
        """)
        cur.execute("""
            SELECT setting_value
            FROM app_settings
            WHERE setting_key='bts_employee_status_snapshot_20260901_v1'
        """)
        _bts_status_sync_state = cur.fetchone()

        if _bts_status_sync_state and _bts_status_sync_state[0] == 'pending':
            # Sync only IDs that already exist in HRMS. No INSERT is performed.
            cur.execute(
                "UPDATE employees SET status='Active' WHERE employee_id = ANY(%s)",
                (_bts_active_ids_20260901,)
            )
            _bts_active_updated = cur.rowcount
            cur.execute(
                "UPDATE employees SET status='Inactive' WHERE employee_id = ANY(%s)",
                (_bts_inactive_ids_20260901,)
            )
            _bts_inactive_updated = cur.rowcount

            cur.execute("""
                UPDATE app_settings
                SET setting_value='completed'
                WHERE setting_key='bts_employee_status_snapshot_20260901_v1'
            """)
            cur.execute("""
                INSERT INTO app_settings(setting_key, setting_value)
                VALUES ('bts_employee_status_snapshot_20260901_summary', %s)
                ON CONFLICT(setting_key)
                DO UPDATE SET setting_value=excluded.setting_value
            """, (
                f"active_updated={_bts_active_updated};inactive_updated={_bts_inactive_updated};"
                "not_in_bts_unchanged=20322,20349;source=Employee master.pdf",
            ))

'''

text = text.replace(anchor, block + anchor, 1)
p.write_text(text, encoding='utf-8')
