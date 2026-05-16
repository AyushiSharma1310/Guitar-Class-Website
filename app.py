import os
import streamlit as st
from db import init_db, save_lead, save_chat, find_faq
from utils import get_openai_answer
from supabase_client import sign_up, sign_in, insert_payment, get_recordings, get_client, set_meet_link, get_active_meet_link


init_db()

st.set_page_config(page_title="Guitar Class", layout="wide")

st.title("Guitar Class — Learn with a Pro")

# Sidebar account / Supabase auth
if "user" not in st.session_state:
    st.session_state.user = None

supaclient = get_client()
if not supaclient:
    st.sidebar.warning("Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY in environment to enable login/payments/recordings.")
else:
    st.sidebar.header("Account")
    if not st.session_state.user:
        with st.sidebar.form("signup_form"):
            su_email = st.text_input("Sign up email", key="su_email")
            su_pw = st.text_input("Sign up password", type="password", key="su_pw")
            su_submit = st.form_submit_button("Sign up")
            if su_submit and su_email and su_pw:
                res = sign_up(su_email, su_pw)
                st.sidebar.write(res)
        with st.sidebar.form("signin_form"):
            si_email = st.text_input("Sign in email", key="si_email")
            si_pw = st.text_input("Sign in password", type="password", key="si_pw")
            si_submit = st.form_submit_button("Sign in")
            if si_submit and si_email and si_pw:
                res = sign_in(si_email, si_pw)
                if isinstance(res, dict) and res.get("error"):
                    st.sidebar.error(res.get("error"))
                else:
                    # response structure varies; try to extract user
                    user = None
                    if isinstance(res, dict) and res.get("user"):
                        user = res.get("user")
                    elif hasattr(res, 'user'):
                        user = res.user
                    if user:
                        st.session_state.user = {"id": user.get("id"), "email": user.get("email")}
                        st.sidebar.success("Signed in")
                    else:
                        st.sidebar.error("Sign in failed")
    else:
        st.sidebar.markdown(f"Signed in as {st.session_state.user['email']}")
        if st.sidebar.button("Sign out"):
            st.session_state.user = None

col1, col2 = st.columns([2,1])

with col1:
    st.header("Join our guitar classes")
    st.markdown("""
    - Weekly group and 1:1 sessions
    - Genres: Pop, Rock, Blues, Classical
    - Flexible timings and online meet links
    """)

    st.subheader("How sessions work")
    st.write("We host live classes over Google Meet. The tutor will share a Meet link for each scheduled class — press the Join button to open the meeting.")

    st.markdown("## Contact & Booking")
    with st.form("contact_form"):
        name = st.text_input("Your name")
        email = st.text_input("Email")
        phone = st.text_input("Phone (optional)")
        message = st.text_area("Message / availability")
        submit = st.form_submit_button("Send")
        if submit:
            save_lead(name or "", email or "", phone or "", message or "")
            st.success("Thanks — we saved your details. We'll be in touch.")

    st.markdown("## Upcoming session")
    admin_email = os.getenv("ADMIN_EMAIL")
    active = get_active_meet_link() if supaclient else None

    # Admin can set the persistent meet link
    if supaclient and st.session_state.get("user") and admin_email and st.session_state.user.get("email") == admin_email:
        with st.form("set_meet_form"):
            new_link = st.text_input("Set Google Meet link")
            days = st.number_input("Valid days", min_value=1, max_value=365, value=90)
            set_link = st.form_submit_button("Save link")
            if set_link and new_link:
                set_meet_link(new_link, created_by=st.session_state.user.get("id"), days_valid=int(days))
                st.success("Meet link saved and will be active for the selected period.")

    # Students: show active meet link if signed in and link not expired
    if st.session_state.get("user"):
        if active and active.get("link"):
            st.markdown(f"**Active session (expires {active.get('expires_at')} UTC)**")
            st.markdown(f"[Join Google Meet]({active.get('link')})")
        else:
            st.info("No active meet link available. The tutor will publish one for registered students.")
    else:
        st.info("Only registered students can access the live session. Please sign in or sign up from the sidebar.")

with col2:
    st.image("https://images.unsplash.com/photo-1511376777868-611b54f68947?w=800", width=320)
    st.markdown("**Tutor:** Alex Guitarist")
    st.markdown("**Experience:** 10+ years teaching, session musician")
    st.markdown("**Portfolio:**")
    st.write("- YouTube: https://youtube.example (replace)")
    st.write("- SoundCloud: https://soundcloud.example (replace)")

st.markdown("---")

st.header("AI Assistant — Ask FAQs")
api_key = st.sidebar.text_input("OpenAI API key (optional)", type="password")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def render_chat():
    for role, text in st.session_state.chat_history:
        if role == "user":
            st.markdown(f"**You:** {text}")
        else:
            st.markdown(f"**Assistant:** {text}")

with st.form("chat_form"):
    question = st.text_input("Ask about the classes, schedule, pricing...")
    ask = st.form_submit_button("Send")
    if ask and question:
        st.session_state.chat_history.append(("user", question))
        answer = None
        if api_key:
            answer = get_openai_answer(question, api_key)
        if not answer:
            answer = find_faq(question) or "Sorry — I don't have that info yet. You can leave your question and contact details in the contact form."
        st.session_state.chat_history.append(("assistant", answer))
        save_chat(None, question, answer)

render_chat()

st.markdown("---")
st.markdown("---")

# User-specific payments and recordings (requires Supabase)
if st.session_state.get("user"):
    st.subheader("Payments & Recordings")
    with st.form("payment_form"):
        amount = st.number_input("Amount paid", min_value=0.0, value=0.0)
        note = st.text_input("Note (transaction id / method)")
        paid = st.form_submit_button("Record payment")
        if paid:
            if not supaclient:
                st.error("Supabase not configured")
            else:
                res = insert_payment(st.session_state.user['id'], amount, note)
                st.success("Payment recorded")

    st.subheader("My Recordings")
    recs = get_recordings(st.session_state.user['id']) if supaclient else []
    if recs:
        for r in recs:
            name = r.get('session_name') or 'Session'
            url = r.get('recording_url')
            st.write(f"{name}: {url}")
    else:
        st.write("No recordings found.")

st.markdown("*To deploy: run `pip install -r requirements.txt` then `streamlit run app.py`.*")
