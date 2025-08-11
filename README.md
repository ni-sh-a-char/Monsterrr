# Monsterrr

Autonomous AI system for GitHub organization management.

## Overview
Monsterrr is a multi-agent, always-on system that discovers, creates, and maintains open-source projects for the `ni_sh_a.char` GitHub organization. It leverages the Groq LLM API for all reasoning and code generation, and automates repository management, issue triage, and project scaffolding.

## Features
- **Idea Generator Agent:** Fetches trending project ideas, summarizes and ranks them with Groq, and stores results.
- **Creator Agent:** Creates new repos, scaffolds code, commits boilerplate, and opens starter issues.
- **Maintainer Agent:** Monitors repos, responds to issues, auto-closes stale tickets, and suggests fixes with Groq.
- **Scheduler:** Runs daily/weekly jobs and sends a weekly status report email.
- **FastAPI API:** Webhooks, manual triggers, and status endpoints.
- **Production-ready:** Robust error handling, retries, logging, and CI/CD.

## Installation & Setup
1. Clone the repo and install dependencies:
	```sh
	git clone <your-org>/Monsterrr.git
	cd Monsterrr
	pip install -r requirements.txt
	```
2. Copy `.env.example` to `.env` and fill in your secrets:
	```sh
	cp .env.example .env
	# Edit .env with your keys and SMTP credentials
	```

## Running Locally
Start the API:
```sh
uvicorn main:app --reload
```
Start the scheduler:
```sh
python monsterrr/scheduler.py
```

## Running in Docker
Build and run (dev):
```sh
docker build -t monsterrr:dev --target dev .
docker run --env-file .env -p 8000:8000 monsterrr:dev
```


## Deployment to Render
1. Push code to your GitHub org.
2. Connect Render to the repo.
3. Add all .env variables in the Render dashboard.
4. Deploy both the API service and background worker (see `render.yaml`).

**Render Start Command:**
```
uvicorn main:app --host 0.0.0.0 --port 8000
```

## .env Variables
```
# ==== Groq API ====
GROQ_API_KEY=sk-your-groq-key-here
GROQ_MODEL=mixtral-8x7b      # Best tradeoff between cost, quality, and speed
GROQ_TEMPERATURE=0.2         # Low temp for factual, consistent outputs
GROQ_MAX_TOKENS=2048         # Long enough for detailed reports

# ==== GitHub ====
GITHUB_TOKEN=ghp-your-pat-here
GITHUB_ORG=ni-sh-a-char      # Matches your org slug exactly

# ==== Email (SMTP) ====
SMTP_HOST=smtp.gmail.com     # Gmail example, can be Outlook, Zoho, etc.
SMTP_PORT=587                # TLS port
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password  # Special app password (see below)

# ==== Status Reports ====
STATUS_REPORT_RECIPIENTS=you@example.com,teammate@example.com

```

## Weekly Status Report Example
```
Subject: Monsterrr Weekly Status Report

New repositories created: 2
Issues opened: 5 | Issues closed: 4
Top 3 project ideas:
  - OpenHealth NER (https://github.com/ni_sh_a.char/OpenHealth-NER)
  - DevOps Insights (https://github.com/ni_sh_a.char/DevOps-Insights)
  - PyData Visualizer (https://github.com/ni_sh_a.char/PyData-Visualizer)
PR activity: 3 merged, 1 open
Next week: [Groq-generated plan]
```

## Testing
Run all tests:
```sh
pytest --cov=monsterrr
```
Lint and format:
```sh
flake8 monsterrr && black monsterrr
```
