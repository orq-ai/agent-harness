"""CI-failure triage workflow.

Given a repo, finds recent failed GitHub Actions runs and has an agent
investigate the most recent one, then posts a concise cause summary to Slack.

Run on demand:
  POST /workflows/runs
  {"workflow_name": "ci_triage", "input": {"repo": "orquesta-web"}, "eager_start": true}
"""

from dataclasses import dataclass


WORKFLOW_NAME = "ci_triage"


@dataclass
class Input:
    repo: str
    channel: str = "eng-ci"
    max_runs: int = 5


async def handler(inp: Input, ctx):
    runs = await ctx.call_tool(
        "github", "list_failed_workflow_runs", {"repo": inp.repo, "limit": inp.max_runs}
    )
    if not runs:
        return {"status": "no_failures", "repo": inp.repo}

    latest = runs[0]
    prompt = (
        f"A GitHub Actions run failed on {inp.repo}.\n\n"
        f"Failed run: {latest}\n\n"
        "Investigate the likely cause. Use the `github` tool — inspect the "
        "run's jobs (`workflow_run_jobs`) to see which step failed, the commit "
        "that triggered it, and recent related changes (`search_code`, "
        "`list_pull_requests`). Then write a Slack message with: what failed, "
        "the most likely cause, and one suggested next step. Keep it under 12 lines."
    )
    result = await ctx.agent_turn(prompt)
    await ctx.post_to_slack(inp.channel, result["result_text"])
    return {"status": "triaged", "run": latest, "summary": result["result_text"]}
