import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils import get_mosques, get_meters, get_consumption_stats, predict_usage, login_user

st.set_page_config(layout="wide", page_title="نظام مراقبة المساجد", page_icon="🕌")

# RTL CSS
st.markdown("""
<style>
    .stApp { direction: rtl; text-align: right; }
    h1, h2, h3, p, div { text-align: right; }
</style>
""", unsafe_allow_html=True)

# --- Database Initialization for Deployment ---
# This ensures the DB exists and has data when deployed to Streamlit Cloud
@st.cache_resource
def init_db():
    from models import seed_data
    try:
        seed_data()
        return True
    except Exception as e:
        st.error(f"Failed to initialize database: {e}")
        return False

if not init_db():
    st.info("Stopping application due to database initialization failure.")
    st.stop()

# Session State for Auth
if 'user' not in st.session_state:
    st.session_state.user = None

def login():
    st.title("🔐 تسجيل الدخول")
    username = st.text_input("اسم المستخدم")
    password = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        user = login_user(username, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("اسم المستخدم أو كلمة المرور غير صحيحة")

if not st.session_state.user:
    login()
    st.stop()

# Sidebar
user_role = st.session_state.user.role if hasattr(st.session_state.user, 'role') else 'manager'
st.sidebar.title(f"مرحباً, {st.session_state.user.username}")
if st.sidebar.button("تسجيل الخروج"):
    st.session_state.user = None
    st.rerun()

st.sidebar.title("القائمة الرئيسية")
# Admin gets extra options
pages = ["لوحة القيادة", "إدخال البيانات", "التنبؤات"]
if user_role == 'admin':
    pages.append("إدارة النظام")

page = st.sidebar.radio("انتقل إلى", pages)

# 1. Dashboard
# 1. Dashboard
if page == "لوحة القيادة":
    st.title("🕌 لوحة القيادة العامة")
    
    # --- Filters ---
    st.markdown("### 🔍 تصفية البيانات")
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        mosques = get_mosques()
        m_opts = {m.name: m.id for m in mosques}
        # Add "All" option
        sel_m_names = st.multiselect("المسجد", list(m_opts.keys()), default=list(m_opts.keys())[:1])
        sel_m_ids = [m_opts[n] for n in sel_m_names] if sel_m_names else None

    with f_col2:
        sel_utility = st.multiselect("نوع الخدمة", ["Electricity", "Water"], default=["Electricity"])
        
    with f_col3:
        # Date Filter
        today = datetime.now().date()
        date_range = st.date_input(
            "الفترة الزمنية",
            value=(today - timedelta(days=30), today),
            max_value=today
        )

    # Validate Dates
    start_date, end_date = None, None
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range

    # --- Fetch Data ---
    from utils import get_chart_data
    # Helper to merge multiple mosque IDs if list
    # For POC, simplified logical OR in filtering or iteratively fetch
    # Since get_chart_data accepts single ID, let's modify or just loop. 
    # Better: Update utils to accept list. For now, let's fetch all and filter in Pandas for POC speed
    
    df_chart = get_chart_data(start_date=start_date, end_date=end_date)
    
    # Apply Python-side Filters
    if not df_chart.empty:
        if sel_m_ids:
            df_chart = df_chart[df_chart['mosque_id'].isin(sel_m_ids)]
        if sel_utility:
            df_chart = df_chart[df_chart['type'].isin(sel_utility)]

    # --- KPIs ---
    st.markdown("---")
    if not df_chart.empty:
        total_cons = df_chart['daily_consumption'].sum()
        total_cost = df_chart['cost'].sum()
        
        k1, k2, k3 = st.columns(3)
        k1.metric("إجمالي الاستهلاك", f"{total_cons:,.2f}")
        k2.metric("التكلفة الإجمالية", f"{total_cost:,.2f} ريال")
        k3.metric("عدد القراءات", len(df_chart))
    
    # --- Visualizations ---
    if not df_chart.empty:
        # 1. Line Chart (Trends) - FR-Viz-01
        st.subheader("📈 اتجاهات الاستهلاك")
        # Aggregate by Date and Type
        line_data = df_chart.groupby(['date', 'type'])['daily_consumption'].sum().reset_index()
        
        fig_line = px.line(
            line_data, x='date', y='daily_consumption', color='type',
            labels={'date': 'التاريخ', 'daily_consumption': 'الاستهلاك', 'type': 'النوع'},
            title="الاستهلاك اليومي (مقارنة)"
        )
        fig_line.update_layout(hovermode="x unified")
        st.plotly_chart(fig_line, width="stretch")
        
        col_charts_1, col_charts_2 = st.columns(2)
        
        with col_charts_1:
            # 2. Bar Chart (Costs) - FR-Viz-02
            st.subheader("💰 التكلفة الشهرية")
            df_chart['month'] = df_chart['date'].dt.strftime('%Y-%m')
            bar_data = df_chart.groupby(['month', 'type'])['cost'].sum().reset_index()
            
            fig_bar = px.bar(
                bar_data, x='month', y='cost', color='type', barmode='group',
                labels={'month': 'الشهر', 'cost': 'التكلفة (ريال)'},
                title="توزيع التكاليف الشهرية"
            )
            st.plotly_chart(fig_bar, width="stretch")

        with col_charts_2:
            # 3. Gauge Chart (Anomaly) - FR-Viz-03
            # Simple logic: Compare avg of selected period vs all-time avg (approx 300)
            st.subheader("⚠️ مؤشر الاستهلاك")
            avg_curr = df_chart['daily_consumption'].mean()
            # Fake baseline for POC
            baseline = 250.0 
            
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = avg_curr,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "متوسط الاستهلاك اليومي"},
                delta = {'reference': baseline},
                gauge = {
                    'axis': {'range': [None, 500]},
                    'bar': {'color': "darkblue"},
                    'steps' : [
                        {'range': [0, 200], 'color': "lightgreen"},
                        {'range': [200, 350], 'color': "yellow"},
                        {'range': [350, 500], 'color': "red"}
                    ],
                }
            ))
            st.plotly_chart(fig_gauge, width="stretch")

        # Download Data
        csv_data = df_chart.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 تحميل البيانات المعروضة (CSV)",
            data=csv_data,
            file_name=f"data_export_{datetime.now().date()}.csv",
            mime="text/csv"
        )
    else:
        st.warning("لا توجد بيانات للفترة المحددة.")

