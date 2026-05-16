# Guitar Class — Streamlit app

Quick start

1. Create a Python venv and activate it.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
streamlit run app.py
```

4. (Optional) Provide your OpenAI API key in the sidebar to enable the AI assistant.

Data storage: a local SQLite database `data.db` is created in the project folder. Leads and chat logs are saved there.

Replace portfolio links and tutor details in `app.py` as needed.

Supabase integration

1. Create a Supabase project at https://app.supabase.com
2. Create two tables: `payments` (columns: `id`, `user_id`, `amount`, `note`, `created_at`) and `recordings` (columns: `id`, `user_id`, `recording_url`, `session_name`, `created_at`).
3. In your project, set the following environment variables (PowerShell example):

```powershell
setx SUPABASE_URL "https://xyz.supabase.co"
setx SUPABASE_KEY "your-anon-or-service-role-key"
```

4. Restart your terminal / editor so environment variables are available to Streamlit.

5. The app shows a sidebar for Sign up / Sign in (powered by Supabase Auth). Once signed in, users can record payments and view recordings.

Security note: Use `service_role` keys only on trusted backend operations. For client-side auth and reads/writes, prefer anon/public keys and Row Level Security (RLS) policies in Supabase.
