from dotenv import load_dotenv
import os

load_dotenv()

# Try to import supabase client; if missing, keep the module usable so the app doesn't crash.
try:
    from supabase import create_client
    _HAS_SUPABASE = True
except Exception:
    create_client = None
    _HAS_SUPABASE = False

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

_client = None

def _auth_credentials(identifier, password):
    identifier = (identifier or "").strip()
    if "@" in identifier:
        return {"email": identifier, "password": password}
    return {"phone": identifier, "password": password}

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

def sign_up(identifier, password):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        response = client.auth.sign_up(_auth_credentials(identifier, password))
        user = _get_response_user(response)
        if user:
            upsert_student_profile(user)
        return response
    except Exception as e:
        return {"error": str(e)}

def sign_in(identifier, password):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        response = client.auth.sign_in_with_password(_auth_credentials(identifier, password))
        user = _get_response_user(response)
        if user:
            upsert_student_profile(user)
        return response
    except Exception as e:
        return {"error": str(e)}

def request_password_reset(identifier):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    identifier = (identifier or "").strip()
    try:
        if "@" in identifier:
            return client.auth.reset_password_for_email(identifier)
        return client.auth.sign_in_with_otp({"phone": identifier})
    except Exception as e:
        return {"error": str(e)}

def verify_phone_reset_otp(phone, token):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        return client.auth.verify_otp({"phone": phone, "token": token, "type": "sms"})
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

def upsert_student_profile(user):
    client = get_client()
    if not client:
        return None
    user_id = _get_user_value(user, "id")
    if not user_id:
        return None
    data = {
        "id": user_id,
        "email": _get_user_value(user, "email"),
        "phone": _get_user_value(user, "phone"),
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