# 2. Prediction
elif page == "التنبؤات":
    st.title("📈 التنبؤ بالاستهلاك الذكي")
    
    mosques = get_mosques()
    m_opts = {m.name: m.id for m in mosques}
    sel_m_name = st.selectbox("اختر المسجد", list(m_opts.keys()))
    
    if sel_m_name:
        m_id = m_opts[sel_m_name]
        meters = get_meters(m_id)
        met_opts = {f"{met.type} ({met.id})": met.id for met in meters}
        
        sel_met_name = st.selectbox("اختر العداد", list(met_opts.keys()))
        
        if sel_met_name:
            if st.button("توليد التوقعات"):
                met_id = met_opts[sel_met_name]
                df_pred, avg_pred, accuracy = predict_usage(met_id)
                
                if not df_pred.empty:
                    st.success("تم توليد التوقعات بنجاح!")
                    
                    # Display Accuracy
                    col_acc, col_val = st.columns(2)
                    col_acc.metric("دقة النموذج (R²)", f"{accuracy:.2f}")
                    col_val.metric("متوسط الاستهلاك المتوقع", f"{avg_pred:.2f}")
                    
                    fig = px.line(df_pred, x='ds', y='y', color='type', 
                                  color_discrete_map={'Historical': 'blue', 'Predicted': 'red'})
                    fig.update_traces(patch={"line": {"dash": "dash"}}, selector={"legendgroup": "Predicted"}) 
                    # Note: Simple dash handling in plotly express requires careful mapping or update_traces
                    
                    st.plotly_chart(fig, width="stretch")
                    
                    # Warning Logic
                    hist_avg = df_pred[df_pred['type']=='Historical']['y'].mean()
                    if avg_pred > hist_avg * 1.2:
                        st.error(f"⚠️ تحذير: الاستهلاك المتوقع ({avg_pred:.2f}) أعلى بنسبة 20% من المعدل الطبيعي ({hist_avg:.2f})!")
                    else:
                        st.info("الاستهلاك المتوقع ضمن الحدود الطبيعية.")
                else:
                    st.warning("لا توجد بيانات كافية.")

