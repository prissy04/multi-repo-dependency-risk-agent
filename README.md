# 🤖 Multi-Repo Cross-Team Dependency Risk Agent

> An AI-powered GitHub Action that monitors dependency-tagged issues across multiple repositories and delivers a weekly prioritized risk summary — built by a TPM, for TPMs.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Automated-green)
![Claude AI](https://img.shields.io/badge/Claude_AI-Haiku-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 📌 Problem Statement

Enterprise Technical Program Managers managing programs across multiple engineering teams spend significant time each week manually chasing dependency status. The typical workflow looks like this:

- Ping Team A on Slack: *"Is the API contract finalized?"*
- Check Jira, GitHub, email for updates
- Compile a spreadsheet of blocking issues
- Repeat for every team, every week

This process is manual, error-prone, and does not scale. When a dependency slips, a TPM often finds out too late — after it has already cascaded into missed milestones for downstream teams.

**No open-source tool exists that solves this problem from the TPM's perspective.** Existing tools like GitHub Dependabot and the Dependency Review Action monitor *code package vulnerabilities* — not *cross-team project dependencies*. This agent fills that gap.

---

## 💼 Business Justification

### The Cost of Manual Dependency Tracking

| Pain Point | Impact |
|---|---|
| Manual status collection across teams | 3–5 hours per TPM per week |
| Late discovery of blocked dependencies | Milestone delays, executive escalations |
| No single source of truth across repos | Misalignment between teams, duplicate effort |
| Inconsistent risk prioritization | High-risk items treated the same as low-risk |

### Why This Matters to Organizations

In programs spanning 5–15 engineering teams, a single unresolved dependency can cascade into delays across multiple workstreams. Traditional project management tools like Jira and Asana address this within a single workspace — but enterprise programs often span multiple GitHub repositories managed by different teams, with no unified view of cross-repo dependency health.

This agent automates the weekly dependency triage process entirely, giving TPMs back their time and giving leadership a consistent, AI-generated risk brief every Monday morning.

---

## 🔍 Market Validation

Before building, I researched the existing tool landscape:

| Tool | What It Does | Gap |
|---|---|---|
| **GitHub Dependabot** | Detects vulnerable code packages (CVEs) | Not for project/team dependencies |
| **Dependency Review Action** | Flags insecure packages in PRs | Single-repo, code-level only |
| **Multi-repo config auditors** | Check config drift across repos | Not TPM-focused, no risk summary |
| **Jira / Linear** | Task tracking within a paid workspace | Siloed per team, no cross-repo GitHub view |
| **Weekly code change summaries** | Summarize commits via Slack | Not dependency-aware, no risk analysis |

**Confirmed gap:** No open-source GitHub-native tool monitors cross-team *project* dependency issues across multiple repos and generates a TPM-style AI risk brief.

---

## ✅ What This Agent Does

1. **Scans** multiple GitHub repositories for issues labeled `dependency`, `blocked`, or `cross-team`
2. **Analyzes** risk signals for each issue:
   - Days open without update (staleness)
   - Missing assignee
   - No milestone attached
   - Linked to other blocking issues
3. **Calls Claude AI (Haiku)** to reason over the risk signals and generate a prioritized summary with plain-English recommendations
4. **Posts** the weekly report as a new GitHub Issue every Monday at 8 AM UTC — automatically, with no manual intervention

---

## 📋 Sample Output

The agent generates a GitHub Issue every week that looks like this:

```
## 🔴 Weekly Dependency Risk Report — Week of 2025-01-13

### Executive Summary
3 high-risk dependencies detected across 4 repositories.
Immediate attention required on auth-service and payments-api.

---

### 🔴 HIGH RISK

**[auth-service] API contract for OAuth 2.0 token refresh not finalized**
- Repo: org/auth-service | Issue #142
- Open for: 18 days | Assignee: None | Milestone: None
- Risk: Blocking 2 downstream teams (checkout-ui, mobile-app)
- Recommendation: Escalate to auth-service lead. Assign owner immediately.
  Schedule sync with downstream teams to unblock parallel work.

---

### 🟡 MEDIUM RISK

**[payments-api] Webhook retry logic decision pending**
- Repo: org/payments-api | Issue #89
- Open for: 9 days | Assignee: @jsmith | Milestone: Q1-Release
- Risk: No update in 6 days. Milestone at risk if not resolved this week.
- Recommendation: Request status update from @jsmith by EOD Wednesday.

---

### 🟢 LOW RISK

**[data-pipeline] Schema migration approach — decision in progress**
- Repo: org/data-pipeline | Issue #201
- Open for: 3 days | Assignee: @ateam | Milestone: Q1-Release
- Risk: Recently opened, actively being discussed.
- Recommendation: Monitor. No action needed this week.
```

---

## 🏗️ Technical Architecture

```
┌─────────────────────────────────────────────────────┐
│                  GitHub Actions                      │
│            (Scheduled: Every Monday 8AM)             │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              Python Agent (agent.py)                 │
│                                                      │
│  1. Read config (repos + labels to monitor)          │
│  2. Call GitHub API → fetch labeled issues           │
│  3. Calculate risk signals per issue                 │
│  4. Call Claude API → generate risk summary          │
│  5. Post report as new GitHub Issue                  │
└──────────┬──────────────────────┬───────────────────┘
           │                      │
           ▼                      ▼
┌──────────────────┐   ┌──────────────────────────┐
│   GitHub API     │   │   Anthropic Claude API   │
│  (PyGithub)      │   │   (claude-haiku)         │
│  - List issues   │   │   - Risk prioritization  │
│  - Filter labels │   │   - Plain-English summary│
│  - Post report   │   │   - Recommendations      │
└──────────────────┘   └──────────────────────────┘
```

### Tech Stack

| Component | Technology | Why |
|---|---|---|
| Agent logic | Python 3.11 | Clean GitHub/Anthropic SDK support |
| GitHub integration | PyGithub | Official Python wrapper for GitHub API |
| AI reasoning layer | Anthropic Claude Haiku | Low cost (~$0.01/run), fast, capable |
| Scheduling & execution | GitHub Actions | Free for public repos, no infrastructure needed |
| Report delivery | GitHub Issues | Native to where developers already work |

---

## ⚙️ Configuration

The agent is configured via a simple `config.yml` file at the root of the repository:

```yaml
# repos to monitor (format: owner/repo-name)
repositories:
  - your-org/auth-service
  - your-org/payments-api
  - your-org/data-pipeline
  - your-org/mobile-app

# labels that signal a cross-team dependency
dependency_labels:
  - dependency
  - blocked
  - cross-team
  - waiting-on-external

# risk thresholds
risk_thresholds:
  high_days_open: 14       # Issues open longer than this = HIGH risk
  medium_days_open: 7      # Issues open longer than this = MEDIUM risk
  stale_days_no_update: 5  # No comment in this many days = staleness flag
```

---

## 🚀 Setup & Deployment

### Prerequisites
- GitHub account with access to the repositories you want to monitor
- Anthropic API key (free tier sufficient for this use case)

### Step 1: Fork or clone this repository

```bash
git clone https://github.com/prissy04/multi-repo-dependency-risk-agent.git
cd multi-repo-dependency-risk-agent
```

### Step 2: Add secrets to GitHub

In your repository settings → Secrets and variables → Actions, add:

| Secret Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `GH_TOKEN` | A GitHub Personal Access Token with `repo` scope |

### Step 3: Edit `config.yml`

Update the `repositories` list with the repos you want to monitor, and customize the labels to match your team's conventions.

### Step 4: Push and let it run

The GitHub Action runs automatically every Monday at 8 AM UTC. You can also trigger it manually from the Actions tab using `workflow_dispatch`.

---

## 💰 Cost Analysis

| Component | Cost |
|---|---|
| GitHub Actions | **Free** (public repo) |
| GitHub API | **Free** (within rate limits) |
| Claude Haiku per weekly run | **~$0.01** |
| Monthly total (4 runs) | **~$0.04** |

This is effectively free to operate.

---

## 📊 TPM Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| GitHub API rate limiting on large orgs | Low | Medium | Implement exponential backoff |
| Claude API response format variability | Low | Low | Structured prompt with fallback parsing |
| False positives (low-risk issues flagged high) | Medium | Low | Configurable thresholds in `config.yml` |
| Secret exposure in logs | Low | High | Secrets stored as GitHub Actions secrets, never logged |

---

## 🧠 TPM Lens: Why I Built This

As a Technical Program Manager with enterprise experience at Microsoft, SAS, and MetLife, I have personally lived the pain this tool solves. Dependency tracking across multi-team programs is one of the highest-friction, lowest-leverage activities a TPM does manually.

The insight behind this project: the data already exists in GitHub Issues. Teams are already labeling blockers and dependencies. The missing piece was an automated agent that reads those signals, applies risk logic, and surfaces them in a consistent, actionable format — without the TPM having to chase anyone.

This project demonstrates three things I believe define a modern TPM:

1. **Systems thinking** — identifying the workflow gap and designing an automated solution
2. **Technical execution** — building a working agent, not just a slide deck about one
3. **AI fluency** — using Claude not as a chatbot, but as a reasoning layer inside a production workflow

---

## 🗺️ Roadmap

- [x] Core agent: GitHub Issues scan + Claude risk summary
- [x] GitHub Actions scheduled workflow
- [x] Configurable repos and labels
- [ ] Slack notification integration
- [ ] Risk trend tracking week-over-week
- [ ] Email digest option
- [ ] Support for GitLab repositories

---

## 📄 License

MIT License — free to use, adapt, and deploy in your organization.

---

## 🤝 Contributing

Contributions welcome. If you are a TPM or engineering leader who has ideas for additional risk signals or report formats, open an issue and let's discuss.

---

*Built by [Prisca Manokore](https://github.com/prissy04) — TPM | AI Portfolio Project*
