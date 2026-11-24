# Milestone 2 status: Table Hold

- **Deployed at:** https://se480-brittonpeterson-service.onrender.com
- **Demo video:** https://drive.google.com/file/d/1g16J17unAUxJT_AtcAefqn0tQU42ktoT/view?usp=sharing
## What shipped, against the proposal

- **The eight operations in `openapi.yaml` v1, deployed.** These are list tables, get a table, a day's openings, a table's holds, create a hold, and get, move, or cancel a hold. Try `GET /v1/tables` on the deployed URL, or read `/docs`. The contract and drift tests in `tests/` check the code against the spec on every push.
- **`client/example.py` lists, holds, and shows a conflict.** Run `python client/example.py https://se480-brittonpeterson-service.onrender.com`.
- **Structured logs.** One JSON line per request, with a request id, the route template, the status, and the duration. See the README's "Operate it" section.
- **A `/health` body that reports what is in memory.** It shows tables, reservations, and confirmed holds, plus `started_at`, uptime, and the deployed commit.

## What did not, and why

- Nothing the proposal put in Milestone 2 is missing.
- The double booking still happens. That is on purpose: the proposal puts preventing it in the final. It now has a reproduction (`tests/test_concurrency.py`, `scripts/double_hold.py`) and a postmortem (`docs/postmortem.md`).

## What changed from the proposal

The service also gained things the proposal didn't ask for. `/metrics` has request counts, a duration histogram, and `table_conflicts_total`. There's an SLO in `docs/slo.md`, a 500 handler that hands back a request id, and the Lab 4 checks (ruff, a coverage floor of 85, and pip-audit in CI). None of them changes the API. The scope in `docs/proposal.md` is unchanged.

## What is next for the final

- The action items in `docs/postmortem.md`: decide in Week 6 how the overlap check and the write become one step, then make `tests/test_concurrency.py` pass and remove its `xfail`.
- A durable store, so holds survive Render's restarts.
- Count overlapping confirmed holds in `/metrics`. The count should always read zero.
- The safety case around the fix, due Fri Dec 4.