elif page == "إدخال البيانات":
    st.title("📝 إدخال البيانات")
    
    st.markdown("### تسجيل قراءة جديدة")
    
    mosques = get_mosques()
    m_opts = {m.name: m.id for m in mosques}
    sel_m_name = st.selectbox("اختر المسجد", list(m_opts.keys()))
    
    if sel_m_name:
        m_id = m_opts[sel_m_name]
        meters = get_meters(m_id)
        # Dictionary mapping display text to (meter_id, meter_type)
        met_opts = {f"{met.type} ({met.id})": (met.id, met.type) for met in meters}
        
        sel_met_label = st.selectbox("اختر العداد", list(met_opts.keys()))
        
        if sel_met_label:
            met_id, met_type = met_opts[sel_met_label]
            
            with st.form("entry_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    date_val = st.date_input("تاريخ القراءة", value=datetime.now())
                
                with col2:
                    current_val = st.number_input("قراءة العداد الحالية (Cumulative)", min_value=0.0, step=1.0)
                
                # Auto-calculate cost (Optional helper)
                unit_price = 0.18 if met_type == 'Electricity' else 5.0
                st.caption(f"سعر الوحدة الافتراضي: {unit_price} ريال")
                
                submitted = st.form_submit_button("حفظ القراءة")
                
                if submitted:
                    from utils import add_reading
                    # Estimate cost roughly based on this reading (in real app, diff with prev)
                    # For POC, just passing 0 or simple calc if we had diff
                    success = add_reading(met_id, date_val, current_val, cost=0) # Cost 0 for now as we calculate on diff
                    
                    if success:
                        st.success("✅ تم حفظ البيانات بنجاح!")
                        st.info("يمكنك التحقق من البيانات الجديدة في لوحة القيادة.")

    st.markdown("---")
    st.markdown("### 📤 استيراد ملف CSV")
    uploaded_file = st.file_uploader("اختر ملف CSV (الأعمدة: meter_id, date, value, cost)", type="csv")
    if uploaded_file:
        from utils import process_csv_upload
        if st.button("معالجة الملف"):
            success, msg = process_csv_upload(uploaded_file)
            if success:
                st.success(msg)
            else:
                st.error(f"حدث خطأ: {msg}")

elif page == "إدارة النظام":
    st.title("⚙️ إدارة النظام")
    
    from utils import create_mosque, delete_mosque, create_meter, delete_meter, create_user
    
    tab1, tab2, tab3 = st.tabs(["المساجد", "العدادات", "المستخدمين"])
    
    with tab1:
        st.header("إدارة المساجد")
        
        with st.expander("إضافة مسجد جديد"):
            with st.form("add_mosque_form"):
                new_m_name = st.text_input("اسم المسجد")
                new_m_loc = st.text_input("الموقع")
                new_m_cap = st.number_input("السعة", min_value=1)
                
                if st.form_submit_button("إضافة"):
                    if create_mosque(new_m_name, new_m_loc, new_m_cap):
                        st.success("تم إضافة المسجد بنجاح")
                        st.rerun()
        
        st.markdown("### قائمة المساجد")
        mosques = get_mosques()
        for m in mosques:
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{m.name}** - {m.location} ({m.capacity} مصلي)")
            if c2.button("حذف", key=f"del_m_{m.id}"):
                delete_mosque(m.id)
                st.rerun()

    with tab2:
        st.header("إدارة العدادات")
        mosques = get_mosques()
        m_opts = {m.name: m.id for m in mosques}
        sel_m_mgr = st.selectbox("اختر المسجد للعدادات", list(m_opts.keys()), key="mgr_meters")
        
        if sel_m_mgr:
            m_id = m_opts[sel_m_mgr]
            meters = get_meters(m_id)
            
            st.write(f"العدادات الحالية لـ {sel_m_mgr}:")
            for met in meters:
                c1, c2 = st.columns([3, 1])
                c1.write(f"{met.type} (ID: {met.id})")
                if c2.button("حذف", key=f"del_met_{met.id}"):
                    delete_meter(met.id)
                    st.rerun()
            
            st.markdown("---")
            with st.form("add_meter_form"):
                new_met_type = st.selectbox("نوع العداد", ["Electricity", "Water"])
                if st.form_submit_button("إضافة عداد"):
                    create_meter(m_id, new_met_type)
                    st.success("تم إضافة العداد")
                    st.rerun()

    with tab3:
        st.header("إدارة المستخدمين")
        with st.form("add_user_form"):
            new_u_name = st.text_input("اسم المستخدم")
            new_u_pwd = st.text_input("كلمة المرور", type="password")
            new_u_role = st.selectbox("الصلاحية", ["manager", "admin"])
            
            if st.form_submit_button("إنشاء مستخدم"):
                if create_user(new_u_name, new_u_pwd, new_u_role):
                    st.success(f"تم إنشاء المستخدم {new_u_name}")
                else:
                    st.error("اسم المستخدم موجود مسبقاً")

