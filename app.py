import sqlite3
from datetime import date
from pathlib import Path
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / 'hr_production_cost.db'

st.set_page_config(page_title='HR & Production Cost Dashboard', page_icon='🏭', layout='wide')
st.markdown('''<style>.block-container{padding-top:1rem}[data-testid="stMetric"]{background:#111827;border:1px solid #253249;padding:14px;border-radius:12px}[data-testid="stMetricLabel"],[data-testid="stMetricValue"]{color:white}</style>''', unsafe_allow_html=True)

def conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    c.execute('PRAGMA foreign_keys=ON')
    return c

def init_db():
    with conn() as c:
        c.execute('CREATE TABLE IF NOT EXISTS employees(employee_id TEXT PRIMARY KEY, employee_name TEXT NOT NULL, department TEXT NOT NULL, designation TEXT NOT NULL, employee_type TEXT NOT NULL, shift TEXT NOT NULL, monthly_salary REAL NOT NULL DEFAULT 0, ot_rate REAL NOT NULL DEFAULT 0, working_days INTEGER NOT NULL DEFAULT 26, active TEXT NOT NULL DEFAULT "Yes")')
        c.execute('CREATE TABLE IF NOT EXISTS machines(machine TEXT PRIMARY KEY, department TEXT NOT NULL, standard_manpower INTEGER NOT NULL, target_ton REAL NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY AUTOINCREMENT, work_date TEXT NOT NULL, shift TEXT NOT NULL, employee_id TEXT NOT NULL, status TEXT NOT NULL, ot_hours REAL NOT NULL DEFAULT 0, UNIQUE(work_date,shift,employee_id))')
        c.execute('CREATE TABLE IF NOT EXISTS allocation(id INTEGER PRIMARY KEY AUTOINCREMENT, work_date TEXT NOT NULL, shift TEXT NOT NULL, machine TEXT NOT NULL, employee_id TEXT NOT NULL, role TEXT NOT NULL, UNIQUE(work_date,shift,machine,employee_id))')
        c.execute('CREATE TABLE IF NOT EXISTS production(id INTEGER PRIMARY KEY AUTOINCREMENT, work_date TEXT NOT NULL, shift TEXT NOT NULL, machine TEXT NOT NULL, production_ton REAL NOT NULL DEFAULT 0, target_ton REAL NOT NULL DEFAULT 0, waste_ton REAL NOT NULL DEFAULT 0, breakdown_hours REAL NOT NULL DEFAULT 0, UNIQUE(work_date,shift,machine))')
        if c.execute('SELECT COUNT(*) FROM machines').fetchone()[0] == 0:
            c.executemany('INSERT INTO machines VALUES (?,?,?,?)', [
                ('Corrugator-1','Corrugation',18,50),('Corrugator-2','Corrugation',17,48),('Printer-1','Printing',10,20),('Printer-2','Printing',9,20),('Pasting','Conversion',12,25),('Die Cutting','Conversion',14,25),('Finishing','Finishing',10,15),('Dispatch','Dispatch',8,12)])

def df(sql, params=()):
    with conn() as c:
        return pd.read_sql_query(sql, c, params=params)

def run(sql, params):
    with conn() as c:
        c.execute(sql, params)

