from html import escape
import os

import streamlit as st

from db import find_faq, init_db, save_chat
from supabase_client import (
    get_client,
    get_student_profiles,
    request_password_reset,
    sign_in,
    sign_up,
    update_password,
    verify_phone_reset_otp,
)
from utils import get_groq_answer


st.set_page_config(page_title="Guitar Class", layout="wide")

init_db()

st.markdown(
    """
    <style>
        #MainMenu, footer, header [data-testid="stToolbar"] {
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
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    user_email = (_get_user_value(st.session_state.user, "email") or "").strip().lower()
    return bool(admin_email and user_email and user_email == admin_email)


if "user" not in st.session_state:
    st.session_state.user = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "reset_identifier" not in st.session_state:
    st.session_state.reset_identifier = ""


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
    st.sidebar.caption("Use your email address or phone number.")
    signup_tab, signin_tab, reset_tab = st.sidebar.tabs(["Sign up", "Sign in", "Reset"])

    with signup_tab:
        with st.form("signup_form"):
            signup_identifier = st.text_input(
                "Email or phone",
                key="signup_identifier",
                placeholder="name@example.com or +919876543210",
            )
            signup_password = st.text_input(
                "Password",
                type="password",
                key="signup_password",
            )
            signup_submit = st.form_submit_button("Create account")
            if signup_submit:
                if not signup_identifier or not signup_password:
                    st.error("Enter an email/phone and password.")
                else:
                    response = sign_up(signup_identifier, signup_password)
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
            signin_identifier = st.text_input(
                "Email or phone",
                key="signin_identifier",
                placeholder="name@example.com or +919876543210",
            )
            signin_password = st.text_input(
                "Password",
                type="password",
                key="signin_password",
            )
            signin_submit = st.form_submit_button("Sign in")
            if signin_submit:
                if not signin_identifier or not signin_password:
                    st.error("Enter an email/phone and password.")
                else:
                    response = sign_in(signin_identifier, signin_password)
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
            reset_identifier = st.text_input(
                "Email or phone",
                key="reset_identifier_input",
                placeholder="name@example.com or +919876543210",
            )
            request_reset = st.form_submit_button("Send reset code")
            if request_reset:
                if not reset_identifier:
                    st.error("Enter your email or phone number.")
                else:
                    response = request_password_reset(reset_identifier)
                    if isinstance(response, dict) and response.get("error"):
                        st.error(response["error"])
                    else:
                        st.session_state.reset_identifier = reset_identifier.strip()
                        if "@" in reset_identifier:
                            st.success("Password reset email sent. Follow the email link to set a new password.")
                        else:
                            st.success("OTP sent. Enter it below with your new password.")

        if st.session_state.reset_identifier and "@" not in st.session_state.reset_identifier:
            with st.form("phone_reset_form"):
                reset_otp = st.text_input("OTP", key="reset_otp")
                new_password = st.text_input(
                    "New password",
                    type="password",
                    key="reset_new_password",
                )
                set_password = st.form_submit_button("Set new password")
                if set_password:
                    if not reset_otp or not new_password:
                        st.error("Enter the OTP and new password.")
                    else:
                        verify_response = verify_phone_reset_otp(
                            st.session_state.reset_identifier,
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
                                st.session_state.reset_identifier = ""


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

st.markdown(
    """
    <h2 class="section-title">FAQ Chat</h2>
    <p class="lead" style="margin-top: 0; font-size: 1rem;">
        Ask about schedules, fees, practice routines, lesson levels, or getting started.
    </p>
    """,
    unsafe_allow_html=True,
)


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
        save_chat(_user_label(st.session_state.user) if st.session_state.user else None, question, answer)

render_chat()

if _is_admin():
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <h2 class="section-title">Admin Dashboard</h2>
        <p class="lead" style="margin-top: 0; font-size: 1rem;">
            Registered student details from your Supabase profiles table.
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
  created_at timestamp with time zone default now()
);

alter table public.profiles enable row level security;

create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, phone)
  values (new.id, new.email, new.phone)
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

create policy "admin can read profiles"
on public.profiles
for select
to authenticated
using ((auth.jwt() ->> 'email') = 'YOUR_ADMIN_EMAIL_HERE');
                """.strip(),
                language="sql",
            )
    else:
        emails = sum(1 for student in students if student.get("email"))
        phones = sum(1 for student in students if student.get("phone"))
        st.markdown(
            f"""
            <div class="metric-row">
                <div class="metric-card">
                    <div class="metric-label">Total students</div>
                    <div class="metric-value">{len(students)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Email signups</div>
                    <div class="metric-value">{emails}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Phone signups</div>
                    <div class="metric-value">{phones}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.dataframe(
            students,
            use_container_width=True,
            hide_index=True,
            column_order=["created_at", "email", "phone", "id"],
        )
