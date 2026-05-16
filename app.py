from html import escape
import os

import streamlit as st

from db import find_faq, init_db, save_chat
from supabase_client import (
    add_recording_for_student,
    get_client,
    get_student_portal,
    get_student_profiles,
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

st.markdown(
    """
    <style>
        #MainMenu, footer {
            visibility: hidden;
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

        .info-panel ul {
            margin-bottom: 0;
            padding-left: 1.1rem;
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
            .portal-grid {
                grid-template-columns: 1fr;
            }
        }
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


if "user" not in st.session_state:
    st.session_state.user = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "reset_email" not in st.session_state:
    st.session_state.reset_email = ""


supaclient = get_client()

st.sidebar.markdown("### Account")
if not supaclient:
    st.sidebar.info("Sign in is temporarily unavailable.")
elif st.session_state.user:
    st.sidebar.success(f"Signed in as {_user_label(st.session_state.user)}")
    if st.sidebar.button("Sign out"):
        st.session_state.user = None
        st.rerun()
else:
    st.sidebar.caption("Use email for login and OTP. Phone is saved for student records.")
    signup_tab, signin_tab, reset_tab = st.sidebar.tabs(["Sign up", "Sign in", "Reset"])

    with signup_tab:
        with st.form("signup_form"):
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
            signup_password = st.text_input(
                "Password",
                type="password",
                key="signup_password",
            )
            signup_submit = st.form_submit_button("Create account")
            if signup_submit:
                if not signup_email or not signup_phone or not signup_password:
                    st.error("Enter your email, phone number, and password.")
                else:
                    response = sign_up(signup_email, signup_phone, signup_password)
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
    """
    <div class="title-row">
        <div class="eyebrow">Live online guitar coaching</div>
        <h1 class="page-title">Guitar Class - Learn with a Pro</h1>
        <p class="lead">
            Practical guitar lessons for beginners and growing players, focused on
            songs, rhythm, chords, technique, and personal feedback.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

desc_col, session_col = st.columns(2, gap="large")

with desc_col:
    st.markdown(
        """
        <div class="info-panel">
            <h2 class="section-title">Join our guitar classes</h2>
            <ul>
                <li>Weekly group and 1:1 sessions</li>
                <li>Pop, Rock, Blues, and Classical foundations</li>
                <li>Beginner-friendly lessons with flexible online timings</li>
                <li>Practice plans, technique feedback, and song-based learning</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

with session_col:
    st.markdown(
        """
        <div class="info-panel">
            <h2 class="section-title">How sessions work</h2>
            <p>
                Live classes are hosted online. Students learn through guided
                exercises, song walkthroughs, chord progressions, rhythm practice,
                and personal feedback.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


def render_chat():
    messages = []
    for role, text in st.session_state.chat_history:
        safe_text = escape(text).replace("\n", "<br>")
        if role == "user":
            css_class = "chat-user"
            label = "You"
        else:
            css_class = "chat-assistant"
            label = "Assistant"
        messages.append(
            f"""
            <div class="chat-message {css_class}">
                <span class="chat-role">{label}</span>
                {safe_text}
            </div>
            """
        )
    st.markdown(
        f'<div class="chat-shell">{"".join(messages)}</div>',
        unsafe_allow_html=True,
    )


def render_payment_prompt():
    payment_qr_url = _get_config_value("PAYMENT_QR_URL")
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
    if payment_qr_url:
        st.image(payment_qr_url, width=260)
    else:
        st.warning("Payment QR is not configured yet. Add PAYMENT_QR_URL in Streamlit secrets.")


def render_pay_fees_tab(portal_result):
    st.markdown(
        """
        <h2 class="section-title">Pay Fees</h2>
        <p class="lead" style="margin-top: 0; font-size: 1rem;">
            Complete your payment to unlock live session access and recordings.
        </p>
        """,
        unsafe_allow_html=True,
    )
    if not st.session_state.user:
        st.info("Sign up or sign in from the sidebar to pay fees.")
        return
    if portal_result and portal_result["error"]:
        st.info("Your payment page is being prepared. Please contact the tutor if this continues.")
        return
    profile = (portal_result or {}).get("profile") or {}
    if profile.get("is_paid"):
        st.success("Your fee payment is confirmed. Session details are available in the Session Details tab.")
        return
    render_payment_prompt()


def render_session_details_tab(portal_result):
    st.markdown(
        """
        <h2 class="section-title">Session Details</h2>
        <p class="lead" style="margin-top: 0; font-size: 1rem;">
            Paid students can access upcoming live class details and shared recordings here.
        </p>
        """,
        unsafe_allow_html=True,
    )
    if not st.session_state.user:
        st.info("Sign up or sign in from the sidebar to access session details.")
        return
    if portal_result and portal_result["error"]:
        st.info("Your student portal is being prepared. Please contact the tutor if this continues.")
        return

    profile = (portal_result or {}).get("profile") or {}
    if not profile.get("is_paid"):
        st.warning("Session details are locked until your fee payment is confirmed.")
        render_payment_prompt()
        return

    next_session_at = profile.get("next_session_at") or "Schedule will be updated soon."
    live_session_link = profile.get("live_session_link")
    safe_session = escape(str(next_session_at))
    safe_link = escape(live_session_link or "", quote=True)

    link_html = (
        f'<a class="session-link" href="{safe_link}" target="_blank" rel="noopener noreferrer">'
        "Open live session</a>"
        if live_session_link
        else "<p>Live session link will be shared before class.</p>"
    )

    st.markdown(
        f"""
        <div class="portal-grid">
            <div class="portal-card">
                <h3 class="section-title">Next Session</h3>
                <p>{safe_session}</p>
            </div>
            <div class="portal-card">
                <h3 class="section-title">Live Class</h3>
                {link_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    recordings = (portal_result or {}).get("recordings") or []
    st.markdown("### Session Recordings")
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
                        Open recording
                    </a>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_faq_tab():
    st.markdown(
        """
        <h2 class="section-title">FAQ Chat</h2>
        <p class="lead" style="margin-top: 0; font-size: 1rem;">
            Ask about schedules, fees, practice routines, lesson levels, or getting started.
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
                    or "Sorry, I don't have that info yet. Please contact the tutor for details."
                )
            st.session_state.chat_history.append(("assistant", answer))
            save_chat(
                _user_label(st.session_state.user) if st.session_state.user else None,
                question,
                answer,
            )
    render_chat()


def render_admin_panel():
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
    students = result["data"]

    if result["error"]:
        st.error("Student dashboard is not ready yet. Create the profiles table and policies in Supabase.")
        with st.expander("Supabase SQL setup"):
            st.code(
                """
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  phone text,
  is_paid boolean not null default false,
  next_session_at text,
  live_session_link text,
  created_at timestamp with time zone default now()
);

alter table public.profiles
add column if not exists is_paid boolean not null default false,
add column if not exists next_session_at text,
add column if not exists live_session_link text;

alter table public.profiles enable row level security;

create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, phone)
  values (new.id, new.email, coalesce(new.phone, new.raw_user_meta_data ->> 'phone'))
  on conflict (id) do update
  set email = excluded.email,
      phone = excluded.phone;
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

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
using ((auth.jwt() ->> 'email') = 'YOUR_ADMIN_EMAIL_HERE');

create policy "admin can update profiles"
on public.profiles
for update
to authenticated
using ((auth.jwt() ->> 'email') = 'YOUR_ADMIN_EMAIL_HERE')
with check ((auth.jwt() ->> 'email') = 'YOUR_ADMIN_EMAIL_HERE');

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
  )
);

create policy "admin can read recordings"
on public.recordings
for select
to authenticated
using ((auth.jwt() ->> 'email') = 'YOUR_ADMIN_EMAIL_HERE');

create policy "admin can insert recordings"
on public.recordings
for insert
to authenticated
with check ((auth.jwt() ->> 'email') = 'YOUR_ADMIN_EMAIL_HERE');
                """.strip(),
                language="sql",
            )
    else:
        paid_students = [student for student in students if student.get("is_paid")]
        unpaid_students = [student for student in students if not student.get("is_paid")]
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
                    "email",
                    "phone",
                    "is_paid",
                    "next_session_at",
                    "live_session_link",
                    "id",
                ],
            )

        with unpaid_tab:
            st.dataframe(
                unpaid_students,
                use_container_width=True,
                hide_index=True,
                column_order=["created_at", "email", "phone", "next_session_at", "id"],
            )

        with paid_tab:
            st.dataframe(
                paid_students,
                use_container_width=True,
                hide_index=True,
                column_order=["created_at", "email", "phone", "next_session_at", "live_session_link", "id"],
            )

        with access_tab:
            st.markdown("### Manage Fees And Session Access")
            if not students:
                st.info("No registered students yet.")
                return
            student_options = {
                f"{student.get('email') or student.get('phone') or student.get('id')}": student
                for student in students
            }
            selected_label = st.selectbox("Student", list(student_options.keys()))
            selected_student = student_options[selected_label]

            with st.form("student_access_form"):
                paid_status = st.checkbox(
                    "Paid student",
                    value=bool(selected_student.get("is_paid")),
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
                save_access = st.form_submit_button("Save access")
                if save_access:
                    response = update_student_access(
                        selected_student["id"],
                        paid_status,
                        next_session,
                        live_link,
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
    faq_tab, admin_tab = st.tabs(["FAQ Chat", "Admin Panel"])
    with faq_tab:
        render_faq_tab()
    with admin_tab:
        render_admin_panel()
else:
    faq_tab, pay_tab, session_tab = st.tabs(["FAQ Chat", "Pay Fees", "Session Details"])
    with faq_tab:
        render_faq_tab()
    with pay_tab:
        render_pay_fees_tab(portal_result)
    with session_tab:
        render_session_details_tab(portal_result)