def dashboard(report_date, shift):
    date_text = report_date.isoformat()
    where = 'work_date=?' if shift == 'All' else 'work_date=? AND shift=?'
    params = (date_text,) if shift == 'All' else (date_text, shift)
    emps = df('SELECT * FROM employees WHERE active="Yes"')
    att = df(f'SELECT * FROM attendance WHERE {where}', params)
    alloc = df(f'SELECT * FROM allocation WHERE {where}', params)
    prod = df(f'SELECT * FROM production WHERE {where}', params)
    machines = df('SELECT * FROM machines ORDER BY machine')
    present = att[att.status=='Present'] if not att.empty else pd.DataFrame()
    if not att.empty:
        costs = att.merge(emps[['employee_id','monthly_salary','ot_rate','working_days']], on='employee_id', how='left').fillna(0)
        costs['daily_cost'] = costs['monthly_salary']/costs['working_days'].replace(0,pd.NA)
        costs['attendance_cost'] = costs.apply(lambda r: r['daily_cost'] if r['status']=='Present' else 0, axis=1)
        costs['ot_cost'] = costs['ot_hours']*costs['ot_rate']
        attendance_cost = float(costs['attendance_cost'].sum())
        ot_cost = float(costs['ot_cost'].sum())
    else:
        attendance_cost = ot_cost = 0.0
    total_cost = attendance_cost + ot_cost
    total_prod = float(prod['production_ton'].sum()) if not prod.empty else 0.0
    total_target = float(prod['target_ton'].sum()) if not prod.empty else 0.0
    cost_per_ton = total_cost/total_prod if total_prod else 0.0
    efficiency = total_prod/total_target if total_target else 0.0
    alloc_sum = alloc.groupby('machine',as_index=False).agg(actual_manpower=('employee_id','nunique')) if not alloc.empty else pd.DataFrame(columns=['machine','actual_manpower'])
    prod_sum = prod.groupby('machine',as_index=False).agg(production_ton=('production_ton','sum'),target_actual=('target_ton','sum')) if not prod.empty else pd.DataFrame(columns=['machine','production_ton','target_actual'])
    a = machines.merge(alloc_sum,on='machine',how='left').merge(prod_sum,on='machine',how='left').fillna(0)
    mult = 2 if shift=='All' else 1
    a['standard_mp'] = a['standard_manpower']*mult
    a['target_display'] = a.apply(lambda r: r['target_actual'] if r['target_actual']>0 else r['target_ton']*mult, axis=1)
    a['mp_gap'] = a['actual_manpower']-a['standard_mp']
    a['efficiency'] = (a['production_ton']/a['target_display'].replace(0,pd.NA)).fillna(0)
    a['status'] = a.apply(lambda r: 'No Production' if r['production_ton']==0 else ('Overstaffed' if r['mp_gap']>1 else ('Understaffed' if r['mp_gap']<-1 else 'Optimal')), axis=1)
    a['recommendation'] = a.apply(lambda r: f"Reallocate {int(r['mp_gap'])} people" if r['status']=='Overstaffed' else (f"Add {abs(int(r['mp_gap']))} people" if r['status']=='Understaffed' else ('Check data/machine' if r['status']=='No Production' else 'Maintain')), axis=1)
    return dict(emps=emps,att=att,alloc=alloc,prod=prod,a=a,present=len(present),absent=int((att.status=='Absent').sum()) if not att.empty else 0,leave=int((att.status=='Leave').sum()) if not att.empty else 0,attendance_cost=attendance_cost,ot_cost=ot_cost,total_cost=total_cost,total_prod=total_prod,cost_per_ton=cost_per_ton,efficiency=efficiency)

init_db()
st.title('HR & Production Cost Management System')
st.caption('Monthly salary, attendance, machine allocation, production and cost-per-ton analysis')
page = st.sidebar.radio('Navigation',['Dashboard','Employee Master','Attendance','Manpower Allocation','Production Entry','Machine Master','Reports'])

if page=='Dashboard':
    c1,c2=st.columns(2); report_date=c1.date_input('Report Date',value=date.today()); shift=c2.selectbox('Shift',['All','A','B']); d=dashboard(report_date,shift)
    k1,k2,k3,k4,k5=st.columns(5); k1.metric('Present',d['present']); k2.metric('Production',f"{d['total_prod']:.2f} ton"); k3.metric('Labour Cost',f"₹{d['total_cost']:,.0f}"); k4.metric('Cost / Ton',f"₹{d['cost_per_ton']:,.0f}"); k5.metric('Efficiency',f"{d['efficiency']:.1%}")
    a,b,c,e=st.columns(4); a.metric('Absent',d['absent']); b.metric('On Leave',d['leave']); c.metric('Attendance Cost',f"₹{d['attendance_cost']:,.0f}"); e.metric('OT Cost',f"₹{d['ot_cost']:,.0f}")
    show=d['a'][['machine','department','standard_mp','actual_manpower','production_ton','target_display','mp_gap','efficiency','status','recommendation']].copy(); show.columns=['Machine','Department','Standard MP','Actual MP','Production Ton','Target Ton','MP Gap','Efficiency','Status','Recommendation']; show['Efficiency']=show['Efficiency'].map(lambda x:f'{x:.1%}'); st.dataframe(show,width='stretch',hide_index=True)

