#!/usr/bin/env python3
"""Collect the GitHub half of the daily headsup as JSON.

Uses the authenticated `gh` CLI (no extra dependencies). Prints one JSON
object to stdout with four lists:

  my_prs            open PRs I authored, with CI / review state and age
  review_requests   open PRs waiting on my review
  assigned_issues   open issues assigned to me
  mentions          unread notifications where I was @mentioned / team-mentioned
  waiting_on_me     open PRs/issues by others that I've taken part in, where the
                    last comment is someone else's (often an unanswered question)

Each item carries `age_days` (since creation) and `idle_days` (since last
update) so the caller can judge rot without re-deriving dates.

PRs and issues also carry `last_comment` ({by, days_ago, snippet}).

Usage: uv run scripts/github_snapshot.py [--limit N] [--waiting-days N]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta

PR_FIELDS = """
  ... on PullRequest {
    number title url isDraft createdAt updatedAt
    repository { nameWithOwner }
    author { login }
    reviewDecision
    mergeable
    reviewRequests(first: 10) { totalCount }
    latestReviews(first: 10) { nodes { state author { login } } }
    commits(last: 1) { nodes { commit { statusCheckRollup { state } } } }
    comments(last: 1) { nodes { author { login } createdAt bodyText } }
  }
"""

ISSUE_FIELDS = """
  ... on Issue {
    number title url createdAt updatedAt
    repository { nameWithOwner }
    labels(first: 10) { nodes { name } }
    comments(last: 1) { nodes { author { login } createdAt bodyText } }
  }
