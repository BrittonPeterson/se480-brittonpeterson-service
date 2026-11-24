# Milestone 2 demo: script and transcript

About 3 minutes at a normal speaking pace (roughly 420 words). Record against the deployed service. If the recording follows these words, this file is the transcript.

**Before you hit record:**

- Wake the service: open https://se480-brittonpeterson-service.onrender.com/health and wait for the JSON.
- Have three things open: a terminal in the repo with the venv active, a browser tab on the Render Logs page for the service, and a browser tab on `docs/postmortem.md` on GitHub.
- Make the terminal font large.

---

## 1. What it is (0:00 to 0:20)

**Show:** the README on GitHub, top of the page.

> This is Table Hold, a small API for reserving a table at a game store for a block of time. It's a FastAPI service, deployed on Render at the URL on screen. The failure that matters for this project is two groups both being told the same table is theirs.

## 2. The journey working (0:20 to 1:05)

**Run:**

    python client/example.py https://se480-brittonpeterson-service.onrender.com

> This is the sample client calling the deployed service. It lists the tables that seat four, then asks for Table 4's free stretches on a day two days from now. That openings operation is the one I added to move away from the course example. Then it holds the table from noon for two hours and gets a reservation id back.
>
> Next it sends the same hold again, on purpose. The service says no with a 409 and names the window that's already taken, but not who took it. Last, it cancels the first hold so the slot is free again.

## 3. Seeing it from the outside (1:05 to 1:50)

**Run:**

    curl.exe -si https://se480-brittonpeterson-service.onrender.com/v1/tables

> Every response carries an X-Request-ID header. Here's this one.

**Copy the id. Switch to the Render Logs tab, paste the id into the search box.**

> In Render's log, that id finds exactly one line. Each request writes one JSON line with the method, the route template, the status, and the duration. The route is the template, never the real path, so reservation ids and names don't end up in the log.

**Open** https://se480-brittonpeterson-service.onrender.com/health

> Health reports when this instance started, which commit is deployed, and how many holds are in memory. That's what the proposal promised for this milestone.

**Open** https://se480-brittonpeterson-service.onrender.com/metrics **and scroll to `table_conflicts_total`.**

> Metrics counts requests by route and status class, keeps a duration histogram, and has one counter from the service's own rules: holds refused because the table was already taken.

## 4. The failure that matters (1:50 to 2:40)

**Run:**

    python scripts/double_hold.py https://se480-brittonpeterson-service.onrender.com 20

> This script sends twenty pairs of identical holds at the same instant. Most pairs get one 201 and one 409, which is correct. When I ran it yesterday, one pair got two 201s: two groups, one table. It may or may not happen on this run, because it depends on timing. There's also a test that reproduces it every time, and it's marked as an expected failure.

**Switch to the `docs/postmortem.md` tab.**

> The cause is that the service checks for an overlap and then saves, with nothing holding the table in between. The postmortem is blameless, and its main point is that nothing in the service noticed. Both requests were logged as normal successes, and health said ok.

## 5. What shipped and what's next (2:40 to 3:00)

**Show:** `docs/milestone2.md`.

> Everything the proposal put in Milestone 2 shipped: all eight operations deployed, structured logs, and a health check that reports the store. Next, for the final, is deciding how the check and the save become one step, making that test pass, and moving to a store that survives restarts. Thanks for watching.
