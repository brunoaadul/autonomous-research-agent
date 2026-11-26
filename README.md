# Crokuta Research Agent

A FastAPI research API with a web workspace for account registration, login, research briefs, and follow-up chat. Account profiles and owner-scoped conversations are stored in MySQL, so you can run a hosted instance or deploy a separate installation on your own server. Public signup is enabled by default.

## Run locally or self-host

1. Install MySQL 8 or a compatible server and create a database and a dedicated account for the app. For example, run as a MySQL administrator:

   ```sql
   CREATE DATABASE research CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'crokuta'@'localhost' IDENTIFIED BY 'replace-with-a-strong-password';
   GRANT ALL PRIVILEGES ON research.* TO 'crokuta'@'localhost';
   ```

2. Copy `.env.example` to `.env`. Set `DATABASE_URL` to your MySQL connection string:

   ```text
   DATABASE_URL=mysql+pymysql://crokuta:your-password@localhost:3306/research?charset=utf8mb4
   ```

   URL-encode special characters in the username or password. Keep `.env` private and do not commit it.

3. Install dependencies and start the application:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

4. Open `http://127.0.0.1:8000/`. On first use, the app creates its user, profile, session, conversation, and message tables in the configured database. Signup collects full name, phone number, email, country, and password. Research briefs and chat messages are stored per user and can be reopened or permanently deleted from the workspace.

For production, run the app behind an HTTPS reverse proxy, use a dedicated MySQL account with access only to the app database, and configure the required LLM provider key on the server. Do not expose the database publicly or put provider secrets in browser code.

## Hosted instance

To offer a hosted instance, deploy this application on a server or hosting platform that supports a persistent FastAPI process and outbound MySQL connections. Configure `DATABASE_URL` and the desired server-side LLM provider credentials in that deployment's environment, then serve the app over HTTPS. Users of the hosted instance share its account database; each self-hosted installation has its own separate database and accounts.

The research endpoint currently creates a structured preliminary brief; it does not fetch or verify external sources. Follow-up chat uses the selected LLM provider. Configure that provider's API key in the server environment (for example `OPENAI_API_KEY`) or run the selected local model.

## Engineering documentation

- [Product requirements and acceptance criteria](docs/requirements.md)
- [SDLC, delivery objectives, and release gates](docs/SDLC.md)
- [Architecture overview](docs/architecture.md)
- [System design and API/data behavior](docs/system-design.md)
- [Scaling and reliability strategy](docs/scaling.md)
- [Contributor/agent repository guidance](AGENTS.md)

> **Distribution note:** This repository does not currently include a `LICENSE` file. Add a license that matches your intended terms before advertising redistribution or reuse as free/open-source software.
