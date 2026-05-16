from dotenv import load_dotenv
import os

load_dotenv()

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

_client = None

def _auth_credentials(email, password):
    return {"email": (email or "").strip(), "password": password}

def _signup_credentials(email, phone, password):
    return {
        "email": (email or "").strip(),
        "password": password,
        "options": {"data": {"phone": (phone or "").strip()}},
    }

def _get_user_value(user, field):
    if isinstance(user, dict):
        return user.get(field)
    return getattr(user, field, None)

def _get_response_user(response):
    if isinstance(response, dict):
        return response.get("user")
    return getattr(response, "user", None)

def get_client():
    global _client
    if not _HAS_SUPABASE:
        return None
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return None
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client

def sign_up(email, phone, password):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        response = client.auth.sign_up(_signup_credentials(email, phone, password))
        user = _get_response_user(response)
        if user:
            upsert_student_profile(user, phone=phone)
        return response
    except Exception as e:
        return {"error": str(e)}

def sign_in(email, password):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        response = client.auth.sign_in_with_password(_auth_credentials(email, password))
        user = _get_response_user(response)
        if user:
            upsert_student_profile(user)
        return response
    except Exception as e:
        return {"error": str(e)}

def request_email_otp(email):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        return client.auth.sign_in_with_otp(
            {
                "email": (email or "").strip(),
                "options": {"should_create_user": False},
            }
        )
    except Exception as e:
        return {"error": str(e)}

def verify_email_otp(email, token):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        return client.auth.verify_otp(
            {"email": (email or "").strip(), "token": token, "type": "email"}
        )
    except Exception as e:
        return {"error": str(e)}

def update_password(new_password):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        return client.auth.update_user({"password": new_password})
    except Exception as e:
        return {"error": str(e)}

def upsert_student_profile(user, phone=None):
    client = get_client()
    if not client:
        return None
    user_id = _get_user_value(user, "id")
    if not user_id:
        return None
    data = {
        "id": user_id,
        "email": _get_user_value(user, "email"),
        "phone": phone or _get_user_value(user, "phone"),
    }
    try:
        return client.table("profiles").upsert(data).execute()
    except Exception:
        return None

def get_student_profiles():
    client = get_client()
    if not client:
        return {"data": [], "error": "Supabase not configured"}
    try:
        res = client.table("profiles").select("*").order("created_at", desc=True).execute()
        return {"data": res.data if hasattr(res, "data") else [], "error": None}
    except Exception as e:
        return {"data": [], "error": str(e)}

def update_student_access(user_id, is_paid, next_session_at="", live_session_link=""):
    client = get_client()
    if not client:
        return {"error": "Supabase not configured"}
    data = {
        "is_paid": bool(is_paid),
        "next_session_at": next_session_at,
        "live_session_link": live_session_link,
    }
    try:
        return client.table("profiles").update(data).eq("id", user_id).execute()
    except Exception as e:
        return {"error": str(e)}

def add_recording_for_student(user_id, session_name, recording_url):
    client = get_client()
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
    client = get_client()
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
