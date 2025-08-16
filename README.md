![Monsterrr Logo](Monsterrr.png)
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

## Discord Integration (Jarvis Mode)
Monsterrr now includes a professional Discord bot for real-time guidance, hourly updates, and AI-powered command execution—just like Jarvis in Iron Man.

### Features
- **Hourly Discord Notifications:** Get a summary of actions, suggestions, and pending tasks every hour in your chosen channel.
- **Daily Status Report:** Full daily report sent to Discord and email.
- **AI Command Handling:** Guide, override, or correct the 3 daily contributions using natural language commands.
- **Super Professional Responses:** All bot messages are branded and formal, Jarvis-style.

### Setup
1. **Add Discord Bot Credentials to `.env`**
   ```ini
   DISCORD_BOT_TOKEN=your-bot-token
   DISCORD_GUILD_ID=your-guild-id
   DISCORD_CHANNEL_ID=your-channel-id
   ```
2. **Invite the bot to your Discord server:**
   - Go to https://discord.com/developers/applications, create an app, add a bot, and copy the token.
   - Use the OAuth2 URL with 'bot' and 'message content' permissions to invite the bot to your server/channel.
3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Run Monsterrr:**
   ```sh
   python main.py
   ```
   The Discord bot will auto-start and operate in your specified channel.

### Discord Commands
- `!guide` — Show all available commands and usage instructions.
- `!status` — Get current Monsterrr system status.
- `!ideas` — View top AI-generated ideas.
- `!contribute <instructions>` — Guide or override the 3 daily contributions (e.g., prioritize, skip, fix).
- `!fix <issue/pr>` — Suggest or apply a fix for a specific issue or PR.
- `!skip <repo/issue>` — Skip a repo or issue in the next contributions.

**You can use natural language. If no instructions are given, Monsterrr will always execute 3 contributions per day by default.**

---

## Contact & Support
For questions, issues, or contributions, open an issue or contact [ni-sh-a-char](mailto:piyushmishra.professional@gmail.com).

---

> **Monsterrr: Your autonomous, always-on GitHub organization manager.**
