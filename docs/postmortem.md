# Postmortem: one table, two confirmed holds

This incident was caused on purpose, in Lab 5 task 6, against the deployed service. No real player was affected. The holds were made by a script and cancelled by the same script. Everything below is written as if they had been real, because the service could not tell the difference.

- **Written:** Monday Nov 23, 2026
- **Author:** Britton Peterson
- **Reproduction:** `tests/test_concurrency.py`, a strict expected failure, every time. `scripts/double_hold.py` reproduces it over real HTTP, some of the time.

## Summary

Two requests asked for Table `tbl_7f3k9q2d` from 09:00 to 11:00 on Wed Nov 25 at the same moment, and both were answered 201 with a confirmed hold. In real use, two groups would each have a confirmation for the same table and would find out at the store.

## Impact

One table, one two-hour window, two groups. In the run against Render, 1 of 20 simultaneous pairs got two 201s and the other 19 were handled correctly, with one 201 and one 409. Locally the same script double-booked 0 of 20 pairs. The window between the check and the write is microseconds in an in-memory dict, so how often it happens depends on timing the service doesn't control. Any create or move that arrives while another for the same table and window is being handled is exposed. The service cannot say how many times it has already happened.

## Detection

It was found by a script that looked for it. Nothing in the service noticed. Both requests were logged at level INFO with status 201. `/health` said `ok` throughout. `table_conflicts_total` moved by 19, not 20, but nothing compares that number with anything. Render's notifications only cover deploys and failed health checks, and the service was healthy. Without the script, the first signal would have been a group at the table holding a confirmation for a table someone else is already sitting at.

## Timeline

All times Nov 23, 2026, UTC. The holds were for Nov 24 and 25.

| When | What was seen, said or decided |
| --- | --- |
| 18:34:01 | Commit `cca76c6` starts on Render (`started_at` in `/health`). |
| 18:35:17 | `scripts/double_hold.py` starts. `/health` reports 60 reservations, all cancelled. |
| 18:35:18 | Twelve pairs for Nov 24 each get one 201 and one 409, as designed. |
| 18:35:19 | The pair for Nov 25 09:00 gets two 201s, request ids `8632340d2df162c0` and `13cff083a76a3600`. |
| 18:35:20 | Seven more pairs get one 201 and one 409. `/health` reports 81 reservations, 21 confirmed. There should have been 20. |
| 18:35:20 | The script cancels all 21 holds it created. |
| Later | Decision: no fix in Lab 5. The failure is recorded in Known limits, and the fix goes to the Week 6 store decision. |

The times come from `/health`'s `uptime_seconds` (76 before the run, 79 after) added to `started_at`.

## Contributing factors

- The overlap check (`rules.find_conflict`) and the write to the store are two separate steps with nothing holding the table in between. Two requests can both pass the check before either one is stored.
- The store accepts whatever reservation it is given. The no-overlap rule only lives in the check that runs before the write, so the store can't refuse a second hold.
- Nothing counts overlapping confirmed holds. Once the service was in the state it promised never to be in, no signal showed it.
- The unit and contract tests send requests one at a time, which is the one situation where the check always works. Before Lab 5, no test ran two creates at once.
- uvicorn runs requests on a thread pool, so two requests to a plain `def` route really do run at the same time, even in one process.

## What went well, and where we got lucky

- The proposal and the README's Known limits already named this exact failure, so it took minutes to explain, not hours.
- The script printed the request ids from task 1 for both 201s, so the two lines in Render's log can be found by id, and the route template puts them on the same operation. Before Lab 5 they would have looked like any other pair of 201s.
- The table's own reservation list shows both holds, so the evidence is one GET away.
- Lucky: the race window is tiny today. It will get wider when the store does real I/O, which is planned for Week 6, so how rarely it happens now says nothing about how often it will happen later.
- Lucky: no one was standing at the table.

## What the service would have shown

Tasks 1 and 2 give each request an id and a duration, so the two creates can be found and shown to overlap in time. Task 3's `/health` shows one more confirmed hold than refusals and creates would explain, if someone did the arithmetic. Task 4's `table_conflicts_total` moved by one less than the number of duplicate pairs, but only because the script knew how many pairs it sent. In production, nobody knows how many there should have been. None of the four tasks would have warned anyone before the groups met at the table. Every signal they add reports what the service believes, and the service believed both holds were fine.

## Action items

| Action | Owner | Date | Home |
| --- | --- | --- | --- |
| Reproduce the failure on demand, as a test that is expected to fail | Britton Peterson | Sun Nov 22, 2026 (done in Lab 5) | `tests/test_concurrency.py` |
| Decide how the check and the write become one step (a lock, or a store that refuses overlaps), and record the decision | Britton Peterson | Week 6 | A decision record in `docs/` |
| Make `tests/test_concurrency.py` pass, and remove its `xfail` | Britton Peterson | Fri Dec 4, 2026 | The final |
| Count overlapping confirmed holds and report the count in `/metrics`. It should always read zero | Britton Peterson | Fri Dec 4, 2026 | The final |
| Until then, keep the failure in the README's Known limits with a link to this page | Britton Peterson | Mon Nov 23, 2026 (done) | Known limits |
