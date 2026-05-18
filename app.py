import base64
import json
from datetime import date
from html import escape
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import streamlit as st

from db import find_faq, init_db, save_chat
from supabase_client import (
    add_recording_for_student,
    forget_auth_session,
    get_client,
    get_student_portal,
    get_student_profiles,
    has_admin_service_role_key,
    request_email_otp,
    sign_in,
    sign_up,
    update_password,
    update_student_access,
    verify_email_otp,
)
from utils import get_groq_answer


st.set_page_config(
    page_title="Guitar Class",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

ASSET_DIR = Path(__file__).parent / "assets"
TUTOR_VIDEO_PATH = ASSET_DIR / "tutor_intro.mp4"
TUTOR_PHOTO_PATH = ASSET_DIR / "tutor_photo.jpeg"
BACKGROUND_IMAGE_PATH = ASSET_DIR / "background.jpeg"

if BACKGROUND_IMAGE_PATH.exists():
    background_data = base64.b64encode(BACKGROUND_IMAGE_PATH.read_bytes()).decode("ascii")
    BACKGROUND_IMAGE_URL = f"data:image/jpeg;base64,{background_data}"
else:
    BACKGROUND_IMAGE_URL = ""

if "light_theme" not in st.session_state:
    st.session_state.light_theme = False

if "translate_hindi" not in st.session_state:
    st.session_state.translate_hindi = False

TRANSLATIONS = {
    "hi": {
        "Live online guitar coaching": "लाइव ऑनलाइन गिटार कोचिंग",
        "Guitar Class - Learn with a Pro": "गिटार क्लास - प्रो से सीखें",
        "Practical guitar lessons for beginners and growing players, focused on songs, rhythm, chords, technique, and personal feedback.": "शुरुआती और आगे बढ़ रहे विद्यार्थियों के लिए व्यावहारिक गिटार लेसन, जिनमें गीत, रिदम, कॉर्ड्स, तकनीक और व्यक्तिगत फीडबैक पर ध्यान दिया जाता है.",
        "Meet Ashutosh": "आशुतोष से मिलें",
        "Meet who you learn from": "जिससे आप सीखेंगे उनसे मिलें",
        "Watch Ashutosh performing live on stage and get a feel for the musicality, confidence, and real performance experience behind the classes.": "आशुतोष को स्टेज पर लाइव परफॉर्म करते देखें और क्लासेस के पीछे की संगीत समझ, आत्मविश्वास और वास्तविक परफॉर्मेंस अनुभव को महसूस करें.",
        "What you sign up for": "आपको क्या मिलेगा",
        "Structured guitar learning with clear practice targets, live feedback, beginner-friendly explanations, and access to class details after fee confirmation. Batch formation will be started soon for upcoming learners.": "स्पष्ट प्रैक्टिस लक्ष्य, लाइव फीडबैक, शुरुआती छात्रों के लिए आसान समझाइश, और फीस कन्फर्म होने के बाद क्लास डिटेल्स का एक्सेस. नए विद्यार्थियों के लिए बैच जल्द शुरू होंगे.",
        "Personal guidance, clear progress": "व्यक्तिगत मार्गदर्शन, स्पष्ट प्रगति",
        "Learn songs, rhythm, chords, and technique with practical feedback after every session.": "हर सेशन के बाद व्यावहारिक फीडबैक के साथ गीत, रिदम, कॉर्ड्स और तकनीक सीखें.",
        "Before you register": "रजिस्टर करने से पहले",
        "The stage performance video gives students and parents a clear sense of Ashutosh's command over the instrument, stage presence, and the kind of musical confidence students can build through consistent practice.": "स्टेज परफॉर्मेंस वीडियो से विद्यार्थियों और माता-पिता को आशुतोष की गिटार पर पकड़, स्टेज उपस्थिति, और नियमित अभ्यास से बनने वाले संगीत आत्मविश्वास की स्पष्ट झलक मिलती है.",
        "Join our guitar classes": "हमारी गिटार क्लासेस से जुड़ें",
        "New batch formation will be started soon": "नया बैच जल्द शुरू होगा",
        "Weekly group and 1:1 sessions": "साप्ताहिक ग्रुप और 1:1 सेशन",
        "Pop, Rock, Blues, and Classical foundations": "पॉप, रॉक, ब्लूज़ और क्लासिकल की बुनियाद",
        "Beginner-friendly lessons with flexible online timings": "लचीले ऑनलाइन समय के साथ शुरुआती छात्रों के लिए आसान लेसन",
        "Practice plans, technique feedback, and song-based learning": "प्रैक्टिस प्लान, तकनीक फीडबैक और गीत-आधारित सीखना",
        "How sessions work": "सेशन कैसे चलते हैं",
        "Live classes are hosted online. Students learn through guided exercises, song walkthroughs, chord progressions, rhythm practice, and personal feedback.": "लाइव क्लासेस ऑनलाइन होती हैं. विद्यार्थी गाइडेड एक्सरसाइज, गीत वॉकथ्रू, कॉर्ड प्रोग्रेशन, रिदम प्रैक्टिस और व्यक्तिगत फीडबैक के ज़रिए सीखते हैं.",
        "Student Dashboard": "स्टूडेंट डैशबोर्ड",
        "Account": "अकाउंट",
        "Payment status": "पेमेंट स्टेटस",
        "Next session": "अगला सेशन",
        "Class access": "क्लास एक्सेस",
        "Active": "एक्टिव",
        "Pending": "पेंडिंग",
        "Fee confirmation pending": "फीस कन्फर्मेशन बाकी है",
        "Shared after fee confirmation": "फीस कन्फर्म होने के बाद साझा किया जाएगा",
        "Pay Fees": "फीस भरें",
        "Complete your payment to unlock live session access and recordings.": "लाइव सेशन एक्सेस और रिकॉर्डिंग्स अनलॉक करने के लिए पेमेंट पूरा करें.",
        "Session Details": "सेशन डिटेल्स",
        "Paid students can access upcoming live class details and shared recordings here.": "फीस भर चुके विद्यार्थी यहां आने वाली लाइव क्लास डिटेल्स और साझा रिकॉर्डिंग्स देख सकते हैं.",
        "Next Session": "अगला सेशन",
        "Live Class": "लाइव क्लास",
        "Session Notes": "सेशन नोट्स",
        "Open live session": "लाइव सेशन खोलें",
        "Open session notes": "सेशन नोट्स खोलें",
        "Session Recordings": "सेशन रिकॉर्डिंग्स",
        "Open recording": "रिकॉर्डिंग खोलें",
        "FAQ Chat": "FAQ चैट",
        "Ask about schedules, fees, practice routines, lesson levels, or getting started.": "शेड्यूल, फीस, प्रैक्टिस रूटीन, लेसन लेवल या शुरुआत करने के बारे में पूछें.",
    }
}


def tr(text):
    if st.session_state.get("translate_hindi"):
        return TRANSLATIONS["hi"].get(text, text)
    return text


st.sidebar.markdown("### Site Controls")
st.sidebar.toggle(
    "Light theme",
    key="light_theme",
    help="Switch between the default dark style and a lighter reading theme.",
)
st.sidebar.toggle(
    "Hindi translation",
    key="translate_hindi",
    help="Translate the main student-facing site copy between English and Hindi.",
)
if st.sidebar.button(
    "Privacy Policy",
    help="We only collect details needed for class registration, payment confirmation, student access, and support. Login data is handled through Supabase authentication.",
):
    st.sidebar.info(
        "Privacy policy: student details are used for registration, fee confirmation, "
        "class access, session communication, and support. They are not sold or shared "
        "for advertising."
    )

st.markdown(
    """
    <style>
        #MainMenu, footer {
            visibility: hidden;
        }

        .stApp {
            background:
                radial-gradient(circle at 22% 14%, rgba(216, 180, 106, 0.18), transparent 24rem),
                radial-gradient(circle at 86% 22%, rgba(105, 132, 190, 0.14), transparent 28rem),
                linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px),
                #0f1117;
            background-size: auto, auto, 44px 44px, 44px 44px, auto;
            background-attachment: fixed;
        }

        .block-container {
            max-width: 1180px;
            padding-top: 4.5rem;
            padding-bottom: 4rem;
        }

        [data-testid="stSidebar"] {
            background: #17191f;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        [data-testid="stSidebar"] [data-testid="stForm"] {
            border: 0;
            background: transparent;
            padding: 0;
        }

        [data-testid="stSidebar"] .stTabs [data-baseweb="tab-list"] {
            gap: 0.35rem;
        }

        [data-testid="stSidebar"] .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 0.55rem 0.8rem;
        }

        [data-testid="stSidebar"] .stTextInput input {
            border-radius: 8px;
        }

        .stButton button,
        .stFormSubmitButton button {
            border-radius: 8px;
            font-weight: 700;
        }

        .title-row {
            margin-bottom: 1.8rem;
        }

        .eyebrow {
            color: #d8b46a;
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.6rem;
        }

        .page-title {
            font-size: clamp(2.5rem, 5vw, 4.8rem);
            line-height: 1;
            font-weight: 900;
            margin: 0;
            max-width: 900px;
        }

        .lead {
            color: rgba(255, 255, 255, 0.78);
            font-size: 1.08rem;
            line-height: 1.65;
            max-width: 820px;
            margin-top: 1.15rem;
            text-align: justify;
            text-justify: inter-word;
            overflow-wrap: break-word;
            hyphens: auto;
        }

        .section-title {
            font-size: 1.55rem;
            font-weight: 850;
            margin: 0 0 0.8rem;
        }

        .info-panel {
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.035);
            padding: 1.2rem 1.25rem;
            min-height: 170px;
        }

        .info-panel p,
        .info-panel li {
            color: rgba(255, 255, 255, 0.78);
            line-height: 1.6;
        }

        .info-panel p,
        .media-panel p,
        .portal-card p,
        .chat-message p {
            text-align: justify;
            text-justify: inter-word;
            overflow-wrap: break-word;
            hyphens: auto;
        }

        .info-panel ul {
            margin-bottom: 0;
            padding-left: 1.1rem;
        }

        .intro-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.05fr) minmax(280px, 0.95fr);
            gap: 1rem;
            align-items: stretch;
            margin: 1.2rem 0 1rem;
        }

        .media-panel {
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.035);
            height: 100%;
            min-height: 250px;
            overflow: hidden;
            padding: 1rem;
        }

        .media-panel p {
            color: rgba(255, 255, 255, 0.78);
            line-height: 1.6;
            margin-bottom: 0;
        }

        .media-panel img,
        .media-panel video {
            width: 100%;
            border-radius: 8px;
        }

        .media-placeholder {
            align-items: center;
            color: rgba(255, 255, 255, 0.68);
            display: flex;
            min-height: 230px;
            justify-content: center;
            line-height: 1.55;
            text-align: center;
        }

        .tutor-intro {
            display: grid;
            grid-template-columns: minmax(120px, 180px) minmax(220px, 1fr);
            gap: 1rem;
            align-items: center;
        }

        .tutor-intro img {
            aspect-ratio: 1;
            object-fit: cover;
        }

        .tutor-copy {
            min-width: 0;
        }

        .tutor-copy .section-title {
            font-size: clamp(1.25rem, 2.4vw, 1.7rem);
            line-height: 1.15;
            overflow-wrap: normal;
            word-break: normal;
        }

        .kpi-strip {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(112px, 1fr));
            gap: 0.75rem;
            margin: 1rem -0.35rem 0;
        }

        .video-banner {
            margin: 1rem 0;
        }

        .video-banner .media-placeholder {
            min-height: 360px;
        }

        .video-banner [data-testid="stVideo"] {
            border-radius: 8px;
            overflow: hidden;
        }

        .tutor-row {
            margin: 1.1rem 0 1.4rem;
        }

        .class-info-row {
            margin-top: 1.3rem;
        }

        .side-panel-stack {
            display: grid;
            gap: 1rem;
        }

        .side-panel-stack .info-panel,
        .side-panel-stack .media-panel {
            min-height: 0;
        }

        .kpi-strip .metric-card {
            min-width: 0;
        }

        .kpi-strip .metric-label,
        .kpi-strip .metric-value {
            overflow-wrap: normal;
            word-break: normal;
        }

        .site-footer {
            border-top: 1px solid rgba(255, 255, 255, 0.11);
            color: rgba(255, 255, 255, 0.62);
            font-size: 0.9rem;
            margin-top: 2.6rem;
            padding-top: 1.2rem;
            text-align: center;
        }

        .divider {
            height: 1px;
            background: rgba(255, 255, 255, 0.11);
            margin: 2.3rem 0 2rem;
        }

        .chat-shell {
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.03);
            padding: 1.1rem;
            margin-top: 1rem;
        }

        .chat-message {
            border-radius: 8px;
            padding: 0.85rem 1rem;
            margin-bottom: 0.7rem;
            line-height: 1.55;
        }

        .chat-user {
            background: rgba(216, 180, 106, 0.14);
            border: 1px solid rgba(216, 180, 106, 0.26);
        }

        .chat-assistant {
            background: rgba(255, 255, 255, 0.055);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .chat-role {
            color: rgba(255, 255, 255, 0.55);
            display: block;
            font-size: 0.78rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
            text-transform: uppercase;
        }

        .metric-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1rem;
            margin: 1rem 0 1.2rem;
        }

        .metric-card {
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.035);
            padding: 1rem;
        }

        .metric-label {
            color: rgba(255, 255, 255, 0.55);
            font-size: 0.78rem;
            font-weight: 800;
            text-transform: uppercase;
        }

        .metric-value {
            color: #f7f3ea;
            font-size: 2rem;
            font-weight: 900;
            margin-top: 0.25rem;
        }

        .portal-grid {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
            gap: 1rem;
            margin-top: 1rem;
        }

        .portal-card {
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.035);
            padding: 1.15rem;
        }

        .portal-card p {
            color: rgba(255, 255, 255, 0.78);
            line-height: 1.6;
            margin-bottom: 0.7rem;
        }

        .metric-card p,
        .media-placeholder p,
        .site-footer p,
        [data-testid="stSidebar"] p {
            text-align: left;
        }

        .session-link {
            display: inline-block;
            border-radius: 8px;
            background: #d8b46a;
            color: #17191f !important;
            font-weight: 900;
            padding: 0.75rem 1rem;
            text-decoration: none !important;
        }

        @media (max-width: 800px) {
            .metric-row,
            .portal-grid,
            .intro-grid,
            .kpi-strip {
                grid-template-columns: 1fr;
            }

            .tutor-intro {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 1100px) {
            .tutor-intro {
                grid-template-columns: 1fr;
            }

            .tutor-intro img {
                max-width: 220px;
            }
        }

        @media (max-width: 980px) {
            .kpi-strip {
                grid-template-columns: 1fr;
            }

            .tutor-row,
            .class-info-row {
                margin-top: 1.5rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.light_theme:
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at 20% 12%, rgba(216, 180, 106, 0.26), transparent 24rem),
                    radial-gradient(circle at 88% 20%, rgba(105, 132, 190, 0.18), transparent 28rem),
                    linear-gradient(rgba(29, 31, 36, 0.045) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(29, 31, 36, 0.045) 1px, transparent 1px),
                    #f7f3ea;
                background-size: auto, auto, 44px 44px, 44px 44px, auto;
                background-attachment: fixed;
                color: #1d1f24;
            }

            [data-testid="stSidebar"] {
                background: #fffaf0;
                border-right: 1px solid rgba(29, 31, 36, 0.12);
            }

            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] h4,
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] span,
            [data-testid="stSidebar"] small,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
            [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
            [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
                color: #1d1f24 !important;
                opacity: 1 !important;
            }

            [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
                color: rgba(29, 31, 36, 0.68) !important;
            }

            [data-testid="stSidebar"] .stTabs [data-baseweb="tab-list"] {
                border-bottom-color: rgba(29, 31, 36, 0.16);
            }

            [data-testid="stSidebar"] .stTabs [data-baseweb="tab"] p,
            [data-testid="stSidebar"] .stTabs [data-baseweb="tab"] span {
                color: rgba(29, 31, 36, 0.72) !important;
                opacity: 1 !important;
            }

            [data-testid="stSidebar"] .stTabs [aria-selected="true"] p,
            [data-testid="stSidebar"] .stTabs [aria-selected="true"] span {
                color: #9a6a0a !important;
                font-weight: 800;
            }

            [data-testid="stSidebar"] .stTextInput input {
                background: #ffffff !important;
                border-color: rgba(29, 31, 36, 0.18) !important;
                color: #1d1f24 !important;
            }

            [data-testid="stSidebar"] .stTextInput input::placeholder {
                color: rgba(29, 31, 36, 0.44) !important;
            }

            [data-testid="stSidebar"] .stButton button,
            [data-testid="stSidebar"] .stFormSubmitButton button {
                background: #1d1f24 !important;
                border-color: #1d1f24 !important;
                color: #fffaf0 !important;
            }

            [data-testid="stSidebar"] .stButton button p,
            [data-testid="stSidebar"] .stFormSubmitButton button p {
                color: #fffaf0 !important;
            }

            .lead,
            .info-panel p,
            .info-panel li,
            .media-panel p,
            .portal-card p,
            .metric-card p,
            .site-footer {
                color: rgba(29, 31, 36, 0.78) !important;
            }

            .stTabs [data-baseweb="tab-list"] {
                border-bottom-color: rgba(29, 31, 36, 0.16);
            }

            .stTabs [data-baseweb="tab"] p,
            .stTabs [data-baseweb="tab"] span {
                color: rgba(29, 31, 36, 0.7) !important;
                opacity: 1 !important;
            }

            .stTabs [aria-selected="true"] p,
            .stTabs [aria-selected="true"] span {
                color: #9a6a0a !important;
                font-weight: 800;
            }

            .stTextInput input {
                background: rgba(255, 255, 255, 0.92) !important;
                border-color: rgba(29, 31, 36, 0.16) !important;
                color: #1d1f24 !important;
            }

            .stTextInput input::placeholder {
                color: rgba(29, 31, 36, 0.5) !important;
                opacity: 1 !important;
            }

            .stButton button,
            .stFormSubmitButton button {
                background: #1d1f24 !important;
                border-color: #1d1f24 !important;
                color: #fffaf0 !important;
            }

            .stButton button p,
            .stFormSubmitButton button p {
                color: #fffaf0 !important;
            }

            .stButton button:disabled,
            .stFormSubmitButton button:disabled {
                background: rgba(29, 31, 36, 0.22) !important;
                border-color: rgba(29, 31, 36, 0.12) !important;
            }

            .stButton button:disabled p,
            .stFormSubmitButton button:disabled p {
                color: rgba(29, 31, 36, 0.56) !important;
            }

            .info-panel,
            .media-panel,
            .metric-card,
            .portal-card,
            .chat-shell,
            .chat-assistant {
                background: rgba(255, 255, 255, 0.72);
                border-color: rgba(29, 31, 36, 0.12);
            }

            .metric-value,
            .page-title,
            .section-title {
                color: #1d1f24;
            }

            .metric-label,
            .chat-role {
                color: rgba(29, 31, 36, 0.58);
            }

            .divider,
            .site-footer {
                border-color: rgba(29, 31, 36, 0.13);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

if BACKGROUND_IMAGE_URL:
    if st.session_state.light_theme:
        background_overlay = (
            "linear-gradient(rgba(247, 243, 234, 0.82), rgba(247, 243, 234, 0.9))"
        )
    else:
        background_overlay = (
            "linear-gradient(rgba(15, 17, 23, 0.84), rgba(15, 17, 23, 0.9))"
        )

    st.markdown(
        f"""
        <style>
            .stApp {{
                background:
                    {background_overlay},
                    url("{BACKGROUND_IMAGE_URL}") center / cover fixed;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _get_user_value(user, field):
    if isinstance(user, dict):
        return user.get(field)
    return getattr(user, field, None)


def _extract_user(auth_response):
    if isinstance(auth_response, dict):
        if auth_response.get("error"):
            return None
        return auth_response.get("user")
    return getattr(auth_response, "user", None)


def _user_label(user):
    email = _get_user_value(user, "email")
    phone = _get_user_value(user, "phone")
    return email or phone or "student"


def _is_admin():
    admin_email = _get_config_value("ADMIN_EMAIL", "").strip().lower()
    user_email = (_get_user_value(st.session_state.user, "email") or "").strip().lower()
    return bool(admin_email and user_email and user_email == admin_email)


def _get_config_value(name, default=""):
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def _user_id():
    return _get_user_value(st.session_state.user, "id")


def _is_paid_student(student):
    value = student.get("is_paid")
    if isinstance(value, bool):
        is_paid = value
    elif value is None:
        is_paid = False
    elif isinstance(value, str):
        is_paid = value.strip().lower() in {"true", "t", "1", "yes", "paid"}
    else:
        is_paid = bool(value)

    if not is_paid:
        return False

    paid_until = _parse_date(student.get("paid_until"))
    return not paid_until or paid_until >= date.today()


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _add_one_month(value=None):
    base = value or date.today()
    month = base.month + 1
    year = base.year
    if month > 12:
        month = 1
        year += 1

    days_by_month = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(base.day, days_by_month[month - 1])
    return date(year, month, day)


def _next_paid_until(student):
    current_paid_until = _parse_date(student.get("paid_until"))
    base = current_paid_until if current_paid_until and current_paid_until >= date.today() else date.today()
    return _add_one_month(base).isoformat()


def _normalize_student_rows(students):
    normalized = []
    for student in students:
        row = dict(student)
        row["is_paid"] = _is_paid_student(row)
        normalized.append(row)
    return normalized


def _student_display_name(student):
    return (
        student.get("student_name")
        or student.get("email")
        or student.get("phone")
        or student.get("id")
        or "Student"
    )


CITY_OPTIONS = [
    "Delhi",
    "Mumbai",
    "Bengaluru",
    "Hyderabad",
    "Chennai",
    "Kolkata",
    "Pune",
    "Jaipur",
    "Lucknow",
    "Other",
]

GENDER_OPTIONS = ["Female", "Male", "Non-binary", "Prefer not to say"]

LANGUAGE_OPTIONS = ["English", "Hindi", "Hinglish", "Tamil", "Telugu", "Bengali", "Marathi", "Other"]


@st.cache_data(ttl=60 * 60 * 24)
def _lookup_cities_by_pincode(pincode):
    if len(pincode) != 6 or not pincode.isdigit():
        return []
    try:
        with urlopen(f"https://api.postalpincode.in/pincode/{pincode}", timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, ValueError):
        return []

    if not payload or payload[0].get("Status") != "Success":
        return []

    post_offices = payload[0].get("PostOffice") or []
    cities = {
        ", ".join(part for part in [office.get("District"), office.get("State")] if part)
        for office in post_offices
    }
    return sorted(city for city in cities if city)


if "user" not in st.session_state:
    st.session_state.user = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "reset_email" not in st.session_state:
    st.session_state.reset_email = ""


supaclient = get_client()

st.sidebar.markdown(f"### {tr('Account')}")
if not supaclient:
    st.sidebar.info("Sign in is temporarily unavailable.")
elif st.session_state.user:
    st.sidebar.success(f"Signed in as {_user_label(st.session_state.user)}")
    if st.sidebar.button("Sign out"):
        forget_auth_session()
        st.session_state.user = None
        st.rerun()
else:
    st.sidebar.caption("Use email for login and OTP. Phone is saved for student records.")
    signup_tab, signin_tab, reset_tab = st.sidebar.tabs(["Sign up", "Sign in", "Reset"])

    with signup_tab:
        with st.form("signup_form"):
            signup_name = st.text_input(
                "Student name",
                key="signup_name",
                placeholder="Full name",
            )
            email_col, phone_col = st.columns(2)
            with email_col:
                signup_email = st.text_input(
                    "Email",
                    key="signup_email",
                    placeholder="name@example.com",
                )
            with phone_col:
                signup_phone = st.text_input(
                    "Phone number",
                    key="signup_phone",
                    placeholder="+919876543210",
                )
            signup_pincode = st.text_input(
                "Pincode",
                key="signup_pincode",
                placeholder="110001",
                max_chars=10,
            )
            signup_pincode_digits = "".join(ch for ch in signup_pincode if ch.isdigit())
            fetched_city_options = _lookup_cities_by_pincode(signup_pincode_digits)
            if len(signup_pincode_digits) == 6 and fetched_city_options:
                st.caption("City fetched from pincode.")
            elif len(signup_pincode_digits) == 6:
                st.caption("City could not be fetched. Choose manually.")

            city_options = fetched_city_options or CITY_OPTIONS
            if "Other" not in city_options:
                city_options = [*city_options, "Other"]
            signup_city = st.selectbox("Nearest city", city_options, key="signup_city")
            gender_col, language_col = st.columns(2)
            with gender_col:
                signup_gender = st.selectbox("Gender", GENDER_OPTIONS, key="signup_gender")
            with language_col:
                signup_language = st.selectbox(
                    "Language",
                    LANGUAGE_OPTIONS,
                    key="signup_language",
                )
            signup_password = st.text_input(
                "Password",
                type="password",
                key="signup_password",
            )
            signup_submit = st.form_submit_button("Create account")
            if signup_submit:
                if not signup_name or not signup_email or not signup_phone or not signup_pincode or not signup_password:
                    st.error("Enter your name, email, phone number, pincode, and password.")
                elif len(signup_pincode_digits) != 6:
                    st.error("Enter a valid 6-digit pincode.")
                else:
                    student_details = {
                        "student_name": signup_name.strip(),
                        "city": signup_city,
                        "pincode": signup_pincode_digits,
                        "gender": signup_gender,
                        "preferred_language": signup_language,
                    }
                    response = sign_up(
                        signup_email,
                        signup_phone,
                        signup_password,
                        student_details,
                    )
                    if isinstance(response, dict) and response.get("error"):
                        st.error(response["error"])
                    else:
                        user = _extract_user(response)
                        if user:
                            st.session_state.user = user
                            st.success("Account created.")
                            st.rerun()
                        else:
                            st.success("Check your email or phone to confirm your account.")

    with signin_tab:
        with st.form("signin_form"):
            signin_email = st.text_input(
                "Email",
                key="signin_email",
                placeholder="name@example.com",
            )
            signin_password = st.text_input(
                "Password",
                type="password",
                key="signin_password",
            )
            signin_submit = st.form_submit_button("Sign in")
            if signin_submit:
                if not signin_email or not signin_password:
                    st.error("Enter your email and password.")
                else:
                    response = sign_in(signin_email, signin_password)
                    if isinstance(response, dict) and response.get("error"):
                        st.error(response["error"])
                    else:
                        user = _extract_user(response)
                        if user:
                            st.session_state.user = user
                            st.success("Signed in.")
                            st.rerun()
                        else:
                            st.error("Sign in failed.")

    with reset_tab:
        with st.form("request_reset_form"):
            reset_email = st.text_input(
                "Email",
                key="reset_email_input",
                placeholder="name@example.com",
            )
            request_reset = st.form_submit_button("Send reset code")
            if request_reset:
                if not reset_email:
                    st.error("Enter your email.")
                else:
                    response = request_email_otp(reset_email)
                    if isinstance(response, dict) and response.get("error"):
                        st.error(response["error"])
                    else:
                        st.session_state.reset_email = reset_email.strip()
                        st.success("OTP sent to your email. Enter it below with your new password.")

        if st.session_state.reset_email:
            with st.form("email_reset_form"):
                reset_otp = st.text_input("Email OTP", key="reset_otp")
                new_password = st.text_input(
                    "New password",
                    type="password",
                    key="reset_new_password",
                )
                set_password = st.form_submit_button("Set new password")
                if set_password:
                    if not reset_otp or not new_password:
                        st.error("Enter the email OTP and new password.")
                    else:
                        verify_response = verify_email_otp(
                            st.session_state.reset_email,
                            reset_otp,
                        )
                        if isinstance(verify_response, dict) and verify_response.get("error"):
                            st.error(verify_response["error"])
                        else:
                            password_response = update_password(new_password)
                            if isinstance(password_response, dict) and password_response.get("error"):
                                st.error(password_response["error"])
                            else:
                                st.success("Password updated. You can sign in now.")
                                st.session_state.reset_email = ""


st.markdown(
    f"""
    <div class="title-row">
        <div class="eyebrow">{tr("Live online guitar coaching")}</div>
        <h1 class="page-title">{tr("Guitar Class - Learn with a Pro")}</h1>
        <p class="lead">
            {tr("Practical guitar lessons for beginners and growing players, focused on songs, rhythm, chords, technique, and personal feedback.")}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


def render_home_intro():
    st.markdown(
        f"""
        <div class="intro-grid">
            <div class="media-panel">
                <h2 class="section-title">{tr("Meet who you learn from")}</h2>
                <p class="lead" style="margin-top: 0; font-size: 1rem;">
                    {tr("Watch Ashutosh performing live on stage and get a feel for the musicality, confidence, and real performance experience behind the classes.")}
                </p>
            </div>
            <div class="media-panel">
                <h2 class="section-title">{tr("What you sign up for")}</h2>
                <p>
                    {tr("Structured guitar learning with clear practice targets, live feedback, beginner-friendly explanations, and access to class details after fee confirmation. Batch formation will be started soon for upcoming learners.")}
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="video-banner">', unsafe_allow_html=True)
    if TUTOR_VIDEO_PATH.exists():
        st.video(str(TUTOR_VIDEO_PATH))
    else:
        st.markdown(
            """
            <div class="media-panel media-placeholder">
                Add Ashutosh intro video at<br>
                <strong>assets/tutor_intro.mp4</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="tutor-row">', unsafe_allow_html=True)
    tutor_col, summary_col = st.columns([0.95, 1.05], gap="large")
    with tutor_col:
        if TUTOR_PHOTO_PATH.exists():
            photo_data = base64.b64encode(TUTOR_PHOTO_PATH.read_bytes()).decode("ascii")
            photo_html = (
                f'<img src="data:image/jpeg;base64,{photo_data}" '
                'alt="Ashutosh photo">'
            )
        else:
            photo_html = (
                '<div class="media-placeholder" style="min-height: 140px;">'
                'Add Ashutosh photo at<br><strong>assets/tutor_photo.jpeg</strong></div>'
            )

        st.markdown(
            f"""
            <div class="media-panel">
                <div class="tutor-intro">
                    {photo_html}
                    <div class="tutor-copy">
                        <h2 class="section-title">{tr("Personal guidance, clear progress")}</h2>
                        <p>
                            {tr("Learn songs, rhythm, chords, and technique with practical feedback after every session.")}
                        </p>
                    </div>
                </div>
                <div class="kpi-strip">
                    <div class="metric-card">
                        <div class="metric-label">Learners taught</div>
                        <div class="metric-value">50+</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Lesson format</div>
                        <div class="metric-value" style="font-size: 1.35rem;">Live</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Access</div>
                        <div class="metric-value" style="font-size: 1.35rem;">Portal</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Registration</div>
                        <div class="metric-value" style="font-size: 1.35rem;">25-June-2026</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Total batches</div>
                        <div class="metric-value" style="font-size: 1.35rem;">2</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">New batch commencement</div>
                        <div class="metric-value" style="font-size: 1.2rem;">Soon</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Seats per batch</div>
                        <div class="metric-value" style="font-size: 1.35rem;">5</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with summary_col:
        st.markdown(
            f"""
            <div class="side-panel-stack">
            <div class="media-panel">
                <h2 class="section-title">{tr("Before you register")}</h2>
                <p>
                    {tr("The stage performance video gives students and parents a clear sense of Ashutosh's command over the instrument, stage presence, and the kind of musical confidence students can build through consistent practice.")}
                </p>
            </div>
            <div class="info-panel">
                <h2 class="section-title">{tr("Join our guitar classes")}</h2>
                <ul>
                    <li>{tr("New batch formation will be started soon")}</li>
                    <li>{tr("Weekly group and 1:1 sessions")}</li>
                    <li>{tr("Pop, Rock, Blues, and Classical foundations")}</li>
                    <li>{tr("Beginner-friendly lessons with flexible online timings")}</li>
                    <li>{tr("Practice plans, technique feedback, and song-based learning")}</li>
                </ul>
            </div>
            <div class="info-panel">
                <h2 class="section-title">{tr("How sessions work")}</h2>
                <p>
                    {tr("Live classes are hosted online. Students learn through guided exercises, song walkthroughs, chord progressions, rhythm practice, and personal feedback.")}
                </p>
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)


render_home_intro()

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


import html


def render_student_dashboard(portal_result):
    profile = (portal_result or {}).get("profile") or {}
    signed_in = bool(st.session_state.user)
    paid = _is_paid_student(profile) if signed_in and profile else False
    paid_until = profile.get("paid_until") if profile else ""
    next_session = profile.get("next_session_at") if profile else ""

    status_text = tr("Active") if paid else tr("Pending")
    payment_text = (
        f"Paid until {escape(str(paid_until))}"
        if paid_until and paid
        else tr("Fee confirmation pending")
    )
    session_text = escape(str(next_session or tr("Shared after fee confirmation")))

    st.markdown(
        f"""
        <h2 class="section-title">{tr("Student Dashboard")}</h2>
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-label">{tr("Account")}</div>
                <div class="metric-value" style="font-size: 1.35rem;">
                    {escape(_user_label(st.session_state.user)) if signed_in else "Not signed in"}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">{tr("Payment status")}</div>
                <div class="metric-value" style="font-size: 1.35rem;">{status_text}</div>
                <p style="margin: 0.35rem 0 0; color: rgba(255,255,255,0.68);">{payment_text}</p>
            </div>
            <div class="metric-card">
                <div class="metric-label">{tr("Next session")}</div>
                <div class="metric-value" style="font-size: 1.35rem;">{tr("Class access")}</div>
                <p style="margin: 0.35rem 0 0; color: rgba(255,255,255,0.68);">{session_text}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer():
    st.markdown(
        """
        <div class="site-footer">
            Made with ❤️ by my didi
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_chat():
    for role, message in st.session_state.chat_history:

        role_class = (
            "chat-user"
            if role == "user"
            else "chat-assistant"
        )

        st.markdown(
            f"""
            <div class="chat-message {role_class}">
                <span class="chat-role">
                    {"You" if role == "user" else "Assistant"}
                </span>
                <p>{html.unescape(message)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_payment_prompt():

    payment_note = _get_config_value(
        "PAYMENT_NOTE",
        "Scan the QR code to complete your fee payment. Access will be enabled after confirmation.",
    )

    st.markdown(
        f"""
        <div class="portal-card">
            <h3 class="section-title">Complete Fee Payment</h3>
            <p>{escape(payment_note)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.image("assets/qr.jpeg", width=260)


def render_pay_fees_tab(portal_result):
    st.markdown(
        f"""
        <h2 class="section-title">{tr("Pay Fees")}</h2>
        <p class="lead" style="margin-top: 0; font-size: 1rem;">
            {tr("Complete your payment to unlock live session access and recordings.")}
        </p>
        """,
        unsafe_allow_html=True,
    )
    if not st.session_state.user:
        st.info("Sign up or sign in from the sidebar to pay fees.")
        return
    if portal_result and portal_result["error"]:
        st.info("Your payment page is being prepared. Please contact Ashutosh if this continues.")
        return
    profile = (portal_result or {}).get("profile") or {}
    if _is_paid_student(profile):
        paid_until = profile.get("paid_until")
        if paid_until:
            st.success(f"Your fee payment is confirmed until {paid_until}. Session details are available.")
        else:
            st.success("Your fee payment is confirmed. Session details are available in the Session Details tab.")
        return
    render_payment_prompt()


def render_session_details_tab(portal_result):
    st.markdown(
        f"""
        <h2 class="section-title">{tr("Session Details")}</h2>
        <p class="lead" style="margin-top: 0; font-size: 1rem;">
            {tr("Paid students can access upcoming live class details and shared recordings here.")}
        </p>
        """,
        unsafe_allow_html=True,
    )
    if not st.session_state.user:
        st.info("Sign up or sign in from the sidebar to access session details.")
        return
    if portal_result and portal_result["error"]:
        st.info("Your student portal is being prepared. Please contact Ashutosh if this continues.")
        return

    profile = (portal_result or {}).get("profile") or {}
    if not _is_paid_student(profile):
        st.warning("Session details are locked until your fee payment is confirmed.")
        render_payment_prompt()
        return

    next_session_at = profile.get("next_session_at") or "Schedule will be updated soon."
    live_session_link = profile.get("live_session_link")
    session_notes_link = profile.get("session_notes_link")
    safe_session = escape(str(next_session_at))
    safe_link = escape(live_session_link or "", quote=True)
    safe_notes_link = escape(session_notes_link or "", quote=True)

    link_html = (
        f'<a class="session-link" href="{safe_link}" target="_blank" rel="noopener noreferrer">'
        f'{tr("Open live session")}</a>'
        if live_session_link
        else "<p>Live session link will be shared before class.</p>"
    )
    notes_link_html = (
        f'<a class="session-link" href="{safe_notes_link}" target="_blank" rel="noopener noreferrer">'
        f'{tr("Open session notes")}</a>'
        if session_notes_link
        else "<p>Session notes link will be shared after class.</p>"
    )

    st.markdown(
        f"""
        <div class="portal-grid">
            <div class="portal-card">
                <h3 class="section-title">{tr("Next Session")}</h3>
                <p>{safe_session}</p>
            </div>
            <div class="portal-card">
                <h3 class="section-title">{tr("Live Class")}</h3>
                {link_html}
            </div>
            <div class="portal-card">
                <h3 class="section-title">{tr("Session Notes")}</h3>
                {notes_link_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    recordings = (portal_result or {}).get("recordings") or []
    st.markdown(f"### {tr('Session Recordings')}")
    if not recordings:
        st.info("No recordings have been shared yet.")
        return

    for recording in recordings:
        title = escape(recording.get("session_name") or "Class recording")
        url = escape(recording.get("recording_url") or "", quote=True)
        created_at = escape(str(recording.get("created_at") or ""))
        if url:
            st.markdown(
                f"""
                <div class="portal-card" style="margin-bottom: 0.75rem;">
                    <h3 class="section-title">{title}</h3>
                    <p>{created_at}</p>
                    <a class="session-link" href="{url}" target="_blank" rel="noopener noreferrer">
                        {tr("Open recording")}
                    </a>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_faq_tab():
    st.markdown(
        f"""
        <h2 class="section-title">{tr("FAQ Chat")}</h2>
        <p class="lead" style="margin-top: 0; font-size: 1rem;">
            {tr("Ask about schedules, fees, practice routines, lesson levels, or getting started.")}
        </p>
        """,
        unsafe_allow_html=True,
    )
    with st.form("chat_form"):
        question = st.text_input(
            "Ask a question",
            placeholder="What should I practice as a beginner?",
            label_visibility="collapsed",
        )
        ask = st.form_submit_button("Send")
        if ask and question:
            st.session_state.chat_history.append(("user", question))
            answer = get_groq_answer(question)
            if not answer:
                answer = (
                    find_faq(question)
                    or "Sorry, I don't have that info yet. Please contact Ashutosh for details."
                )
            st.session_state.chat_history.append(("assistant", answer))
            save_chat(
                _user_label(st.session_state.user) if st.session_state.user else None,
                question,
                answer,
            )
    render_chat()


def render_admin_panel():
    admin_email = _get_config_value("ADMIN_EMAIL", "").strip().lower()
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <h2 class="section-title">Admin Dashboard</h2>
        <p class="lead" style="margin-top: 0; font-size: 1rem;">
            Manage fee status, live session access, and recordings separately from the student portal.
        </p>
        """,
        unsafe_allow_html=True,
    )

    result = get_student_profiles()
    students = _normalize_student_rows(result["data"])

    if result["error"]:
        st.error("Student dashboard is not ready yet. Create the profiles table and policies in Supabase.")
        with st.expander("Supabase SQL setup"):
            st.code(
                f"""
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  phone text,
  student_name text,
  city text,
  pincode text,
  gender text,
  preferred_language text,
  is_paid boolean not null default false,
  paid_until date,
  last_payment_at timestamp with time zone,
  next_session_at text,
  live_session_link text,
  session_notes_link text,
  created_at timestamp with time zone default now()
);

alter table public.profiles
add column if not exists student_name text,
add column if not exists city text,
add column if not exists pincode text,
add column if not exists gender text,
add column if not exists preferred_language text,
add column if not exists is_paid boolean not null default false,
add column if not exists paid_until date,
add column if not exists last_payment_at timestamp with time zone,
add column if not exists next_session_at text,
add column if not exists live_session_link text,
add column if not exists session_notes_link text,
alter column phone type text using phone::text;

alter table public.profiles enable row level security;

create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (
    id,
    email,
    phone,
    student_name,
    city,
    pincode,
    gender,
    preferred_language
  )
  values (
    new.id,
    new.email,
    coalesce(new.phone, new.raw_user_meta_data ->> 'phone'),
    new.raw_user_meta_data ->> 'student_name',
    new.raw_user_meta_data ->> 'city',
    new.raw_user_meta_data ->> 'pincode',
    new.raw_user_meta_data ->> 'gender',
    new.raw_user_meta_data ->> 'preferred_language'
  )
  on conflict (id) do update
  set email = excluded.email,
      phone = coalesce(excluded.phone, public.profiles.phone),
      student_name = coalesce(excluded.student_name, public.profiles.student_name),
      city = coalesce(excluded.city, public.profiles.city),
      pincode = coalesce(excluded.pincode, public.profiles.pincode),
      gender = coalesce(excluded.gender, public.profiles.gender),
      preferred_language = coalesce(excluded.preferred_language, public.profiles.preferred_language);
  return new;
end;
$$ language plpgsql security definer;

insert into public.profiles (
  id,
  email,
  phone,
  student_name,
  city,
  pincode,
  gender,
  preferred_language
)
select
  id,
  email,
  coalesce(phone, raw_user_meta_data ->> 'phone'),
  raw_user_meta_data ->> 'student_name',
  raw_user_meta_data ->> 'city',
  raw_user_meta_data ->> 'pincode',
  raw_user_meta_data ->> 'gender',
  raw_user_meta_data ->> 'preferred_language'
from auth.users
on conflict (id) do update
set email = excluded.email,
    phone = coalesce(excluded.phone, public.profiles.phone),
    student_name = coalesce(excluded.student_name, public.profiles.student_name),
    city = coalesce(excluded.city, public.profiles.city),
    pincode = coalesce(excluded.pincode, public.profiles.pincode),
    gender = coalesce(excluded.gender, public.profiles.gender),
    preferred_language = coalesce(excluded.preferred_language, public.profiles.preferred_language);

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

drop policy if exists "students can insert own profile" on public.profiles;
drop policy if exists "students can update own profile" on public.profiles;
drop policy if exists "students can read own profile" on public.profiles;
drop policy if exists "admin can read profiles" on public.profiles;
drop policy if exists "admin can update profiles" on public.profiles;

create policy "students can insert own profile"
on public.profiles
for insert
to authenticated
with check (auth.uid() = id);

create policy "students can update own profile"
on public.profiles
for update
to authenticated
using (auth.uid() = id)
with check (auth.uid() = id);

create policy "students can read own profile"
on public.profiles
for select
to authenticated
using (auth.uid() = id);

create policy "admin can read profiles"
on public.profiles
for select
to authenticated
using (lower(auth.jwt() ->> 'email') = '{admin_email}');

create policy "admin can update profiles"
on public.profiles
for update
to authenticated
using (lower(auth.jwt() ->> 'email') = '{admin_email}')
with check (lower(auth.jwt() ->> 'email') = '{admin_email}');

create table if not exists public.recordings (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  session_name text,
  recording_url text not null,
  created_at timestamp with time zone default now()
);

alter table public.recordings
add column if not exists session_name text,
add column if not exists created_at timestamp with time zone default now();

alter table public.recordings enable row level security;

drop policy if exists "paid students can read own recordings" on public.recordings;
drop policy if exists "admin can read recordings" on public.recordings;
drop policy if exists "admin can insert recordings" on public.recordings;

create policy "paid students can read own recordings"
on public.recordings
for select
to authenticated
using (
  auth.uid() = user_id
  and exists (
    select 1 from public.profiles
    where profiles.id = auth.uid()
    and profiles.is_paid = true
    and (profiles.paid_until is null or profiles.paid_until >= current_date)
  )
);

create policy "admin can read recordings"
on public.recordings
for select
to authenticated
using (lower(auth.jwt() ->> 'email') = '{admin_email}');

create policy "admin can insert recordings"
on public.recordings
for insert
to authenticated
with check (lower(auth.jwt() ->> 'email') = '{admin_email}');
                """.strip(),
                language="sql",
            )
    else:
        paid_students = [student for student in students if _is_paid_student(student)]
        unpaid_students = [student for student in students if not _is_paid_student(student)]
        st.markdown(
            f"""
            <div class="metric-row">
                <div class="metric-card">
                    <div class="metric-label">Total students</div>
                    <div class="metric-value">{len(students)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Paid students</div>
                    <div class="metric-value">{len(paid_students)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Unpaid students</div>
                    <div class="metric-value">{len(unpaid_students)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        roster_tab, unpaid_tab, paid_tab, access_tab = st.tabs(
            ["All Students", "Unpaid", "Paid", "Access Manager"]
        )

        with roster_tab:
            st.dataframe(
                students,
                use_container_width=True,
                hide_index=True,
                column_order=[
                    "created_at",
                    "student_name",
                    "email",
                    "phone",
                    "city",
                    "pincode",
                    "gender",
                    "preferred_language",
                    "is_paid",
                    "paid_until",
                    "last_payment_at",
                    "next_session_at",
                    "live_session_link",
                    "session_notes_link",
                    "id",
                ],
            )

        with unpaid_tab:
            if unpaid_students:
                st.markdown("### Confirm Manual Payments")
                for student in unpaid_students:
                    student_id = student.get("id")
                    if not student_id:
                        continue
                    name = _student_display_name(student)
                    email = student.get("email") or ""
                    phone = student.get("phone") or ""
                    row_col, action_col = st.columns([3, 1])
                    with row_col:
                        st.markdown(f"**{name}**")
                        st.caption(" | ".join(value for value in [email, phone] if value))
                    with action_col:
                        if st.button("Payment received", key=f"mark_paid_{student_id}"):
                            paid_until = _next_paid_until(student)
                            response = update_student_access(
                                student_id,
                                True,
                                student.get("next_session_at") or "",
                                student.get("live_session_link") or "",
                                student.get("session_notes_link") or "",
                                paid_until,
                            )
                            if isinstance(response, dict) and response.get("error"):
                                st.error(response["error"])
                            else:
                                st.success(f"{name} marked as paid until {paid_until}.")
                                st.rerun()
            else:
                st.info("No unpaid students found.")

        with paid_tab:
            if paid_students:
                st.dataframe(
                    paid_students,
                    use_container_width=True,
                    hide_index=True,
                    column_order=[
                        "created_at",
                        "student_name",
                        "email",
                        "phone",
                        "city",
                        "pincode",
                        "preferred_language",
                        "is_paid",
                        "paid_until",
                        "last_payment_at",
                        "next_session_at",
                        "live_session_link",
                        "session_notes_link",
                        "id",
                    ],
                )
                st.markdown("### Renew Monthly Access")
                for student in paid_students:
                    student_id = student.get("id")
                    if not student_id:
                        continue
                    name = _student_display_name(student)
                    current_until = student.get("paid_until") or "not set"
                    row_col, action_col = st.columns([3, 1])
                    with row_col:
                        st.markdown(f"**{name}**")
                        st.caption(f"Paid until: {current_until}")
                    with action_col:
                        if st.button("Renew 1 month", key=f"renew_paid_{student_id}"):
                            paid_until = _next_paid_until(student)
                            response = update_student_access(
                                student_id,
                                True,
                                student.get("next_session_at") or "",
                                student.get("live_session_link") or "",
                                student.get("session_notes_link") or "",
                                paid_until,
                            )
                            if isinstance(response, dict) and response.get("error"):
                                st.error(response["error"])
                            else:
                                st.success(f"{name} renewed until {paid_until}.")
                                st.rerun()
            else:
                st.info("No paid students found. Mark a student as paid from Access Manager.")

        with access_tab:
            st.markdown("### Manage Fees And Session Access")
            if not students:
                if not has_admin_service_role_key():
                    st.warning(
                        "No students are visible to the admin query. Add SUPABASE_SERVICE_ROLE_KEY "
                        "to Streamlit Secrets so the server-side admin panel can read all profiles."
                    )
                st.info("No registered students yet.")
                return
            student_options = {
                f"{student.get('student_name') or student.get('email') or student.get('phone') or student.get('id')}": student
                for student in students
            }
            selected_label = st.selectbox("Student", list(student_options.keys()))
            selected_student = student_options[selected_label]

            with st.form("student_access_form"):
                paid_status = st.checkbox(
                    "Paid student",
                    value=bool(selected_student.get("is_paid")),
                )
                default_paid_until = _parse_date(selected_student.get("paid_until")) or date.today()
                paid_until = st.date_input(
                    "Paid until",
                    value=default_paid_until,
                    disabled=not paid_status,
                )
                next_session = st.text_input(
                    "Next session schedule",
                    value=selected_student.get("next_session_at") or "",
                    placeholder="Sunday, 7:00 PM IST",
                )
                live_link = st.text_input(
                    "Live session link",
                    value=selected_student.get("live_session_link") or "",
                    placeholder="https://meet.google.com/...",
                )
                notes_link = st.text_input(
                    "Session notes link",
                    value=selected_student.get("session_notes_link") or "",
                    placeholder="https://docs.google.com/...",
                )
                save_access = st.form_submit_button("Save access")
                if save_access:
                    response = update_student_access(
                        selected_student["id"],
                        paid_status,
                        next_session,
                        live_link,
                        notes_link,
                        paid_until.isoformat() if paid_status else "",
                    )
                    if isinstance(response, dict) and response.get("error"):
                        st.error(response["error"])
                    else:
                        st.success("Student access updated.")
                        st.rerun()

            with st.form("recording_form"):
                recording_name = st.text_input("Recording title", placeholder="Week 1 - Chords")
                recording_url = st.text_input("Recording URL", placeholder="https://...")
                add_recording = st.form_submit_button("Add recording")
                if add_recording:
                    if not recording_url:
                        st.error("Add a recording URL.")
                    else:
                        response = add_recording_for_student(
                            selected_student["id"],
                            recording_name or "Class recording",
                            recording_url,
                        )
                        if isinstance(response, dict) and response.get("error"):
                            st.error(response["error"])
                        else:
                            st.success("Recording added.")
                            st.rerun()


portal_result = get_student_portal(_user_id()) if st.session_state.user and _user_id() else None

if _is_admin():
    faq_tab, admin_tab = st.tabs([tr("FAQ Chat"), "Admin Panel"])
    with faq_tab:
        render_faq_tab()
    with admin_tab:
        render_admin_panel()
else:
    render_student_dashboard(portal_result)
    faq_tab, pay_tab, session_tab = st.tabs([tr("FAQ Chat"), tr("Pay Fees"), tr("Session Details")])
    with faq_tab:
        render_faq_tab()
    with pay_tab:
        render_pay_fees_tab(portal_result)
    with session_tab:
        render_session_details_tab(portal_result)

render_footer()
