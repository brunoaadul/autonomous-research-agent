# Crokuta Research Agent

A FastAPI research API with a small web workspace for account registration, login, research briefs, and follow-up chat.

## Run locally

1. Create a Supabase project and enable Email authentication. For a friction-free local test, disable email confirmation in **Authentication → Providers → Email**; otherwise, users need to confirm their email before signing in.
2. Copy `.env.example` to `.env` and set `SUPABASE_URL` and `SUPABASE_ANON_KEY` from the Supabase project's API settings.
3. Install dependencies and start the API:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
   ```

4. Open `http://127.0.0.1:8000/` for the workspace or `http://127.0.0.1:8000/docs` for the API docs.

The research endpoint currently creates a structured preliminary brief; it does not fetch or verify external sources. Follow-up chat uses the selected LLM provider. Configure that provider's API key in the server environment (for example `OPENAI_API_KEY`) or run the selected local model. Never put provider secrets in browser code.

## Deploy to Vercel

1. Push this repository to GitHub and import it into Vercel. Vercel detects the FastAPI app in `app/main.py`; `vercel.json` includes the web workspace assets in the function bundle.
2. In Vercel **Project Settings → Environment Variables**, add:
   - `SUPABASE_URL` — the Supabase project URL.
   - `SUPABASE_ANON_KEY` — the project's anon/publishable key.
   - The server-side LLM provider key you intend to use, such as `OPENAI_API_KEY`, or the provider's environment settings.
3. In Supabase, configure the allowed auth redirect URLs for your Vercel deployment domain. If email confirmation is enabled, include the production URL and test confirmation emails.
4. Redeploy after setting environment variables, then open `https://<your-vercel-domain>/`.

The frontend and API share one origin, so no separate API URL or CORS configuration is needed. Supabase stores user accounts; the browser stores each signed-in user's recent briefs locally.