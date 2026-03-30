"""
Multi-Repo Cross-Team Dependency Risk Agent
============================================
Scans multiple GitHub repos for dependency-labeled issues,
analyzes risk signals, calls Claude AI for a prioritized summary,
and posts the weekly report as a GitHub Issue.

Author: Prisca Manokore | github.com/prissy04
"""

import os
import yaml
from datetime import datetime, timezone
from github import Github
import anthropic


# ── 1. LOAD CONFIGURATION ───────────────────────────────────────────────────

def load_config(path="config.yml"):
    """Load repo list, labels, and risk thresholds from config.yml."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


# ── 2. FETCH ISSUES FROM GITHUB ─────────────────────────────────────────────

def fetch_dependency_issues(github_client, repositories, dependency_labels, max_issues=100):
    """
    For each repo in the config, fetch all open issues that carry
    at least one of the dependency labels.

    Returns a list of issue dicts with key risk fields extracted.
    """
    all_issues = []

    for repo_name in repositories:
        print(f"  Scanning repo: {repo_name}")
        try:
            repo = github_client.get_repo(repo_name)
            issue_count = 0

            for issue in repo.get_issues(state="open"):
                # Stop scanning if we hit the max limit for this repo
                if issue_count >= max_issues:
                    print(f"  Reached max_issues_per_repo limit ({max_issues}) for {repo_name}")
                    break

                # Skip pull requests (GitHub API returns PRs as issues)
                if issue.pull_request:
                    continue

                # Check if any of the issue's labels match our dependency labels
                issue_label_names = [label.name.lower() for label in issue.labels]
                matched_labels = [
                    lbl for lbl in dependency_labels
                    if lbl.lower() in issue_label_names
                ]

                if not matched_labels:
                    issue_count += 1
                    continue

                # Calculate days since issue was opened
                now = datetime.now(timezone.utc)
                days_open = (now - issue.created_at).days

                # Calculate days since last update
                last_update = issue.updated_at
                days_since_update = (now - last_update).days

                all_issues.append({
                    "repo": repo_name,
                    "title": issue.title,
                    "number": issue.number,
                    "url": issue.html_url,
                    "days_open": days_open,
                    "days_since_update": days_since_update,
                    "assignee": issue.assignee.login if issue.assignee else None,
                    "milestone": issue.milestone.title if issue.milestone else None,
                    "matched_labels": matched_labels,
                    "body_preview": (issue.body or "")[:300],
                })

                issue_count += 1

        except Exception as e:
            print(f"  WARNING: Could not access repo {repo_name}: {e}")

    return all_issues


# ── 3. CALCULATE RISK SIGNALS ────────────────────────────────────────────────

def calculate_risk_level(issue, thresholds):
    """
    Score each issue as HIGH, MEDIUM, or LOW based on:
    - How long the issue has been open
    - Whether it has an assignee
    - Whether it has a milestone
    - How recently it was updated (staleness)
    """
    score = 0

    # Days open scoring
    if issue["days_open"] >= thresholds["high_days_open"]:
        score += 3
    elif issue["days_open"] >= thresholds["medium_days_open"]:
        score += 2
    else:
        score += 1

    # No assignee = higher risk (nobody owns it)
    if not issue["assignee"]:
        score += 2

    # No milestone = higher risk (not tied to a delivery)
    if not issue["milestone"]:
        score += 1

    # Staleness — no update in X days
    if issue["days_since_update"] >= thresholds["stale_days_no_update"]:
        score += 2

    # Map score to risk level
    if score >= 6:
        return "HIGH"
    elif score >= 3:
        return "MEDIUM"
    else:
        return "LOW"


def enrich_issues_with_risk(issues, thresholds):
    """Add risk level to each issue dict."""
    for issue in issues:
        issue["risk_level"] = calculate_risk_level(issue, thresholds)
    return issues


# ── 4. CALL CLAUDE AI FOR RISK SUMMARY ──────────────────────────────────────

def generate_ai_summary(issues, anthropic_client):
    """
    Send the enriched issue list to Claude Haiku.
    Claude reasons over the risk signals and returns a prioritized,
    plain-English weekly summary with recommendations.
    """
    if not issues:
        return "No dependency-labeled issues found across monitored repositories this week. All clear!"

    issues_text = ""
    for i, issue in enumerate(issues, 1):
        issues_text += f"""