elif page=='Employee Master':
    st.subheader('Employee Master')
    with st.form('emp'):
        c1,c2,c3,c4=st.columns(4); eid=c1.text_input('Employee ID'); name=c2.text_input('Employee Name'); dept=c3.text_input('Department'); desig=c4.text_input('Designation')
        c1,c2,c3,c4=st.columns(4); etype=c1.selectbox('Employee Type',['Permanent','Contract']); shift=c2.selectbox('Default Shift',['A','B','General']); salary=c3.number_input('Monthly Salary',min_value=0.0,step=500.0); otrate=c4.number_input('OT Rate / Hour',min_value=0.0,step=10.0)
        c1,c2=st.columns(2); days=c1.number_input('Working Days / Month',min_value=1,max_value=31,value=26); active=c2.selectbox('Active',['Yes','No']); save=st.form_submit_button('Save Employee',width='stretch')
    if save:
        if not eid.strip() or not name.strip() or not dept.strip() or not desig.strip(): st.error('All basic employee fields are required.')
        else:
            run('INSERT INTO employees VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(employee_id) DO UPDATE SET employee_name=excluded.employee_name,department=excluded.department,designation=excluded.designation,employee_type=excluded.employee_type,shift=excluded.shift,monthly_salary=excluded.monthly_salary,ot_rate=excluded.ot_rate,working_days=excluded.working_days,active=excluded.active',(eid.strip(),name.strip(),dept.strip(),desig.strip(),etype,shift,float(salary),float(otrate),int(days),active)); st.success('Employee saved.'); st.rerun()
    e=df('SELECT * FROM employees ORDER BY employee_name');
    if not e.empty: e['daily_cost']=e['monthly_salary']/e['working_days']
    st.dataframe(e,width='stretch',hide_index=True)

elif page=='Attendance':
    st.subheader('Attendance and Overtime'); e=df('SELECT employee_id,employee_name FROM employees WHERE active="Yes" ORDER BY employee_name')
    if e.empty: st.info('Add employees first.')
    else:
        opts=e['employee_id']+' - '+e['employee_name']
        with st.form('att'):
            c1,c2,c3,c4,c5=st.columns(5); wd=c1.date_input('Date',value=date.today()); sh=c2.selectbox('Shift',['A','B']); emp=c3.selectbox('Employee',opts); status=c4.selectbox('Status',['Present','Absent','Leave']); oth=c5.number_input('OT Hours',min_value=0.0,max_value=24.0,step=0.5); save=st.form_submit_button('Save Attendance',width='stretch')
        if save: run('INSERT INTO attendance(work_date,shift,employee_id,status,ot_hours) VALUES (?,?,?,?,?) ON CONFLICT(work_date,shift,employee_id) DO UPDATE SET status=excluded.status,ot_hours=excluded.ot_hours',(wd.isoformat(),sh,emp.split(' - ')[0],status,float(oth))); st.success('Attendance saved.'); st.rerun()
        st.dataframe(df('SELECT a.work_date,a.shift,a.employee_id,e.employee_name,a.status,a.ot_hours FROM attendance a LEFT JOIN employees e ON e.employee_id=a.employee_id ORDER BY a.work_date DESC,a.shift,e.employee_name'),width='stretch',hide_index=True)

elif page=='Manpower Allocation':
    st.subheader('Employee-to-Machine Allocation'); e=df('SELECT employee_id,employee_name FROM employees WHERE active="Yes" ORDER BY employee_name'); m=df('SELECT machine FROM machines ORDER BY machine')['machine'].tolist()
    if e.empty: st.info('Add employees first.')
    else:
        opts=e['employee_id']+' - '+e['employee_name']
        with st.form('alloc'):
            c1,c2,c3,c4,c5=st.columns(5); wd=c1.date_input('Date',value=date.today()); sh=c2.selectbox('Shift',['A','B']); machine=c3.selectbox('Machine',m); emp=c4.selectbox('Employee',opts); role=c5.selectbox('Role',['Operator','Helper','Supervisor']); save=st.form_submit_button('Save Allocation',width='stretch')
        if save: run('INSERT INTO allocation(work_date,shift,machine,employee_id,role) VALUES (?,?,?,?,?) ON CONFLICT(work_date,shift,machine,employee_id) DO UPDATE SET role=excluded.role',(wd.isoformat(),sh,machine,emp.split(' - ')[0],role)); st.success('Allocation saved.'); st.rerun()
        st.dataframe(df('SELECT a.work_date,a.shift,a.machine,a.employee_id,e.employee_name,a.role FROM allocation a LEFT JOIN employees e ON e.employee_id=a.employee_id ORDER BY a.work_date DESC,a.shift,a.machine'),width='stretch',hide_index=True)

