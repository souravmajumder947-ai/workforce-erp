from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V10.6 DATABASE LOGIN RESILIENCE"
if MARK in s:
    print("V10.6 database resilience patch already applied")
    raise SystemExit(0)

# Make PostgreSQL transport explicit for Neon-hosted deployments.
pool_anchor = '''        keepalives_interval=10,
        keepalives_count=3,
    )'''
pool_new = '''        keepalives_interval=10,
        keepalives_count=3,
        sslmode="require",
    )'''
if pool_anchor not in s:
    raise RuntimeError("PostgreSQL pool settings anchor not found")
s = s.replace(pool_anchor, pool_new, 1)

# Add an explicit discard path for stale/broken pooled connections.
close_anchor = '''    def __enter__(self):
        return self
'''
close_new = '''    def discard(self):
        """Permanently remove a broken connection from the pool."""
        if self._returned:
            return
        try:
            self._pool.putconn(self._conn, close=True)
        except Exception:
            try:
                if self._conn and not self._conn.closed:
                    self._conn.close()
            except Exception:
                pass
        finally:
            self._returned = True

    def __enter__(self):
        return self
'''
if close_anchor not in s:
    raise RuntimeError("Pooled connection class anchor not found")
s = s.replace(close_anchor, close_new, 1)

# Replace get_pg_conn with an active health-check, not just conn.closed.
old_get = '''def get_pg_conn():
    pool = _postgres_pool()

    # If Neon closed an idle connection, discard it and get a healthy one.
    for _ in range(2):
        conn = pool.getconn()
        if conn is not None and not conn.closed:
            return _PooledConnection(pool, conn)
        if conn is not None:
            try:
                pool.putconn(conn, close=True)
            except Exception:
                pass

    raise RuntimeError("Unable to obtain a PostgreSQL connection.")
'''
new_get = '''# V10.6 DATABASE LOGIN RESILIENCE
_PG_TRANSIENT_ERRORS = (psycopg2.OperationalError, psycopg2.InterfaceError)


def _discard_raw_pg_connection(pool, conn):
    if conn is None:
        return
    try:
        pool.putconn(conn, close=True)
    except Exception:
        try:
            if not conn.closed:
                conn.close()
        except Exception:
            pass


def get_pg_conn():
    pool = _postgres_pool()
    last_error = None

    # conn.closed is not enough: an idle TCP connection can look open locally
    # after Neon/server-side idle cleanup. Validate every checkout with SELECT 1.
    for _attempt in range(3):
        conn = None
        try:
            conn = pool.getconn()
            if conn is None or conn.closed:
                _discard_raw_pg_connection(pool, conn)
                continue

            cur = conn.cursor()
            try:
                cur.execute("SELECT 1")
                cur.fetchone()
            finally:
                cur.close()

            # SELECT 1 starts a transaction under psycopg2 default settings.
            # Roll it back before handing the connection to application code.
            conn.rollback()
            return _PooledConnection(pool, conn)

        except _PG_TRANSIENT_ERRORS as exc:
            last_error = exc
            _discard_raw_pg_connection(pool, conn)
            continue
        except Exception:
            _discard_raw_pg_connection(pool, conn)
            raise

    if last_error is not None:
        raise last_error
    raise RuntimeError("Unable to obtain a healthy PostgreSQL connection.")
'''
if old_get not in s:
    raise RuntimeError("get_pg_conn block not found")
s = s.replace(old_get, new_get, 1)

# Replace read_df with retry + broken-connection eviction.
old_read = '''def read_df(sql, params=()):
    pg_sql = sql.replace("?", "%s")

    conn = get_pg_conn()

    try:
        cur = conn.cursor()
        cur.execute(pg_sql, params)

        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

        cur.close()

        return _normalize_postgres_numbers(pd.DataFrame(rows, columns=columns))

    finally:
        conn.close()
'''
new_read = '''def read_df(sql, params=()):
    pg_sql = sql.replace("?", "%s")
    last_error = None

    for _attempt in range(3):
        conn = None
        try:
            conn = get_pg_conn()
            cur = conn.cursor()
            try:
                cur.execute(pg_sql, params)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
            finally:
                cur.close()
            return _normalize_postgres_numbers(pd.DataFrame(rows, columns=columns))

        except _PG_TRANSIENT_ERRORS as exc:
            last_error = exc
            if conn is not None:
                conn.discard()
            if _attempt >= 2:
                raise
            continue
        finally:
            if conn is not None and not getattr(conn, "_returned", False):
                conn.close()

    if last_error is not None:
        raise last_error
    return pd.DataFrame()
'''
if old_read not in s:
    raise RuntimeError("read_df block not found")