Issue {i}:
  Repo: {issue['repo']}
  Title: {issue['title']}
  URL: {issue['url']}
  Risk Level: {issue['risk_level']}
  Days Open: {issue['days_open']}
  Days Since Last Update: {issue['days_since_update']}
  Assignee: {issue['assignee'] or 'UNASSIGNED'}
  Milestone: {issue['milestone'] or 'NONE'}
  Labels: {', '.join(issue['matched_labels'])}
  Description Preview: {issue['body_preview'] or 'No description provided.'}
"""

    prompt = f"""You are an AI assistant helping a Technical Program Manager (TPM) understand
cross-team dependency risks across multiple GitHub repositories.

Below is a list of open GitHub issues labeled as cross-team dependencies,
along with their risk signals. Your job is to:
1. Group them by risk level (HIGH, MEDIUM, LOW)
2. For each issue, write a brief 2-3 sentence analysis of why it is risky
3. Provide a specific, actionable recommendation for the TPM
4. Write an executive summary at the top (3-4 sentences max)

Use clear, professional language. Write for a TPM audience, not an engineering audience.
Avoid jargon. Focus on business impact and delivery risk.

Format your response in Markdown so it renders cleanly as a GitHub Issue.

Here are this week's dependency issues:
{issues_text}

Generate the weekly risk report now."""

    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text


# ── 5. POST REPORT AS A GITHUB ISSUE ────────────────────────────────────────

def post_report_as_issue(github_client, report_repo, report_content, issue_count):
    """
    Post the weekly risk report as a new GitHub Issue
    in the agent's own repository.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = f"🤖 Weekly Dependency Risk Report — {today} ({issue_count} issues found)"

    header = f"""## Weekly Dependency Risk Report
**Generated:** {today}
**Issues Scanned:** {issue_count}
**Agent:** Multi-Repo Cross-Team Dependency Risk Agent

---

"""
    full_body = header + report_content

    repo = github_client.get_repo(report_repo)
    issue = repo.create_issue(
        title=title,
        body=full_body,
        labels=["dependency-report"]
    )
    print(f"  Report posted: {issue.html_url}")
    return issue.html_url


# ── 6. MAIN ORCHESTRATOR ─────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Multi-Repo Dependency Risk Agent — Starting Run")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    print("\n[1/5] Loading configuration...")
    config = load_config("config.yml")
    repositories = config["repositories"]
    dependency_labels = config["dependency_labels"]
    thresholds = config["risk_thresholds"]
    report_repo = config["report_repository"]
    max_issues = config.get("max_issues_per_repo", 100)
    print(f"  Monitoring {len(repositories)} repositories")
    print(f"  Labels: {', '.join(dependency_labels)}")
    print(f"  Max issues per repo: {max_issues}")

    print("\n[2/5] Initializing API clients...")
    github_token = os.environ["GH_TOKEN"]
    anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]
    github_client = Github(github_token)
    anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
    print("  GitHub and Anthropic clients ready")

    print("\n[3/5] Fetching dependency-labeled issues from GitHub...")
    issues = fetch_dependency_issues(
        github_client, repositories, dependency_labels, max_issues
    )
    print(f"  Found {len(issues)} dependency issues across all repos")

    print("\n[4/5] Calculating risk levels...")
    issues = enrich_issues_with_risk(issues, thresholds)
    high = sum(1 for i in issues if i["risk_level"] == "HIGH")
    medium = sum(1 for i in issues if i["risk_level"] == "MEDIUM")
    low = sum(1 for i in issues if i["risk_level"] == "LOW")
    print(f"  HIGH: {high}  |  MEDIUM: {medium}  |  LOW: {low}")

    print("\n[5/5] Generating AI risk summary with Claude...")
    report = generate_ai_summary(issues, anthropic_client)
    print("  AI summary generated")

    print("\nPosting report as GitHub Issue...")
    report_url = post_report_as_issue(
        github_client, report_repo, report, len(issues)
    )

    print("\n" + "=" * 60)
    print("  Run complete!")
    print(f"  Report: {report_url}")
    print("=" * 60)


if __name__ == "__main__":
    main()
