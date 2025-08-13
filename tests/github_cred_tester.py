#!/usr/bin/env python3
"""
github_cred_tester.py

Checks that the GITHUB_TOKEN and GITHUB_ORG in your .env are valid and that
the token has the permissions required for the Monsterrr project.

By default this script runs in DRY_RUN mode (no write actions). To perform
write-checks (create a test repo, create a file), pass --apply.

Usage:
  # dry-run checks only
  python github_cred_tester.py

  # perform write checks (create temp repo + file). Add --cleanup to delete test repo afterwards.
  python github_cred_tester.py --apply --cleanup

Outputs:
 - prints concise, redacted diagnostics
 - prints full HTTP failure response bodies when an API call fails (for debugging)
"""

import os
import sys
import argparse
import base64
import json
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

# ---------------------------
# Helpers
# ---------------------------
load_dotenv()  # loads .env from current directory if present

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_ORG = os.getenv("GITHUB_ORG")
API_BASE = "https://api.github.com"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"} if GITHUB_TOKEN else {}

def redact(s: str, keep=6):
    if not s:
        return "MISSING"
    if len(s) <= keep + 4:
        return s[0:keep] + "..."
    return s[:keep] + "..." + s[-4:]

def pretty_print_response(resp: requests.Response):
    print(f"HTTP {resp.status_code}")
    # print headers that are useful
    for k in ("X-OAuth-Scopes", "X-Accepted-OAuth-Scopes", "X-RateLimit-Remaining", "X-RateLimit-Reset"):
        if k in resp.headers:
            print(f"{k}: {resp.headers[k]}")
    try:
        j = resp.json()
        print(json.dumps(j, indent=2)[:4000])
    except Exception:
        text = resp.text or "<no body>"
        print(text[:4000])

# ---------------------------
# Tests
# ---------------------------
def check_environment():
    print("Checking environment variables:")
    print(f"  GITHUB_ORG = {GITHUB_ORG or 'MISSING'}")
    print(f"  GITHUB_TOKEN = {redact(GITHUB_TOKEN)}")
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN missing. Create a PAT and put it in .env as GITHUB_TOKEN.")
        return False
    if not GITHUB_ORG:
        print("ERROR: GITHUB_ORG missing. Set it in .env (for this project it should be 'ni-sh-a-char').")
        return False
    return True

def auth_check():
    print("\n1) Testing token validity (GET /user)...")
    url = f"{API_BASE}/user"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        print("  Token is valid. Authenticated user:")
        print(f"    login: {data.get('login')}")
        print(f"    id: {data.get('id')}")
        if 'X-OAuth-Scopes' in resp.headers:
            print(f"    scopes: {resp.headers.get('X-OAuth-Scopes')}")
        return True, data.get("login")
    else:
        print("  AUTH check failed:")
        pretty_print_response(resp)
        return False, None

def org_check(login):
    print("\n2) Testing organization visibility & membership...")
    url = f"{API_BASE}/orgs/{GITHUB_ORG}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        print(f"  Organization '{GITHUB_ORG}' exists.")
        # membership test - try to fetch membership for authenticated user
        mem_url = f"{API_BASE}/user/memberships/orgs/{GITHUB_ORG}"
        resp2 = requests.get(mem_url, headers=HEADERS, timeout=10)
        if resp2.status_code == 200:
            m = resp2.json()
            state = m.get("state")
            role = m.get("role")
            print(f"  You are a member of the org (state={state}, role={role}).")
            return True
        else:
            # alternative: check if the user is visible in members list (may be blocked by permission)
            members_url = f"{API_BASE}/orgs/{GITHUB_ORG}/members/{login}"
            resp3 = requests.get(members_url, headers=HEADERS, timeout=10)
            if resp3.status_code == 204:
                print("  You are a visible org member.")
                return True
            elif resp3.status_code == 404:
                print("  You are NOT a visible member of the org according to API.")
                print("  Cause: token lacks 'read:org' or you are not a member / membership is pending.")
                return False
            else:
                print("  Unexpected response when checking membership:")
                pretty_print_response(resp3)
                return False
    else:
        print(f"  Could not fetch org '{GITHUB_ORG}':")
        pretty_print_response(resp)
        return False

