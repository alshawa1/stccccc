import sys
import os
import tempfile
from datetime import datetime, timedelta
import polars as pl
import streamlit as st
# ─── إعداد مسار المشروع ───
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
STC_DIR = os.path.join(THIS_DIR, "STC_System")
if STC_DIR not in sys.path:
    sys.path.insert(0, STC_DIR)
from core.data_loader import load_files
from core.utils import MAIN_PORTFOLIO, PROMISE_PAY, MAHARAH_PAY, COMPANY_PAY
from export.excel_writer_xl import ExcelReportWriter
# ─── إعدادات الصفحة ───
st.set_page_config(
    page_title="STC Operations AI Copilot",
    page_icon="🟣",
    layout="wide",
    initial_sidebar_state="expanded"
)
# ════════════════════════════════════════════════════════════════════
#  CSS احترافي - هوية STC بالألوان الأرجوانية والتصميم الداكن
# ════════════════════════════════════════════════════════════════════
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap');
    /* ─── القواعد العامة ─── */
    html, body, [class*="css"], .stApp {
        font-family: 'Cairo', 'Segoe UI', sans-serif !important;
        direction: RTL;
        text-align: right;
        background-color: #0d0e1a !important;
        color: #e2e8f0 !important;
    }
    /* ─── خلفية متدرجة للتطبيق ─── */
    .stApp {
        background: radial-gradient(ellipse at top left, #1a0a2e 0%, #0d0e1a 60%) !important;
    }
    /* ─── الشريط الجانبي ─── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #130b2b 0%, #0d0e1a 100%) !important;
        border-left: 1px solid rgba(79, 45, 127, 0.4) !important;
    }
    [data-testid="stSidebar"] * {
        direction: RTL;
        text-align: right;
    }
    /* ─── شريط التنقل في Sidebar ─── */
    .stRadio > div {
        direction: RTL;
    }
    .stRadio > div > label {
        direction: RTL;
        text-align: right !important;
        font-size: 14px;
        padding: 8px 12px;
        border-radius: 8px;
        transition: background 0.2s;
    }
    .stRadio > div > label:hover {
        background: rgba(79, 45, 127, 0.2) !important;
    }
    /* ─── الكروت والمناطق ─── */
    [data-testid="metric-container"] {
        background: rgba(79, 45, 127, 0.12) !important;
        border: 1px solid rgba(79, 45, 127, 0.35) !important;
        border-radius: 14px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(79, 45, 127, 0.15);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(79, 45, 127, 0.25);
    }
    [data-testid="stMetricValue"] {
        color: #c084fc !important;
        font-weight: 700;
        font-size: 22px;
    }
    [data-testid="stMetricLabel"] {
        color: #a78bfa !important;
        font-size: 13px;
    }
    /* ─── أزرار ─── */
    .stButton > button {
        background: linear-gradient(135deg, #4f2d7f 0%, #7c3aed 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px;
        font-weight: 700 !important;
        font-size: 15px;
        padding: 10px 24px;
        transition: all 0.25s !important;
        box-shadow: 0 4px 15px rgba(124, 58, 237, 0.35);
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(124, 58, 237, 0.5) !important;
    }
    .stButton > button:active {
        transform: translateY(0px) !important;
    }
    /* ─── زر التحميل ─── */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #065f46 0%, #059669 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px;
        font-weight: 700 !important;
        font-size: 15px;
        box-shadow: 0 4px 15px rgba(5, 150, 105, 0.35) !important;
        transition: all 0.25s !important;
    }
    .stDownloadButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(5, 150, 105, 0.5) !important;
    }
    /* ─── حقل الإدخال والقوائم ─── */
    .stTextInput input, .stSelectbox select, .stMultiSelect,
    [data-testid="stTextInput"] input {
        background: rgba(79, 45, 127, 0.1) !important;
        border: 1px solid rgba(79, 45, 127, 0.4) !important;
        border-radius: 10px !important;
        color: #e2e8f0 !important;
        direction: RTL !important;
    }
    .stTextInput input:focus, [data-testid="stTextInput"] input:focus {
        border-color: #7c3aed !important;
        box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.2) !important;
    }
    /* ─── الخطوط الفاصلة ─── */
    hr {
        border-color: rgba(79, 45, 127, 0.3) !important;
    }
    /* ─── رسائل النجاح والخطأ ─── */
    .stSuccess {
        background: rgba(5, 150, 105, 0.1) !important;
        border: 1px solid rgba(5, 150, 105, 0.3) !important;
        border-radius: 10px;
    }
    .stError {
        background: rgba(220, 38, 38, 0.1) !important;
        border: 1px solid rgba(220, 38, 38, 0.3) !important;
        border-radius: 10px;
    }
    .stInfo {
        background: rgba(79, 45, 127, 0.12) !important;
        border: 1px solid rgba(79, 45, 127, 0.3) !important;
        border-radius: 10px;
    }
    .stWarning {
        background: rgba(217, 119, 6, 0.1) !important;
        border: 1px solid rgba(217, 119, 6, 0.3) !important;
        border-radius: 10px;
    }
    /* ─── حاوية الدردشة مع الـ AI ─── */
    .chat-bubble-user {
        background: rgba(79, 45, 127, 0.25);
        border: 1px solid rgba(124, 58, 237, 0.4);
        border-radius: 16px 16px 4px 16px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 14px;
        direction: RTL;
    }
    .chat-bubble-ai {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(79, 45, 127, 0.3);
        border-radius: 16px 16px 16px 4px;
        padding: 14px 18px;
        margin: 8px 0;
        font-size: 14px;
        direction: RTL;
        line-height: 1.8;
    }
    .chat-avatar-ai {
        width: 28px; height: 28px;
        border-radius: 50%;
        background: linear-gradient(135deg, #4f2d7f, #7c3aed);
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 12px; margin-left: 8px;
    }
    /* ─── عنوان بطاقة الـ AI ─── */
    .ai-header-card {
        background: linear-gradient(135deg, rgba(79,45,127,0.3) 0%, rgba(124,58,237,0.15) 100%);
        border: 1px solid rgba(124, 58, 237, 0.4);
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 16px;
        direction: RTL;
    }
    /* ─── شاشة كلمة المرور ─── */
    .login-card {
        background: linear-gradient(135deg, rgba(79,45,127,0.25) 0%, rgba(30,10,60,0.8) 100%);
        border: 1px solid rgba(124, 58, 237, 0.5);
        border-radius: 24px;
        padding: 48px 40px;
        max-width: 480px;
        margin: 60px auto;
        box-shadow: 0 20px 60px rgba(79, 45, 127, 0.4);
        direction: RTL;
        text-align: center;
    }
    /* ─── عنوان STC ─── */
    .stc-logo-text {
        font-size: 52px;
        font-weight: 900;
        background: linear-gradient(135deg, #a855f7, #7c3aed, #4f2d7f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: 2px;
        line-height: 1;
    }
    .stc-tagline {
        color: #a78bfa;
        font-size: 15px;
        margin-top: 4px;
    }
    /* ─── شريط الفصل الأرجواني ─── */
    .purple-divider {
        height: 3px;
        background: linear-gradient(90deg, transparent, #7c3aed, #a855f7, #7c3aed, transparent);
        border-radius: 3px;
        margin: 12px 0;
    }
    /* ─── Spinner Shimmer ─── */
    @keyframes shimmer {
        0% { background-position: -200% center; }
        100% { background-position: 200% center; }
    }
    .loading-text {
        background: linear-gradient(90deg, #4f2d7f, #a855f7, #4f2d7f);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shimmer 2s linear infinite;
    }
    /* ─── DataFrames ─── */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(79, 45, 127, 0.3);
    }
    /* ─── File Uploader ─── */
    [data-testid="stFileUploader"] {
        background: rgba(79, 45, 127, 0.08) !important;
        border: 2px dashed rgba(124, 58, 237, 0.4) !important;
        border-radius: 14px !important;
        padding: 12px;
        transition: border-color 0.2s, background 0.2s;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: rgba(124, 58, 237, 0.7) !important;
        background: rgba(79, 45, 127, 0.14) !important;
    }
    /* ─── RTL كامل ─── */
    .stMarkdown, .stSelectbox, .stFileUploader, .stButton,
    .stMultiSelect, .stDateInput, .stTextArea, p, label {
        direction: RTL;
        text-align: right !important;
    }
    </style>
""", unsafe_allow_html=True)
# ════════════════════════════════════════════════════════════════════
#  🔒 بوابة كلمة المرور
# ════════════════════════════════════════════════════════════════════
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    col_l, col_c, col_r = st.columns([1, 1.4, 1])
    with col_c:
        st.markdown("""
        <div class="login-card">
            <div class="stc-logo-text">STC</div>
            <div class="stc-tagline">Operations AI Copilot</div>
            <div class="purple-divider" style="margin:20px 0;"></div>
            <p style="color:#94a3b8; font-size:14px; margin-bottom:24px;">
                🔐 هذا النظام مخصص لفريق عمليات STC فقط<br>أدخل كلمة المرور للمتابعة
            </p>
        </div>
        """, unsafe_allow_html=True)
        pwd_input = st.text_input(
            "كلمة المرور",
            type="password",
            placeholder="أدخل كلمة المرور هنا...",
            key="pwd_input",
            label_visibility="collapsed"
        )
        login_btn = st.button("🔓 دخول", use_container_width=True)
        if login_btn or (pwd_input and pwd_input == "333"):
            if pwd_input == "333":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة. حاول مرة أخرى.")
    st.stop()
# ════════════════════════════════════════════════════════════════════
#  تعريف الموديولات
# ════════════════════════════════════════════════════════════════════
MODULES = {
    "ai_copilot": {
        "name": "🤖 AI Operations Copilot",
        "desc": "مساعد الذكاء الاصطناعي لقسم العمليات. يفهم بياناتك، يحللها، ويجيب عن أي سؤال باللغة الطبيعية.",
        "id": 99,
        "files": [
            {"key": "portfolio", "label": "ملف المحفظة (.xlsx)", "required": True},
            {"key": "payments", "label": "ملف السدادات (.xlsx) - اختياري", "required": False}
        ]
    },
    "rotation": {
        "name": "🔄 السحب والتدوير",
        "desc": "سحب جميع عملاء محصل معين وإعادة توزيعهم بالتساوي على باقي المحصليين التابعين لنفس المشرف، مع الحفاظ على جميع مديونيات العميل الواحد لدى نفس المحصل الجديد.",
        "id": 6,
        "files": [
            {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
        ]
    },
    "contact": {
        "name": "📞 التوصل وعدم التوصل",
        "desc": "تحليل وتصنيف العملاء بناءً على حالات التواصل الرئيسية والفرعية والمتابعة للوصول إلى التصنيف النهائي وتتبع محاولات الاتصال.",
        "id": 2,
        "files": [
            {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
        ]
    },
    "targets": {
        "name": "🎯 العملاء المستهدفة",
        "desc": "تحديد العملاء ذوي الأولوية المرتفعة بناءً على متبقي السداد الموثق ونسب التغطية والتوجيهات المعتمدة.",
        "id": 7,
        "files": [
            {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
        ]
    },
    "neglect": {
        "name": "⏰ الإهمال والمتابعات",
        "desc": "تحليل وتصنيف حالات الإهمال وتحديد العملاء غير المتابعين بناءً على أيام المتابعة وآخر محاولة تواصل.",
        "id": 3,
        "files": [
            {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
        ]
    },
    "errors": {
        "name": "🔴 أخطاء النظام والوعود",
        "desc": "كشف وتوثيق الأخطاء في بيانات المحفظة والمطابقة مع وعود السداد النشطة أو المنتهية لتصحيح حالة العميل.",
        "id": 1,
        "files": [
            {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True},
            {"key": "promise", "label": "ملف وعود السداد (.xlsx) - اختياري", "required": False}
        ]
    },
    "balancing": {
        "name": "⚖️ سحب وتوزيع المحافظ",
        "desc": "إعادة توزيع العملاء من محافظ مصدر على محافظ هدف بخوارزمية ذكية تحقق توازناً مزدوجاً في عدد العملاء وإجمالي متبقي السداد بين جميع المحصلين المستهدفين.",
        "id": 8,
        "files": [
            {"key": "portfolio", "label": "ملف المحفظة الأساسية (.xlsx)", "required": True}
        ]
    },
    "operations": {
        "name": "📊 مركز تقارير العمليات",
        "desc": "تقرير يومي وأسبوعي وشهري شامل بنسب التغطية والسدادات ومتبقي المديونية مع Pivot Tables وDashboard تفاعلية دون أي تعديل على البيانات الأصلية.",
        "id": 9,
        "files": [
            {"key": "portfolio", "label": "ملف المحفظة الموزعة (.xlsx) - مطلوب", "required": True},
            {"key": "payments", "label": "ملف السدادات (.xlsx) - اختياري", "required": False}
        ]
    }
}
# ════════════════════════════════════════════════════════════════════
#  دوال مساعدة
# ════════════════════════════════════════════════════════════════════
def read_excel_calamine(file_path: str) -> pl.DataFrame:
    from python_calamine import CalamineWorkbook
    wb = CalamineWorkbook.from_path(file_path)
    sheet = wb.get_sheet_by_name(wb.sheet_names[0])
    data = sheet.to_python()
    if not data:
        return pl.DataFrame()
    headers = []
    seen = {}
    for i, h in enumerate(data[0]):
        h_str = str(h).strip() if h is not None else f"Column_{i}"
        if not h_str:
            h_str = f"Column_{i}"
        if h_str in seen:
            seen[h_str] += 1
            h_str = f"{h_str}_{seen[h_str]}"
        else:
            seen[h_str] = 0
        headers.append(h_str)
    records = data[1:]
    str_records = [
        [str(cell) if cell is not None else "" for cell in row]
        for row in records
    ]
    return pl.DataFrame(str_records, schema=headers, orient="row")
@st.cache_data
def scan_portfolio_for_balancing(file_path):
    try:
        df = read_excel_calamine(file_path)
        from modules.module8_balancing import PortfolioBalancingModule
        portfolios = PortfolioBalancingModule.get_portfolios(df)
        collector_map = PortfolioBalancingModule.get_collectors_per_portfolio(df)
        return portfolios, collector_map
    except Exception as e:
        st.error(f"حدث خطأ أثناء فحص الملف: {e}")
        return [], {}
@st.cache_data
def scan_portfolio_for_operations(file_path):
    try:
        df = read_excel_calamine(file_path)
        from modules.module9_operations_report import OperationsReportModule
        return OperationsReportModule.get_filter_options(df)
    except Exception as e:
        st.error(f"حدث خطأ أثناء فحص ملف العمليات: {e}")
        return {}
@st.cache_data
def scan_portfolio_for_rotation(file_path):
    try:
        df = read_excel_calamine(file_path)
        from modules.module6b_rotation import PortfolioRotationModule
        supervisors = PortfolioRotationModule.get_supervisors(df)
        mapping = {}
        for sup in supervisors:
            mapping[sup] = PortfolioRotationModule.get_collectors_for_supervisor(df, sup)
        return mapping
    except Exception as e:
        st.error(f"حدث خطأ أثناء فحص الملف: {e}")
        return None
@st.cache_data
def load_portfolio_df(file_path):
    """تحميل إطار البيانات من ملف المحفظة"""
    return read_excel_calamine(file_path)
def detect_supervisor_column(df: pl.DataFrame) -> str | None:
    """اكتشاف عمود المشرف تلقائياً"""
    candidates = ["اسم المشرف", "المشرف", "مشرف", "Supervisor", "supervisor"]
    for c in candidates:
        if c in df.columns:
            return c
    # fuzzy fallback
    for col in df.columns:
        if "مشرف" in col or "supervisor" in col.lower():
            return col
    return None
# ════════════════════════════════════════════════════════════════════
#  الشريط الجانبي - STC Header + Navigation
# ════════════════════════════════════════════════════════════════════
with st.sidebar:
    # شعار STC
    st.markdown("""
    <div style="text-align:center; padding: 20px 0 10px 0;">
        <div class="stc-logo-text">STC</div>
        <div class="stc-tagline">Operations AI Copilot</div>
        <div class="purple-divider"></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<p style='color:#a78bfa; font-size:13px; text-align:center; margin-bottom:12px;'>⚙️ البرامج المتاحة</p>", unsafe_allow_html=True)
    selected_key = st.radio(
        label="اختر البرنامج:",
        options=list(MODULES.keys()),
        format_func=lambda k: MODULES[k]["name"],
        label_visibility="collapsed"
    )
    st.markdown("<div class='purple-divider'></div>", unsafe_allow_html=True)
    # زر تسجيل الخروج
    if st.button("🔒 تسجيل الخروج", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.pop("ai_portfolio_df", None)
        st.session_state.pop("ai_payments_df", None)
        st.session_state.pop("chat_history", None)
        st.session_state.pop("ai_supervisors", None)
        st.rerun()
    st.markdown("""
    <div style='text-align:center; margin-top:20px; color:#475569; font-size:11px;'>
        STC Operations © 2026<br>جميع الحقوق محفوظة
    </div>
    """, unsafe_allow_html=True)
# ════════════════════════════════════════════════════════════════════
#  الرأس الرئيسي للصفحة
# ════════════════════════════════════════════════════════════════════
module_info = MODULES[selected_key]
# Header بطاقة عليا
if selected_key == "ai_copilot":
    st.markdown("""
    <div class="ai-header-card">
        <div style="display:flex; align-items:center; gap:16px; flex-direction:row-reverse;">
            <div style="font-size:48px; line-height:1;">🤖</div>
            <div>
                <div style="font-size:24px; font-weight:800; color:#e2e8f0;">
                    AI Operations Copilot
                </div>
                <div style="color:#a78bfa; font-size:14px; margin-top:4px;">
                    مساعد الذكاء الاصطناعي لقسم العمليات — يفهم بياناتك ويجيب عن أي سؤال
                </div>
                <div class="purple-divider" style="margin:10px 0 0 0; width:200px;"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div style="padding: 16px 0 8px 0;">
        <h2 style="color:#c084fc; font-weight:800; margin-bottom:4px;">{module_info['name']}</h2>
        <div class="purple-divider" style="width:120px;"></div>
    </div>
    """, unsafe_allow_html=True)
    st.info(module_info["desc"])
# ════════════════════════════════════════════════════════════════════
#  🤖 واجهة AI Operations Copilot
# ════════════════════════════════════════════════════════════════════
if selected_key == "ai_copilot":
    # تهيئة الحالة
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "ai_portfolio_df" not in st.session_state:
        st.session_state.ai_portfolio_df = None
    if "ai_payments_df" not in st.session_state:
        st.session_state.ai_payments_df = None
    if "ai_supervisors" not in st.session_state:
        st.session_state.ai_supervisors = []
    if "ai_selected_sups" not in st.session_state:
        st.session_state.ai_selected_sups = []
    # ─── قسم رفع الملفات ───
    st.markdown("#### 📂 رفع الملفات")
    col_p, col_pay = st.columns(2)
    with col_p:
        port_file = st.file_uploader("ملف المحفظة (.xlsx) *", type=["xlsx", "xls"], key="ai_port_file")
    with col_pay:
        pay_file = st.file_uploader("ملف السدادات (.xlsx) - اختياري", type=["xlsx", "xls"], key="ai_pay_file")
    if port_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(port_file.getbuffer())
            tmp_path = tmp.name
        try:
            df_port = load_portfolio_df(tmp_path)
            st.session_state.ai_portfolio_df = df_port
            sup_col = detect_supervisor_column(df_port)
            if sup_col:
                all_sups = sorted(df_port[sup_col].cast(pl.String).drop_nulls().unique().to_list())
                st.session_state.ai_supervisors = all_sups
            else:
                st.session_state.ai_supervisors = []
            st.success(f"✅ تم تحميل المحفظة — {len(df_port):,} عميل | {len(df_port.columns)} عمود")
        except Exception as e:
            st.error(f"خطأ في قراءة ملف المحفظة: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
    if pay_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(pay_file.getbuffer())
            tmp_path = tmp.name
        try:
            df_pay = load_portfolio_df(tmp_path)
            st.session_state.ai_payments_df = df_pay
            st.success(f"✅ تم تحميل السدادات — {len(df_pay):,} صف")
        except Exception as e:
            st.error(f"خطأ في قراءة ملف السدادات: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
    # ─── فلتر المشرفين ───
    if st.session_state.ai_portfolio_df is not None:
        st.markdown("<div class='purple-divider'></div>", unsafe_allow_html=True)
        st.markdown("#### 👥 تحديد نطاق العمل (المشرفين)")
        st.caption("اختر المشرفين الذين تريد أن يعمل الـ AI على بياناتهم. اتركها فارغة للعمل على الكل.")
        sups_all = st.session_state.ai_supervisors
        if sups_all:
            selected_sups = st.multiselect(
                "اختر المشرفين:",
                options=sups_all,
                default=st.session_state.ai_selected_sups,
                key="sup_multiselect",
                label_visibility="collapsed"
            )
            st.session_state.ai_selected_sups = selected_sups
            if selected_sups:
                st.info(f"🔍 العمل على: {', '.join(selected_sups)} ({len(selected_sups)} مشرف)")
            else:
                st.info("🌐 العمل على المحفظة الكاملة (جميع المشرفين)")
        else:
            st.warning("⚠️ لم يتم اكتشاف عمود المشرفين تلقائياً. سيعمل الـ AI على كامل المحفظة.")
        # ─── واجهة الدردشة ───
        st.markdown("<div class='purple-divider'></div>", unsafe_allow_html=True)
        st.markdown("#### 🧠 تحدث مع AI Operations Copilot")
        # عرض رسائل المحادثة
        chat_container = st.container()
        with chat_container:
            if not st.session_state.chat_history:
                st.markdown("""
                <div class="chat-bubble-ai">
                    <strong>🤖 مرحباً!</strong> أنا AI Operations Copilot الخاص بـ STC.<br><br>
                    يمكنني الإجابة عن أي سؤال حول محفظتك. جرب مثلاً:<br>
                    • <em>كم نسبة التغطية اليوم؟</em><br>
                    • <em>كم عدد العملاء الإجمالي؟</em><br>
                    • <em>من أفضل مشرف في المحفظة؟</em><br>
                    • <em>ما توصيتك لتحسين الأداء؟</em><br>
                    • <em>كم إجمالي متبقي السداد؟</em>
                </div>
                """, unsafe_allow_html=True)
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div class="chat-bubble-user">
                        <strong>👤 أنت:</strong><br>{msg['content']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="chat-bubble-ai">
                        <strong>🤖 AI Copilot:</strong><br>{msg['content']}
                    </div>
                    """, unsafe_allow_html=True)
        # حقل الإدخال
        col_q, col_send = st.columns([5, 1])
        with col_q:
            user_question = st.text_input(
                "اسأل الـ AI...",
                placeholder="مثال: كم نسبة التغطية اليوم؟",
                key="ai_question",
                label_visibility="collapsed"
            )
        with col_send:
            send_btn = st.button("✉️ إرسال", use_container_width=True)
        col_clr, _ = st.columns([1, 4])
        with col_clr:
            if st.button("🗑️ مسح المحادثة", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
if send_btn and user_question and user_question.strip():

    # حفظ سؤال المستخدم
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_question
    })

    # تشغيل الـ AI
    with st.spinner("🤖 AI يحلل بياناتك..."):
        try:
            from core.knowledge_base import CopilotKnowledgeBase
            from core.ai_copilot import AIOperationsCopilot

            kb = CopilotKnowledgeBase()

            copilot = AIOperationsCopilot(
                portfolio_df=st.session_state.ai_portfolio_df,
                payments_df=st.session_state.ai_payments_df,
                kb=kb
            )

            answer = copilot.ask(
                question=user_question,
                selected_supervisors=st.session_state.ai_selected_sups or None
            )

        except Exception as e:
            answer = f"⚠️ حدث خطأ أثناء تحليل البيانات: {e}"

    # حفظ رد الـ AI
    st.session_state.chat_history.append({
        "role": "ai",
        "content": answer
    })

    # مسح مربع الكتابة حتى لا يعيد إرسال السؤال مرة أخرى
    st.session_state.ai_question = ""

    # إعادة تحميل الصفحة لإظهار الرد
    st.rerun()
    else:
        st.markdown("""
        <div style="
            text-align:center;
            padding: 60px 20px;
            color: #64748b;
            border: 2px dashed rgba(79,45,127,0.3);
            border-radius: 20px;
            margin-top: 24px;
        ">
            <div style="font-size:64px; margin-bottom:16px;">🤖</div>
            <div style="font-size:18px; color:#a78bfa; font-weight:600;">
                ارفع ملف المحفظة للبدء
            </div>
            <div style="font-size:14px; color:#64748b; margin-top:8px;">
                سيقوم AI Operations Copilot بتحليل بياناتك فور رفع الملف
            </div>
        </div>
        """, unsafe_allow_html=True)
# ════════════════════════════════════════════════════════════════════
#  واجهة باقي الموديولات (الموديولات الأصلية كما هي)
# ════════════════════════════════════════════════════════════════════
else:
    # ─── قسم رفع الملفات ───
    st.markdown("#### 📂 رفع الملفات المطلوبة")
    uploaded_files = {}
    cols_upload = st.columns(len(module_info["files"]))
    for i, fspec in enumerate(module_info["files"]):
        with cols_upload[i]:
            uploaded_files[fspec["key"]] = st.file_uploader(
                label=fspec["label"],
                type=["xlsx", "xls"],
                key=f"{selected_key}_{fspec['key']}"
            )
    # ─── معطيات السحب والتدوير ───
    rotation_params = {}
    if selected_key == "rotation" and uploaded_files.get("portfolio"):
        portfolio_file = uploaded_files["portfolio"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_scan:
            tmp_scan.write(portfolio_file.getbuffer())
            tmp_scan_path = tmp_scan.name
        try:
            mapping = scan_portfolio_for_rotation(tmp_scan_path)
            if mapping:
                st.markdown("#### 🔄 إعدادات السحب وإعادة التوزيع")
                c1, c2 = st.columns(2)
                with c1:
                    selected_sup = st.selectbox(
                        "1. اختر اسم المشرف المسؤول:",
                        options=["-- اختر المشرف --"] + sorted(list(mapping.keys()))
                    )
                with c2:
                    if selected_sup and selected_sup != "-- اختر المشرف --":
                        collectors = sorted(mapping[selected_sup])
                        selected_col = st.selectbox(
                            "2. اسم المحصل المطلوب سحب محفظته:",
                            options=["-- اختر المحصل --"] + collectors
                        )
                    else:
                        st.selectbox("2. اسم المحصل المطلوب سحب محفظته:", ["-- اختر المشرف أولاً --"], disabled=True)
                        selected_col = None
                if selected_sup and selected_sup != "-- اختر Supervisor --" and selected_col and selected_col != "-- اختر المحصل --":
                    pool = [c for c in mapping[selected_sup] if c != selected_col]
                    if len(pool) == 0:
                        st.error(f"⚠️ لا يوجد محصلون آخرون تحت إشراف '{selected_sup}'!")
                    else:
                        st.success(f"✅ سيتم سحب عملاء **'{selected_col}'** وتوزيعهم على **{len(pool)} محصلين** تحت إشراف **'{selected_sup}'**.")
                        rotation_params["supervisor"] = selected_sup
                        rotation_params["collector"] = selected_col
        finally:
            try:
                os.unlink(tmp_scan_path)
            except:
                pass
    # ─── واجهة سحب وتوزيع المحافظ ───
    balancing_params = {}
    source_ports: list = []
    target_ports: list = []
    if selected_key == "balancing" and uploaded_files.get("portfolio"):
        portfolio_file = uploaded_files["portfolio"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_scan:
            tmp_scan.write(portfolio_file.getbuffer())
            tmp_scan_path = tmp_scan.name
        try:
            portfolios, collector_map = scan_portfolio_for_balancing(tmp_scan_path)
            if portfolios:
                st.markdown("#### ⚖️ تحديد المحافظ")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("المحافظ المصدر (السحب منها):")
                    source_ports = st.multiselect(
                        label="اختر محفظة أو أكثر لسحب عملائها:",
                        options=portfolios,
                        key="bal_source",
                        label_visibility="collapsed"
                    )
                    if source_ports:
                        total_source_col = sum(len(collector_map.get(p, [])) for p in source_ports)
                        st.info(f"👥 عدد المحصلين في المحافظ المصدر: **{total_source_col}**")
                with c2:
                    st.markdown("المحافظ الهدف (التوزيع عليها):")
                    available_targets = [p for p in portfolios if p not in (source_ports or [])]
                    target_ports = st.multiselect(
                        label="اختر محفظة أو أكثر للتوزيع عليها:",
                        options=available_targets,
                        key="bal_target",
                        label_visibility="collapsed"
                    )
                    if target_ports:
                        total_target_col = sum(len(collector_map.get(p, [])) for p in target_ports)
                        st.info(f"👥 عدد المحصلين في المحافظ الهدف: **{total_target_col}**")
                if source_ports:
                    if target_ports:
                        overlap = set(source_ports) & set(target_ports)
                        if overlap:
                            st.error(f"⚠️ لا يمكن أن تكون المحفظة مصدراً وهدفاً في نفس الوقت: {', '.join(overlap)}")
                        else:
                            st.success(f"✅ سيتم سحب عملاء **{' | '.join(source_ports)}** وتوزيعهم على محصلي **{' | '.join(target_ports)}**.")
                    else:
                        st.success(f"✅ سيتم سحب وتوزيع عملاء **{' | '.join(source_ports)}** بالتساوي داخل كل محفظة.")
                    st.markdown("##### ⚙️ إعدادات التوزيع المتقدمة")
                    min_chunk = st.number_input(
                        "الحد الأدنى لعدد العملاء:",
                        min_value=50, max_value=1000, value=150, step=10
                    )
                    balancing_params["source"] = source_ports
                    balancing_params["target"] = target_ports if target_ports else None
                    balancing_params["chunk"] = min_chunk
        finally:
            try:
                os.unlink(tmp_scan_path)
            except:
                pass
    # ─── واجهة مركز تقارير العمليات ───
    ops_params = {}
    if selected_key == "operations" and uploaded_files.get("portfolio"):
        portfolio_file = uploaded_files["portfolio"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_scan:
            tmp_scan.write(portfolio_file.getbuffer())
            tmp_scan_path = tmp_scan.name
        try:
            filter_options = scan_portfolio_for_operations(tmp_scan_path)
            if filter_options:
                st.markdown("---")
                st.markdown("### 🏢 Reports Center - مركز التقارير")
                st.info("اختر نوع التقرير والفترة الزمنية والخيارات المطلوب استخراجها:")
                col_mode, _ = st.columns([3, 1])
                with col_mode:
                    rep_type = st.radio(
                        "اختر نوع التقرير المطلوب:",
                        options=["📅 Daily Report (تقرير يومي)", "🗓 Weekly Report (تقرير أسبوعي)", "📆 Monthly Report (تقرير شهري)"],
                        index=0,
                        horizontal=True
                    )
                st.markdown("##### ⏱️ إعدادات الفترة الزمنية")
                if "Daily" in rep_type:
                    ops_params["report_mode"] = "daily"
                    d_val = st.date_input("تاريخ التقرير اليومي:", datetime.today())
                    ops_params["target_date"] = d_val.strftime("%Y-%m-%d")
                elif "Weekly" in rep_type:
                    ops_params["report_mode"] = "weekly"
                    w_cols = st.columns(2)
                    with w_cols[0]:
                        s_val = st.date_input("تاريخ البداية:", datetime.today() - timedelta(days=6))
                    with w_cols[1]:
                        e_val = st.date_input("تاريخ النهاية:", datetime.today())
                    ops_params["start_date"] = s_val.strftime("%Y-%m-%d")
                    ops_params["end_date"] = e_val.strftime("%Y-%m-%d")
                elif "Monthly" in rep_type:
                    ops_params["report_mode"] = "monthly"
                    m_cols = st.columns(2)
                    curr_y = datetime.today().year
                    curr_m = datetime.today().month
                    with m_cols[0]:
                        m_val = st.selectbox("الشهر:", options=list(range(1, 13)), index=curr_m - 1)
                    with m_cols[1]:
                        y_val = st.selectbox("السنة:", options=list(range(2023, 2031)),
                                             index=list(range(2023, 2031)).index(curr_y) if curr_y in range(2023, 2031) else 0)
                    ops_params["month"] = m_val
                    ops_params["year"] = y_val
                st.markdown("##### 🔍 فلاتر مخصصة (اختياري)")
                f_col1, f_col2, f_col3 = st.columns(3)
                with f_col1:
                    sups_sel = st.multiselect("المشرفين:", filter_options.get("supervisors", []))
                    cols_sel = st.multiselect("المحصلين:", filter_options.get("collectors", []))
                with f_col2:
                    ports_sel = st.multiselect("المحافظ:", filter_options.get("portfolios", []))
                    mstat_sel = st.multiselect("الحالة الرئيسية:", filter_options.get("main_statuses", []))
                with f_col3:
                    sstat_sel = st.multiselect("الحالة الفرعية:", filter_options.get("sub_statuses", []))
                ops_params["supervisors"] = sups_sel if sups_sel else None
                ops_params["collectors"] = cols_sel if cols_sel else None
                ops_params["portfolios"] = ports_sel if ports_sel else None
                ops_params["main_statuses"] = mstat_sel if mstat_sel else None
                ops_params["sub_statuses"] = sstat_sel if sstat_sel else None
        finally:
            try:
                os.unlink(tmp_scan_path)
            except:
                pass
    # ─── التحقق من الجاهزية ───
    ready_to_run = True
    for fspec in module_info["files"]:
        if fspec["required"] and not uploaded_files.get(fspec["key"]):
            ready_to_run = False
    if selected_key == "rotation" and not rotation_params:
        ready_to_run = False
    if selected_key == "balancing" and not balancing_params:
        ready_to_run = False
    if selected_key == "operations" and not ops_params:
        ready_to_run = False
    # ─── زر التشغيل ───
    st.markdown("<div class='purple-divider'></div>", unsafe_allow_html=True)
    if st.button("🚀 تشغيل التحليل والمعالجة", disabled=not ready_to_run, use_container_width=True):
        temp_files = []
        path_map = {}
        try:
            with st.spinner("⏳ جاري قراءة وتجهيز الملفات..."):
                for key, file_obj in uploaded_files.items():
                    if file_obj:
                        suffix = os.path.splitext(file_obj.name)[1] or ".xlsx"
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(file_obj.getbuffer())
                            tmp_path = tmp.name
                            temp_files.append(tmp_path)
                            if key == "portfolio":
                                path_map[MAIN_PORTFOLIO] = tmp_path
                            elif key == "promise":
                                path_map[PROMISE_PAY] = tmp_path
                            elif key == "payments":
                                path_map["payments"] = tmp_path
                dfs, results = load_files(path_map)
                for k, vr in results.items():
                    if not vr.is_valid:
                        st.error(f"❌ الملف {k} غير صالح: {vr.summary()}")
                        st.stop()
                portfolio = dfs.get(MAIN_PORTFOLIO)
                promise = dfs.get(PROMISE_PAY, pl.DataFrame())
            with st.spinner("⚙️ جاري معالجة البيانات وتطبيق القواعد الحسابية..."):
                task_id = module_info["id"]
                stats = {}
                out_fd, out_path = tempfile.mkstemp(suffix=".xlsx")
                os.close(out_fd)
                temp_files.append(out_path)
                writer = ExcelReportWriter(out_path)
                if task_id == 1:
                    from modules.module1_errors import SystemErrorsModule
                    r = SystemErrorsModule().run(portfolio, promise)
                    stats.update(r["stats"])
                    writer.write_errors(r["data"])
                elif task_id == 2:
                    from modules.module2_contact import ContactStatusModule
                    r = ContactStatusModule().run(portfolio)
                    stats.update(r["stats"])
                    writer.write_contact(r["data"], r["pivot_supervisor"], r["pivot_collector"], r["pivot_status"])
                elif task_id == 3:
                    from modules.module3_neglect import NeglectModule
                    r = NeglectModule().run(portfolio)
                    stats.update(r["stats"])
                    writer.write_neglect(r["data"], r["full_analysis"], r["pivot_summary"],
                                         r["pivot_supervisor"], r["pivot_collector"], r["pivot_status"],
                                         r["pivot_branch"], r["pivot_portfolio"], r["pivot_days"])
                elif task_id == 7:
                    from modules.module7_targets import TargetCustomersModule
                    r = TargetCustomersModule().run(portfolio, promise, pl.DataFrame())
                    stats.update(r["stats"])
                    writer.write_targets(r["data"], r["pivot_supervisor"])
                elif task_id == 6:
                    sup = rotation_params["supervisor"]
                    col = rotation_params["collector"]
                    from modules.module6b_rotation import PortfolioRotationModule
                    r = PortfolioRotationModule().run(portfolio, col, sup)
                    stats.update(r["stats"])
                    writer.write_rotation(r["data"], r["execution_report"],
                                          r["distribution_summary"], r["withdrawal_summary"])
                elif task_id == 8:
                    from modules.module8_balancing import PortfolioBalancingModule
                    tgt = balancing_params.get("target") or None
                    r = PortfolioBalancingModule().run(
                        portfolio,
                        source_portfolios=balancing_params["source"],
                        target_portfolios=tgt,
                        min_receiver_chunk=balancing_params.get("chunk", 200)
                    )
                    stats.update(r["stats"])
                    writer.write_balancing(r["data"], r["summary_pivot"],
                                           r.get("planning_sheet"), r.get("source_summary"),
                                           r.get("final_result_sheet"))
                elif task_id == 9:
                    from modules.module9_operations_report import OperationsReportModule
                    pmt_df = dfs.get("payments")
                    r = OperationsReportModule().run(
                        portfolio,
                        payments=pmt_df,
                        report_mode=ops_params.get("report_mode", "daily"),
                        target_date=ops_params.get("target_date"),
                        start_date=ops_params.get("start_date"),
                        end_date=ops_params.get("end_date"),
                        month=ops_params.get("month"),
                        year=ops_params.get("year"),
                        supervisors=ops_params.get("supervisors"),
                        collectors=ops_params.get("collectors"),
                        portfolios=ops_params.get("portfolios"),
                        main_statuses=ops_params.get("main_statuses"),
                        sub_statuses=ops_params.get("sub_statuses"),
                    )
                    stats.update(r["stats"])
                    writer.write_operations_report(
                        r["data"], r["pivot_supervisor"], r["pivot_collector"],
                        r["pivot_portfolio"], r.get("pivot_main_status"), r.get("pivot_sub_status"),
                        r.get("top10_supervisors"), r.get("top10_collectors"),
                        r.get("top10_portfolios"), r["stats"],
                    )
                writer.write_dashboard(stats, task_id)
                writer.write_summary(stats)
                writer.save()
            st.balloons()
            st.success("✨ اكتملت معالجة البيانات بنجاح وتم إنشاء التقرير المنسق!")
            # ─── عرض الإحصائيات ───
            st.markdown("#### 📊 ملخص نتائج التقرير")
            stats_cols = st.columns(min(len(stats), 4))
            for j, (k, v) in enumerate(stats.items()):
                col_idx = j % len(stats_cols)
                with stats_cols[col_idx]:
                    st.metric(label=k, value=str(v))
            # جدول توزيع المحصلين
            if task_id == 8 and 'r' in locals() and "summary_pivot" in r:
                st.markdown("---")
                st.markdown("#### 📋 جدول ملخص التوزيع النهائي للمحصلين")
                summary_df = r["summary_pivot"]
                target_cols = ["المحصل", "المحصل الجديد", "اليوزر", "عدد العملاء بعد", "عدد العملاء", "إجمالي متبقي السداد"]
                cols_to_show = [c for c in target_cols if c in summary_df.columns]
                if cols_to_show:
                    show_df = summary_df.select(cols_to_show)
                    first_col = cols_to_show[0]
                    show_df = show_df.filter(~pl.col(first_col).cast(pl.String).str.contains("📉|📈"))
                    st.dataframe(show_df.to_pandas(), use_container_width=True, hide_index=True)
            # ─── زر التحميل ───
            with open(out_path, "rb") as f_out:
                excel_bytes = f_out.read()
            ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            download_name = f"مهاره_{selected_key}_{ts_str}.xlsx"
            st.markdown("<div class='purple-divider'></div>", unsafe_allow_html=True)
            st.download_button(
                label="📥 تحميل التقرير النهائي (Excel Styled)",
                data=excel_bytes,
                file_name=download_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.exception(e)
            st.error(f"❌ حدث خطأ أثناء تشغيل النظام: {e}")
        finally:
            for p in temp_files:
                try:
                    os.unlink(p)
                except:
                    pass
