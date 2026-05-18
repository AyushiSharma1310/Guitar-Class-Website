from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

def _clear_dead_local_proxy():
    dead_proxy_values = {"http://127.0.0.1:9", "https://127.0.0.1:9"}
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        if os.getenv(name) in dead_proxy_values:
            os.environ.pop(name, None)

_clear_dead_local_proxy()

def _get_config_value(name):
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        return None

# Try to import supabase client; if missing, keep the module usable so the app doesn't crash.
try:
    from supabase import create_client
    _HAS_SUPABASE = True
except Exception:
    create_client = None
    _HAS_SUPABASE = False

SUPABASE_URL = _get_config_value("SUPABASE_URL")
SUPABASE_KEY = _get_config_value("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = _get_config_value("SUPABASE_SERVICE_ROLE_KEY")
APP_URL = (_get_config_value("APP_URL") or "").rstrip("/")

_client = None
_admin_client = None

def _friendly_supabase_error(error):
    message = str(error)
    if "WinError 10061" in message or "actively refused" in message:
        return (
            "Could not reach Supabase from this computer. Check your internet connection, "
            "VPN/proxy/firewall settings, then try again."
        )
    return message

def _auth_credentials(email, password):
    return {"email": (email or "").strip(), "password": password}

def _signup_credentials(email, phone, password, student_details=None):
    metadata = {"phone": (phone or "").strip()}
    metadata.update(student_details or {})
    credentials = {
        "email": (email or "").strip(),
        "password": password,
        "options": {"data": metadata},
    }
    if APP_URL:
        credentials["options"]["email_redirect_to"] = APP_URL
    return credentials

def _get_user_value(user, field):
    if isinstance(user, dict):
        return user.get(field)
    return getattr(user, field, None)

def _get_response_user(response):
    if isinstance(response, dict):
        return response.get("user")
    return getattr(response, "user", None)

def _get_response_session(response):
    if isinstance(response, dict):
        return response.get("session")
    return getattr(response, "session", None)

def _get_session_value(session, field):
    if isinstance(session, dict):
        return session.get(field)
    return getattr(session, field, None)

def _get_user_metadata(user):
    if isinstance(user, dict):
        return user.get("user_metadata") or {}
    return getattr(user, "user_metadata", None) or {}

def _restore_streamlit_session():
    if _client is None:
        return
    try:
        import streamlit as st

        auth_session = st.session_state.get("supabase_auth")
        if not auth_session:
            return
        access_token = auth_session.get("access_token")
        refresh_token = auth_session.get("refresh_token")
        if access_token and refresh_token:
            _client.auth.set_session(access_token, refresh_token)
    except Exception:
        return

def remember_auth_session(response):
    session = _get_response_session(response)
    access_token = _get_session_value(session, "access_token")
    refresh_token = _get_session_value(session, "refresh_token")
    if not access_token or not refresh_token:
        return
    try:
        import streamlit as st

        st.session_state.supabase_auth = {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    except Exception:
        return

def forget_auth_session():
    try:
        import streamlit as st

        st.session_state.pop("supabase_auth", None)
    except Exception:
        pass
    client = get_client()
    if client:
        try:
            client.auth.sign_out()
        except Exception:
            pass

def get_client():
    global _client
    if not _HAS_SUPABASE:
        return None
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return None
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    _restore_streamlit_session()
    return _client

def get_admin_client():
    global _admin_client
    if not _HAS_SUPABASE:
        return None
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        if _admin_client is None:
            _admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        return _admin_client
    return get_client()

def has_admin_service_role_key():
    return bool(SUPABASE_SERVICE_ROLE_KEY)

def sign_up(email, phone, password, student_details=None):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        response = client.auth.sign_up(
            _signup_credentials(email, phone, password, student_details)
        )
        remember_auth_session(response)
        user = _get_response_user(response)
        if user:
            upsert_student_profile(user, phone=phone, student_details=student_details)
        return response
    except Exception as e:
        return {"error": _friendly_supabase_error(e)}

def sign_in(email, password):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        response = client.auth.sign_in_with_password(_auth_credentials(email, password))
        remember_auth_session(response)
        user = _get_response_user(response)
        if user:
            upsert_student_profile(user)
        return response
    except Exception as e:
        return {"error": _friendly_supabase_error(e)}

def request_email_otp(email):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        options = {"should_create_user": False}
        if APP_URL:
            options["email_redirect_to"] = APP_URL
        return client.auth.sign_in_with_otp({"email": (email or "").strip(), "options": options})
    except Exception as e:
        return {"error": _friendly_supabase_error(e)}

def verify_email_otp(email, token):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        response = client.auth.verify_otp(
            {"email": (email or "").strip(), "token": token, "type": "email"}
        )
        remember_auth_session(response)
        return response
    except Exception as e:
        return {"error": _friendly_supabase_error(e)}

def update_password(new_password):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        return client.auth.update_user({"password": new_password})
    except Exception as e:
        return {"error": _friendly_supabase_error(e)}

def upsert_student_profile(user, phone=None, student_details=None):
    client = get_admin_client()
    if not client:
        return None
    user_id = _get_user_value(user, "id")
    if not user_id:
        return None
    metadata = _get_user_metadata(user)
    phone_value = phone or _get_user_value(user, "phone") or metadata.get("phone")
    details = {
        "student_name": metadata.get("student_name"),
        "city": metadata.get("city"),
        "pincode": metadata.get("pincode"),
        "gender": metadata.get("gender"),
        "preferred_language": metadata.get("preferred_language"),
    }
    details.update(student_details or {})
    data = {
        "id": user_id,
        "email": _get_user_value(user, "email"),
        "phone": phone_value,
        **details,
    }
    try:
        return client.table("profiles").upsert(data).execute()
    except Exception:
        return None

def get_student_profiles():
    client = get_admin_client()
    if not client:
        return {"data": [], "error": "Supabase not configured"}
    try:
        res = client.table("profiles").select("*").order("created_at", desc=True).execute()
        return {"data": res.data if hasattr(res, "data") else [], "error": None}
    except Exception as e:
        return {"data": [], "error": str(e)}

def update_student_access(
    user_id,
    is_paid,
    next_session_at="",
    live_session_link="",
    session_notes_link="",
    paid_until=None,
):
    client = get_admin_client()
    if not client:
        return {"error": "Supabase not configured"}
    data = {
        "is_paid": bool(is_paid),
        "next_session_at": next_session_at,
        "live_session_link": live_session_link,
        "session_notes_link": session_notes_link,
    }
    if paid_until is not None:
        data["paid_until"] = paid_until or None
        if is_paid and paid_until:
            data["last_payment_at"] = datetime.utcnow().isoformat()
    try:
        return client.table("profiles").update(data).eq("id", user_id).execute()
    except Exception as e:
        if paid_until is not None and (
            "paid_until" in str(e)
            or "last_payment_at" in str(e)
            or "session_notes_link" in str(e)
            or "schema cache" in str(e)
        ):
            data.pop("paid_until", None)
            data.pop("last_payment_at", None)
            data.pop("session_notes_link", None)
            try:
                return client.table("profiles").update(data).eq("id", user_id).execute()
            except Exception as retry_error:
                return {"error": str(retry_error)}
        return {"error": str(e)}

def add_recording_for_student(user_id, session_name, recording_url):
    client = get_admin_client()
    if not client:
        return {"error": "Supabase not configured"}
    data = {
        "user_id": user_id,
        "session_name": session_name,
        "recording_url": recording_url,
    }
    try:
        return client.table("recordings").insert(data).execute()
    except Exception as e:
        return {"error": str(e)}

def get_student_portal(user_id):
    client = get_admin_client()
    if not client:
        return {"profile": None, "recordings": [], "error": "Supabase not configured"}
    try:
        profile_res = client.table("profiles").select("*").eq("id", user_id).limit(1).execute()
        profile_rows = profile_res.data if hasattr(profile_res, "data") else []
        try:
            recordings_res = (
                client.table("recordings")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
        except Exception:
            recordings_res = client.table("recordings").select("*").eq("user_id", user_id).execute()
        recordings = recordings_res.data if hasattr(recordings_res, "data") else []
        return {
            "profile": profile_rows[0] if profile_rows else None,
            "recordings": recordings,
            "error": None,
        }
    except Exception as e:
        return {"profile": None, "recordings": [], "error": str(e)}

def insert_payment(user_id, amount, note=""):
    if not _HAS_SUPABASE:
        return None
    client = get_client()
    if not client:
        return None
    data = {"user_id": user_id, "amount": amount, "note": note}
    try:
        return client.table("payments").insert(data).execute()
    except Exception:
        return None

def insert_recording(user_id, recording_url, session_name=""):
    if not _HAS_SUPABASE:
        return None
    client = get_client()
    if not client:
        return None
    data = {"user_id": user_id, "recording_url": recording_url, "session_name": session_name}
    try:
        return client.table("recordings").insert(data).execute()
    except Exception:
        return None

def get_recordings(user_id):
    if not _HAS_SUPABASE:
        return []
    client = get_client()
    if not client:
        return []
    try:
        res = client.table("recordings").select("*").eq("user_id", user_id).execute()
        return res.data if hasattr(res, 'data') else []
    except Exception:
        return []

def set_meet_link(link, created_by=None, days_valid=90):
    client = get_client()
    if not client:
        return None
    from datetime import datetime, timedelta
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(days=days_valid)
    data = {
        "link": link,
        "created_by": created_by,
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    try:
        return client.table("meet_links").insert(data).execute()
    except Exception:
        return None

def get_active_meet_link():
    client = get_client()
    if not client:
        return None
    from datetime import datetime
    try:
        res = client.table("meet_links").select("*").order("created_at", desc=True).limit(1).execute()
    except Exception:
        return None
    rows = res.data if hasattr(res, 'data') else []
    if not rows:
        return None
    row = rows[0]
    expires = row.get("expires_at")
    try:
        expires_dt = datetime.fromisoformat(expires)
    except Exception:
        return None
    if datetime.utcnow() <= expires_dt:
        return {"link": row.get("link"), "expires_at": expires}
    return None
