from tools.github.client import GitHubClient, _pr_summary, _repo_slug, _run_summary


def test_repo_slug_defaults_to_orq_ai():
    assert _repo_slug("orquesta-web") == "orq-ai/orquesta-web"
    assert _repo_slug("orq-ai/orquesta-web") == "orq-ai/orquesta-web"
    assert _repo_slug("  /paradigmxyz/centaur  ") == "paradigmxyz/centaur"


def test_pr_summary_extracts_fields():
    summary = _pr_summary(
        {
            "number": 7,
            "title": "Fix router",
            "state": "open",
            "user": {"login": "tony"},
            "draft": False,
            "head": {"ref": "fix"},
            "base": {"ref": "main"},
            "html_url": "https://github.com/orq-ai/x/pull/7",
        }
    )
    assert summary["number"] == 7
    assert summary["author"] == "tony"
    assert summary["base"] == "main"


def test_run_summary_keeps_first_commit_line():
    summary = _run_summary(
        {"id": 1, "head_commit": {"message": "fix: thing\n\ndetails"}, "conclusion": "failure"}
    )
    assert summary["commit"] == "fix: thing"
    assert summary["conclusion"] == "failure"


def test_list_pull_requests_uses_repo_slug(monkeypatch):
    calls = []
    client = GitHubClient()

    def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return [
            {
                "number": 1,
                "title": "t",
                "state": "open",
                "user": {"login": "a"},
                "head": {"ref": "h"},
                "base": {"ref": "main"},
                "html_url": "u",
            }
        ]

    monkeypatch.setattr(client, "_request", fake_request)
    result = client.list_pull_requests("orquesta-web")

    assert calls[0][1] == "/repos/orq-ai/orquesta-web/pulls"
    assert result[0]["number"] == 1
