# Monsterrr

## 🚀 Autonomous AI for GitHub Organization Management

Monsterrr is a multi-agent, production-ready system that discovers, creates, and maintains open-source projects for your GitHub organization. Powered by Groq LLM, Monsterrr automates daily planning, contribution execution, and professional reporting—keeping your org healthy and growing 24/7.

---

## Features
- **AI-Driven Daily Planning:** Plans and executes exactly 3 meaningful contributions per day (repo creation or feature branch).
- **Multi-Agent Architecture:** Includes MaintainerAgent, CreatorAgent, and IdeaGeneratorAgent for full org automation.
- **Professional Daily Status Reports:** Sends quantifiable, transparent email reports with all ideas, actions, and metrics.
- **Audit Logging:** All actions and plans are saved for review and compliance.
- **Production-Ready:** Robust error handling, `.env`-only config, and seamless deployment to Render or Docker.

---

## Quick Start
1. **Clone & Install**
   ```sh
   git clone https://github.com/ni-sh-a-char/Monsterrr.git
   cd Monsterrr
   pip install -r requirements.txt
   ```
2. **Configure `.env`**
   - Create a `.env` file in the project root with the following fields:
   
   ```ini
   # ==== Groq API ====
   GROQ_API_KEY=sk-...         # Your Groq API key
   GROQ_MODEL=llama-3.3-70b-versatile  # Groq model name (default: llama-3.3-70b-versatile)
   GROQ_TEMPERATURE=0.2        # (Optional) Model temperature
   GROQ_MAX_TOKENS=2048        # (Optional) Max tokens for Groq responses

   # ==== GitHub ====
   GITHUB_TOKEN=ghp_...        # Your GitHub Personal Access Token (with repo/org permissions)
   GITHUB_ORG=your-org-slug    # Your GitHub organization name (slug)

   # ==== Email (SMTP) ====
   SMTP_HOST=smtp.gmail.com    # SMTP server host (e.g., smtp.gmail.com)
   SMTP_PORT=587               # SMTP server port (e.g., 587 for TLS)
   SMTP_USER=your-email@gmail.com   # Your email address (sender)
   SMTP_PASS=your-app-password     # SMTP password or app password

   # ==== Status Reports ====
   STATUS_REPORT_RECIPIENTS=you@example.com,teammate@example.com  # Comma-separated list of recipient emails

   # ==== Daily Activity Mode ====
   DAILY_ACTIVITY_MODE=enabled   # enabled/disabled (default: enabled)
   DRY_RUN=false                 # true for dry-run mode (logs only, no actions)
   MAX_AUTO_CREATIONS_PER_DAY=3  # Number of contributions per day (default: 3)
   ```

   - **Fill in each field with your actual credentials and settings.**
   - For Gmail, use an App Password (not your main password) and enable 2-Step Verification.
   - For GitHub, use a token with `repo` and `org` permissions.
   - You can add multiple emails to `STATUS_REPORT_RECIPIENTS` for team reports.
3. **Run Locally**
   ```sh
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
4. **Deploy to Render**
   - Connect your repo on Render.
   - Add all `.env` variables in the dashboard.
   - Use start command:
     ```sh
     uvicorn main:app --host 0.0.0.0 --port 8000
     ```

---

## API Endpoints
- `/` — Service status
- `/health` — Health check
- `/status` — Current state file
- `/trigger/idea-agent` — Manual idea generation
- `/ideas/generate` — Generate and rank ideas
- `/repos/create` — Create repo for top idea
- `/run-agents` — Trigger all agents

---

## Daily Automation & Reporting
- Scheduler runs daily at **00:00 UTC**
- Sends a professional status report email with:
  - Ideas proposed
  - Contributions planned/executed
  - Repositories created
  - Actions taken
  - Issues detected
- All actions are logged and auditable.

---

## Contact & Support
For questions, issues, or contributions, open an issue or contact [ni-sh-a-char](mailto:piyushmishra.professional@gmail.com).

---

> **Monsterrr: Your autonomous, always-on GitHub organization manager.**