s = s.replace(old_read, new_read, 1)

# Replace upsert with retry + broken-connection eviction.
old_upsert = '''def upsert(sql, params):
    pg_sql = sql.replace("?", "%s")

    conn = get_pg_conn()

    try:
        cur = conn.cursor()
        cur.execute(pg_sql, params)

        conn.commit()

        cur.close()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
'''
new_upsert = '''def upsert(sql, params):
    pg_sql = sql.replace("?", "%s")
    last_error = None

    for _attempt in range(3):
        conn = None
        try:
            conn = get_pg_conn()
            cur = conn.cursor()
            try:
                cur.execute(pg_sql, params)
                conn.commit()
            finally:
                cur.close()
            return

        except _PG_TRANSIENT_ERRORS as exc:
            last_error = exc
            if conn is not None:
                conn.discard()
            if _attempt >= 2:
                raise
            continue
        except Exception:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if conn is not None and not getattr(conn, "_returned", False):
                conn.close()

    if last_error is not None:
        raise last_error
'''
if old_upsert not in s:
    raise RuntimeError("upsert block not found")
s = s.replace(old_upsert, new_upsert, 1)

# last_login telemetry must never prevent an otherwise-valid user from signing in.
old_last_login = '''    upsert(
        "UPDATE app_users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
        (int(row["user_id"]),),
    )
    return {
'''
new_last_login = '''    try:
        upsert(
            "UPDATE app_users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
            (int(row["user_id"]),),
        )
    except _PG_TRANSIENT_ERRORS:
        # Authentication already succeeded. A telemetry timestamp should not
        # block access because of a momentary database reconnect.
        pass
    return {
'''
if old_last_login not in s:
    raise RuntimeError("last_login update anchor not found")
s = s.replace(old_last_login, new_last_login, 1)

# Login UI: keep transient database faults inside the card instead of letting
# Streamlit show a full red application traceback.
old_login_submit = '''            if login_submit:
                user = authenticate_app_user(login_username, login_password)
                if user is None:
                    st.error("Invalid username/password or inactive user.")
                else:
                    _new_token = create_login_session(user["user_id"])
                    st.session_state["auth_user"] = user
                    st.session_state["auth_token"] = _new_token
                    st.query_params["session"] = _new_token
                    st.rerun()
'''
new_login_submit = '''            if login_submit:
                try:
                    user = authenticate_app_user(login_username, login_password)
                    if user is None:
                        st.error("Invalid username/password or inactive user.")
                    else:
                        try:
                            _new_token = create_login_session(user["user_id"])
                        except _PG_TRANSIENT_ERRORS:
                            # The user is authenticated. Allow this browser
                            # session to continue even if persistent-session
                            # storage briefly reconnects.
                            _new_token = None

                        st.session_state["auth_user"] = user
                        st.session_state["auth_token"] = _new_token
                        if _new_token:
                            st.query_params["session"] = _new_token
                        else:
                            try:
                                st.query_params.pop("session", None)
                            except Exception:
                                pass
                        st.rerun()

                except _PG_TRANSIENT_ERRORS:
                    st.warning(
                        "Database connection was temporarily interrupted and is reconnecting. "
                        "Please click Sign In once more if access does not continue automatically."
                    )
                except Exception:
                    # Do not expose database/internal traceback details on the
                    # public login screen. The full exception remains in server logs.
                    st.error(
                        "Unable to complete sign in right now. Please try again in a few seconds."
                    )
'''
if old_login_submit not in s:
    raise RuntimeError("Login submit block not found")
s = s.replace(old_login_submit, new_login_submit, 1)

p.write_text(s, encoding="utf-8")
print("Applied V10.6 PostgreSQL/login resilience")
