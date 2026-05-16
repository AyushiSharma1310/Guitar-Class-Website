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

def get_client():
    global _client
    if not _HAS_SUPABASE:
        return None
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return None
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client

def sign_up(email, password):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        return client.auth.sign_up({"email": email, "password": password})
    except Exception as e:
        return {"error": str(e)}

def sign_in(email, password):
    if not _HAS_SUPABASE:
        return {"error": "supabase package not installed"}
    client = get_client()
    if not client:
        return {"error":"Supabase not configured"}
    try:
        return client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        return {"error": str(e)}

def insert_payment(user_id, amount, note=""):
    if not _HAS_SUPABASE:
        return None
    client = get_client()
    if not client:
        return None
    data = {"user_id": user_id, "amount": amount, "note": note}
    return client.table("payments").insert(data).execute()

def insert_recording(user_id, recording_url, session_name=""):
    if not _HAS_SUPABASE:
        return None
    client = get_client()
    if not client:
        return None
    data = {"user_id": user_id, "recording_url": recording_url, "session_name": session_name}
    return client.table("recordings").insert(data).execute()

def get_recordings(user_id):
    if not _HAS_SUPABASE:
        return []
    client = get_client()
    if not client:
        return []
    res = client.table("recordings").select("*").eq("user_id", user_id).execute()
    return res.data if hasattr(res, 'data') else []

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
    return client.table("meet_links").insert(data).execute()

def get_active_meet_link():
    client = get_client()
    if not client:
        return None
    from datetime import datetime
    res = client.table("meet_links").select("*").order("created_at", desc=True).limit(1).execute()
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
