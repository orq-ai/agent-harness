"""GitHub tool for the orq-ai Centaur overlay.

Read-mostly access to orq-ai repositories: pull requests, CI runs, and code
search. Centaur exposes every public method of the ``_client()`` instance at
``POST /tools/github/{method}``.
"""

from __future__ import annotations

import os
from typing import Any

try:  # provided by the Centaur runtime; iron-proxy injects the real token
    from centaur_sdk.tool_sdk import secret
except ImportError:  # tests and CI run without the Centaur runtime
    def secret(name: str, default: str = "") -> str:
        return os.environ.get(name, default)

GITHUB_API = "https://api.github.com"
DEFAULT_OWNER = "orq-ai"


def _repo_slug(repo: str) -> str:
    """Accept either ``name`` (assumed under orq-ai) or ``owner/name``."""
    repo = repo.strip().strip("/")
    return repo if "/" in repo else f"{DEFAULT_OWNER}/{repo}"


def _pr_summary(pr: dict) -> dict:
    return {
        "number": pr.get("number"),
        "title": pr.get("title"),
        "state": pr.get("state"),
        "author": (pr.get("user") or {}).get("login"),
        "draft": pr.get("draft", False),
        "head": (pr.get("head") or {}).get("ref"),
        "base": (pr.get("base") or {}).get("ref"),
        "url": pr.get("html_url"),
    }


def _run_summary(run: dict) -> dict:
    return {
        "id": run.get("id"),
        "name": run.get("name"),
        "branch": run.get("head_branch"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "commit": (run.get("head_commit") or {}).get("message", "").split("\n")[0],
        "url": run.get("html_url"),
    }


class GitHubClient:
    """GitHub access scoped to the orq-ai organization."""

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        import httpx

        headers = {
            "Authorization": f"Bearer {secret('GITHUB_TOKEN', '')}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        response = httpx.request(
            method, f"{GITHUB_API}{path}", headers=headers, timeout=30, **kwargs
        )
        response.raise_for_status()
        return response.json()

    def list_pull_requests(self, repo: str, state: str = "open", limit: int = 20) -> list[dict]:
        """List pull requests for a repo. ``state`` is open, closed, or all."""
        data = self._request(
            "GET",
            f"/repos/{_repo_slug(repo)}/pulls",
            params={"state": state, "per_page": min(limit, 100)},
        )
        return [_pr_summary(pr) for pr in data[:limit]]

    def get_pull_request(self, repo: str, number: int) -> dict:
        """Get one pull request with detail."""
        return _pr_summary(
            self._request("GET", f"/repos/{_repo_slug(repo)}/pulls/{number}")
        )

    def pull_request_checks(self, repo: str, number: int) -> dict:
        """CI / check-run status for a pull request's head commit."""
        slug = _repo_slug(repo)
        pr = self._request("GET", f"/repos/{slug}/pulls/{number}")
        sha = pr["head"]["sha"]
        checks = self._request("GET", f"/repos/{slug}/commits/{sha}/check-runs")
        runs = [
            {"name": c.get("name"), "status": c.get("status"), "conclusion": c.get("conclusion")}
            for c in checks.get("check_runs", [])
        ]
        failing = [r for r in runs if r["conclusion"] in ("failure", "timed_out", "cancelled")]
        return {"sha": sha, "total": len(runs), "failing": failing, "check_runs": runs}

    def list_failed_workflow_runs(self, repo: str, limit: int = 10) -> list[dict]:
        """Recent failed GitHub Actions runs for a repo."""
        data = self._request(
            "GET",
            f"/repos/{_repo_slug(repo)}/actions/runs",
            params={"status": "failure", "per_page": min(limit, 100)},
        )
        return [_run_summary(r) for r in data.get("workflow_runs", [])[:limit]]

    def workflow_run_jobs(self, repo: str, run_id: int) -> list[dict]:
        """Per-job status for one GitHub Actions run (which step failed)."""
        data = self._request(
            "GET", f"/repos/{_repo_slug(repo)}/actions/runs/{run_id}/jobs"
        )
        return [
            {
                "name": job.get("name"),
                "conclusion": job.get("conclusion"),
                "failed_steps": [
                    s.get("name")
                    for s in job.get("steps", [])
                    if s.get("conclusion") in ("failure", "timed_out")
                ],
            }
            for job in data.get("jobs", [])
        ]

    def search_code(self, query: str, repo: str | None = None, limit: int = 20) -> list[dict]:
        """Search code across orq-ai, optionally scoped to one repo."""
        scope = f"repo:{_repo_slug(repo)}" if repo else f"org:{DEFAULT_OWNER}"
        data = self._request(
            "GET",
            "/search/code",
            params={"q": f"{query} {scope}", "per_page": min(limit, 100)},
        )
        return [
            {"repo": i["repository"]["full_name"], "path": i["path"], "url": i["html_url"]}
            for i in data.get("items", [])[:limit]
        ]


def _client() -> GitHubClient:
    return GitHubClient()