def try_create_repo(repo_name):
    print(f"\n3) Attempting to create a test repository in org '{GITHUB_ORG}': {repo_name}")
    url = f"{API_BASE}/orgs/{GITHUB_ORG}/repos"
    body = {
        "name": repo_name,
        "description": "Monsterrr credentials check repo - will be deleted by tester",
        "private": True,
        "auto_init": False,
        "visibility": "private"
    }
    resp = requests.post(url, headers=HEADERS, json=body, timeout=15)
    if resp.status_code in (201,):
        print("  Repo created successfully.")
        repo_full_name = resp.json().get("full_name")
        print(f"  full_name: {repo_full_name}")
        return True, repo_full_name
    else:
        print("  Repo creation failed:")
        pretty_print_response(resp)
        return False, None

def create_readme_and_commit(repo_full_name):
    print("\n4) Creating README via Contents API...")
    url = f"{API_BASE}/repos/{repo_full_name}/contents/README.md"
    content = "# Monsterrr CI test\nThis repo was created by github_cred_tester.py"
    b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    body = {
        "message": "chore: add README (cred tester)",
        "content": b64,
        "branch": "main"
    }
    resp = requests.put(url, headers=HEADERS, json=body, timeout=15)
    if resp.status_code in (201, 200):
        print("  README created successfully.")
        return True
    else:
        print("  README creation failed:")
        pretty_print_response(resp)
        return False

def delete_repo(repo_full_name):
    print(f"\n5) Deleting test repo {repo_full_name} ...")
    url = f"{API_BASE}/repos/{repo_full_name}"
    resp = requests.delete(url, headers=HEADERS, timeout=15)
    if resp.status_code in (204,):
        print("  Repo deleted successfully.")
        return True
    else:
        print("  Repo deletion failed:")
        pretty_print_response(resp)
        return False

# ---------------------------
# Main CLI
# ---------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Perform write checks (create/delete a test repo)")
    parser.add_argument("--cleanup", action="store_true", help="When using --apply, delete the test repo afterward")
    args = parser.parse_args()

    ok = check_environment()
    if not ok:
        sys.exit(2)

    auth_ok, login = auth_check()
    if not auth_ok:
        print("Aborting further checks because token is invalid.")
        sys.exit(2)

    org_ok = org_check(login)
    if not org_ok:
        print("Organization access check failed. Make sure your token has required scopes and you are a member/owner of the org.")
        # don't exit immediately if dry-run; but advise.
        if not args.apply:
            sys.exit(2)

    if not args.apply:
        print("\nDRY-RUN complete. Token and org checks finished. To run write tests, re-run with --apply.")
        sys.exit(0)

    # Apply mode: create a temp repo, add README, optionally delete
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    repo_name = f"monsterrr-cred-test-{ts}"
    created, repo_full_name = try_create_repo(repo_name)
    if not created:
        print("Write-check failed (couldn't create repo). Ensure token has repo creation permission for the organization and that you are an org owner or have repo creation rights.")
        sys.exit(3)

    readme_ok = create_readme_and_commit(repo_full_name)
    if not readme_ok:
        print("Failed to commit a README to the created repo.")
        # attempt cleanup if requested
        if args.cleanup:
            delete_repo(repo_full_name)
        sys.exit(4)

    print("\nWrite tests succeeded (repo created and README committed).")

    if args.cleanup:
        deleted = delete_repo(repo_full_name)
        if not deleted:
            print("WARNING: cleanup failed; the test repo may still exist. Please delete it manually.")
            sys.exit(5)
        else:
            print("Cleanup complete.")

    print("\nAll checks passed. Your GITHUB_TOKEN and GITHUB_ORG appear valid for Monsterrr operations.")
    sys.exit(0)

if __name__ == "__main__":
    main()