elif page=='Production Entry':
    st.subheader('Production Entry'); mdf=df('SELECT machine,target_ton FROM machines ORDER BY machine'); machines=mdf['machine'].tolist()
    with st.form('prod'):
        c1,c2,c3=st.columns(3); wd=c1.date_input('Date',value=date.today()); sh=c2.selectbox('Shift',['A','B']); machine=c3.selectbox('Machine',machines); default=float(mdf.loc[mdf.machine==machine,'target_ton'].iloc[0])
        c1,c2,c3,c4=st.columns(4); pt=c1.number_input('Production Ton',min_value=0.0,step=0.1); tt=c2.number_input('Target Ton',min_value=0.0,value=default,step=0.1); wt=c3.number_input('Waste Ton',min_value=0.0,step=0.1); bh=c4.number_input('Breakdown Hours',min_value=0.0,max_value=24.0,step=0.5); save=st.form_submit_button('Save Production',width='stretch')
    if save: run('INSERT INTO production(work_date,shift,machine,production_ton,target_ton,waste_ton,breakdown_hours) VALUES (?,?,?,?,?,?,?) ON CONFLICT(work_date,shift,machine) DO UPDATE SET production_ton=excluded.production_ton,target_ton=excluded.target_ton,waste_ton=excluded.waste_ton,breakdown_hours=excluded.breakdown_hours',(wd.isoformat(),sh,machine,float(pt),float(tt),float(wt),float(bh))); st.success('Production saved.'); st.rerun()
    st.dataframe(df('SELECT * FROM production ORDER BY work_date DESC,shift,machine'),width='stretch',hide_index=True)

elif page=='Machine Master':
    st.subheader('Machine Master'); machines=df('SELECT * FROM machines ORDER BY machine'); edited=st.data_editor(machines,width='stretch',hide_index=True,num_rows='dynamic')
    if st.button('Save Machine Master',width='stretch'):
        clean=edited.dropna(how='all').copy(); clean['machine']=clean['machine'].fillna('').astype(str).str.strip(); clean['department']=clean['department'].fillna('').astype(str).str.strip(); clean=clean[clean.machine!='']
        if clean.empty: st.error('At least one machine is required.')
        elif clean.machine.duplicated().any(): st.error('Duplicate machine names are not allowed.')
        elif (clean.department=='').any(): st.error('Department cannot be blank.')
        else:
            clean['standard_manpower']=pd.to_numeric(clean['standard_manpower'],errors='coerce'); clean['target_ton']=pd.to_numeric(clean['target_ton'],errors='coerce')
            if clean[['standard_manpower','target_ton']].isna().any().any(): st.error('Standard manpower and target ton must be numbers.')
            else:
                rows=[(r.machine,r.department,int(r.standard_manpower),float(r.target_ton)) for r in clean.itertuples(index=False)]
                with conn() as c: c.execute('DELETE FROM machines'); c.executemany('INSERT INTO machines VALUES (?,?,?,?)',rows)
                st.success('Machine Master saved.'); st.rerun()

else:
    st.subheader('Reports'); tabs=st.tabs(['Employees','Attendance','Allocation','Production']); reps=[('employees.csv',df('SELECT * FROM employees')),('attendance.csv',df('SELECT * FROM attendance')),('allocation.csv',df('SELECT * FROM allocation')),('production.csv',df('SELECT * FROM production'))]
    for tab,(name,data) in zip(tabs,reps):
        with tab: st.dataframe(data,width='stretch',hide_index=True); st.download_button(f'Download {name}',data.to_csv(index=False).encode('utf-8'),file_name=name,mime='text/csv')