"""

# One search per request, paginated in small pages. A single query with all four
# searches at 50 results each blows past GitHub's ~10s GraphQL timeout (HTTP 502).
SEARCH_QUERY = """
query($q: String!, $first: Int!, $after: String) {
  search(query: $q, type: ISSUE, first: $first, after: $after) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes { %s }
  }
}
"""
PAGE_SIZE = 20


def gh(*args: str) -> str:
    try:
        out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit(json.dumps({"error": "gh CLI not installed"}))
    except subprocess.CalledProcessError as exc:
        sys.exit(
            json.dumps(
                {
                    "error": f"gh {' '.join(args[:2])} failed",
                    "stderr": exc.stderr.strip(),
                }
            )
        )
    return out.stdout


def search(q: str, fields: str, limit: int) -> dict:
    """Run one GitHub search, paging until `limit` nodes; returns {issueCount, nodes}."""
    nodes: list[dict] = []
    after: str | None = None
    count = 0
    while len(nodes) < limit:
        args = [
            "api",
            "graphql",
            "-f",
            f"query={SEARCH_QUERY % fields}",
            "-f",
            f"q={q}",
            "-F",
            f"first={min(PAGE_SIZE, limit - len(nodes))}",
        ]
        if after:
            args += ["-f", f"after={after}"]
        page = json.loads(gh(*args))["data"]["search"]
        count = page["issueCount"]
        nodes += [n for n in page["nodes"] if n]
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    return {"issueCount": count, "nodes": nodes}


def days_since(iso: str | None, now: datetime) -> int | None:
    if not iso:
        return None
    return (now - datetime.fromisoformat(iso)).days


def last_comment(node: dict, now: datetime) -> dict | None:
    nodes = (node.get("comments") or {}).get("nodes") or []
    if not nodes:
        return None
    c = nodes[0]
    return {
        "by": (c.get("author") or {}).get("login"),
        "days_ago": days_since(c.get("createdAt"), now),
        "snippet": " ".join((c.get("bodyText") or "").split())[:240],
    }


def shape_pr(node: dict, now: datetime) -> dict:
    commits = node.get("commits", {}).get("nodes") or []
    rollup = (commits[0]["commit"].get("statusCheckRollup") or {}) if commits else {}
    return {
        "repo": node["repository"]["nameWithOwner"],
        "number": node["number"],
        "title": node["title"],
        "url": node["url"],
        "author": (node.get("author") or {}).get("login"),
        "draft": node["isDraft"],
        "ci": rollup.get("state"),  # SUCCESS / FAILURE / PENDING / ERROR / None
        "review_decision": node.get(
            "reviewDecision"
        ),  # APPROVED / CHANGES_REQUESTED / REVIEW_REQUIRED / None
        "mergeable": node.get("mergeable"),  # MERGEABLE / CONFLICTING / UNKNOWN
        "pending_review_requests": node["reviewRequests"]["totalCount"],
        "reviews": [
            {"by": (r.get("author") or {}).get("login"), "state": r["state"]}
            for r in node["latestReviews"]["nodes"]
        ],
        "last_comment": last_comment(node, now),
        "age_days": days_since(node["createdAt"], now),
        "idle_days": days_since(node["updatedAt"], now),
    }


def shape_issue(node: dict, now: datetime) -> dict:
    return {
        "repo": node["repository"]["nameWithOwner"],
        "number": node["number"],
        "title": node["title"],
        "url": node["url"],
        "labels": [label["name"] for label in node["labels"]["nodes"]],
        "last_comment": last_comment(node, now),
        "age_days": days_since(node["createdAt"], now),
        "idle_days": days_since(node["updatedAt"], now),
    }


def html_url(api_url: str | None) -> str | None:
    """Turn an api.github.com subject URL into the browser URL."""
    if not api_url:
        return None
    return api_url.replace(
        "https://api.github.com/repos/", "https://github.com/"
    ).replace("/pulls/", "/pull/")


def mentions(now: datetime) -> list[dict]:
    raw = json.loads(
        gh("api", "notifications", "--paginate", "-X", "GET", "-f", "all=false")
    )
    out = []
    for n in raw:
        if n.get("reason") not in {"mention", "team_mention"}:
            continue
        out.append(
            {
                "repo": n["repository"]["full_name"],
                "title": n["subject"]["title"],
                "type": n["subject"]["type"],
                "reason": n["reason"],
                "url": html_url(n["subject"].get("url")) or n["repository"]["html_url"],
                "idle_days": days_since(n.get("updated_at"), now),
            }
        )
    return out


def waiting_on_me(nodes: list[dict], login: str, now: datetime) -> list[dict]:
    """Threads where someone else spoke last — the ball may be in my court."""
    out = []
    for n in nodes:
        if not n:
            continue
        item = shape_pr(n, now) if "isDraft" in n else shape_issue(n, now)
        item["kind"] = "pr" if "isDraft" in n else "issue"
        lc = item["last_comment"]
        if lc and lc["by"] and lc["by"] != login and not lc["by"].endswith("[bot]"):
            out.append(item)
    return sorted(out, key=lambda i: i["last_comment"]["days_ago"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--limit", type=int, default=50, help="max results per search (default 50)"
    )
    parser.add_argument(
        "--waiting-days",
        type=int,
        default=180,
        help="only consider threads updated within this many days for waiting_on_me (default 180)",
    )
    args = parser.parse_args()

    login = gh("api", "user", "--jq", ".login").strip()
    now = datetime.now(UTC)
    since = (now - timedelta(days=args.waiting_days)).date().isoformat()
    data = {
        "mine": search(
            f"is:pr is:open archived:false author:{login}", PR_FIELDS, args.limit
        ),
        "review": search(
            f"is:pr is:open archived:false review-requested:{login}",
            PR_FIELDS,
            args.limit,
        ),
        "issues": search(
            f"is:issue is:open archived:false assignee:{login}",
            ISSUE_FIELDS,
            args.limit,
        ),
        "waiting": search(
            f"is:open archived:false involves:{login} -author:{login} "
            f"-assignee:{login} -review-requested:{login} updated:>={since} sort:updated-desc",
            PR_FIELDS + ISSUE_FIELDS,
            args.limit,
        ),
    }

    result = {
        "login": login,
        "generated_at": now.isoformat(timespec="seconds"),
        "my_prs": sorted(
            (shape_pr(n, now) for n in data["mine"]["nodes"] if n),
            key=lambda p: -p["idle_days"],
        ),
        "review_requests": sorted(
            (shape_pr(n, now) for n in data["review"]["nodes"] if n),
            key=lambda p: -p["age_days"],
        ),
        "assigned_issues": sorted(
            (shape_issue(n, now) for n in data["issues"]["nodes"] if n),
            key=lambda i: -i["idle_days"],
        ),
        "mentions": mentions(now),
        "waiting_on_me": waiting_on_me(data["waiting"]["nodes"], login, now),
        "truncated": {
            k: data[k]["issueCount"] > args.limit
            for k in ("mine", "review", "issues", "waiting")
        },
    }
    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
