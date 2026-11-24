# Milestone 2 demo: script and transcript

About 3 minutes. Every scene lists what should be on screen, what to click or type, and what to say. The quoted lines under "Say" are the transcript: if the recording follows them, this file covers the captions-or-transcript requirement.

---

## Setup, before you press record (about 5 minutes, not recorded)

**1. Wake the service.** In a browser, go to:

    https://se480-brittonpeterson-service.onrender.com/health

Wait until you see JSON starting with `{"status":"ok"`. That can take up to a minute if it was asleep. It sleeps again after about 15 idle minutes, so record within 10 minutes of this.

**2. Open these five browser tabs, in this order, left to right:**

| Tab | URL |
| --- | --- |
| 1 | `https://github.com/BrittonPeterson/se480-brittonpeterson-service` |
| 2 | `https://dashboard.render.com/web/srv-dbjphnnf3r2c73cpkveg/logs` |
| 3 | `https://se480-brittonpeterson-service.onrender.com/health` |
| 4 | `https://github.com/BrittonPeterson/se480-brittonpeterson-service/blob/main/docs/postmortem.md` |
| 5 | `https://github.com/BrittonPeterson/se480-brittonpeterson-service/blob/main/docs/milestone2.md` |

In tab 2, check that you're signed in to Render and the Logs page is showing. Leave the search box empty.

In tab 3, if Edge or Chrome shows a **Pretty-print** checkbox above the JSON, tick it.

**3. Open a terminal.** In Cursor, use **Terminal → New Terminal**, or open Windows Terminal. Then:

    cd C:\Users\pembr\Desktop\SE480Code
    cls

Make the font big: press **Ctrl + =** (Cursor) or **Ctrl + +** (Windows Terminal) three or four times. Close any panels so the terminal fills most of the screen.

**4. Start the recorder.** Use the Snipping Tool's video mode: press **Win + Shift + R**, drag a box around the whole screen, then click **Start**. A 3-second countdown runs. To stop, click the red **Stop** button in the Snipping Tool bar at the top of the screen. The video then opens in the Snipping Tool, and **Ctrl + S** saves it as an MP4.

Don't show the Render **Environment** page or any settings page during the recording.

---

## Scene 1: What it is (0:00 to 0:20)

**On screen:** browser tab 1, the repository's GitHub page, scrolled to the top so the repo name and the start of the README are visible.

**Do:**
1. Click tab 1.
2. Scroll down slowly about one screen so "Deployed at: https://se480-brittonpeterson-service.onrender.com" is visible, and stop there.

**Say:**
> This is Table Hold, a small API for reserving a table at a game store for a block of time. It's a FastAPI service, deployed on Render at the URL on screen. The failure that matters for this project is two groups both being told the same table is theirs.

---

## Scene 2: The journey working (0:20 to 1:05)

**On screen:** the terminal.

**Do:**
1. Switch to the terminal (**Alt + Tab**, or click it).
2. Type this and press **Enter**:

       .\.venv\Scripts\python.exe client\example.py https://se480-brittonpeterson-service.onrender.com

3. It finishes in about 2 seconds. Leave the output on screen and talk over it. Move the mouse to point at each block as you mention it.

**What you'll see** (dates and the reservation id will differ):

    Tables that seat four or more:
      tbl_7f3k9q2d  Table 4 (back room, seats 4)
      tbl_2c8v5n1p  Table 12 (front window, seats 8)

    Free stretches of two hours or more on Thu 26 Nov:
      09:00 to 22:00

    Holding tbl_7f3k9q2d from Thu 12:00 for two hours...
      Reserved. Reservation rsv_...; see /v1/reservations/rsv_...

    Trying the same window again, on purpose...
      Couldn't do that: The table is already held for part of that time
      Table 4 is held from 12:00 to 14:00 on Thu 26 Nov 2026 (America/Chicago). ...

    Cancelling the first one so the slot is free again...
      Cancelled (204).

**Say:**
> This is the sample client calling the deployed service. It lists the tables that seat four *(point at the two tables)*, then asks for Table 4's free stretches on a day two days from now *(point at "09:00 to 22:00")*. That openings operation is the one I added to move away from the course example. Then it holds the table from noon for two hours and gets a reservation id back *(point at "Reserved")*.
>
> Next it sends the same hold again, on purpose. The service says no with a 409 and names the window that's already taken, but not who took it *(point at "Couldn't do that")*. Last, it cancels the first hold so the slot is free again *(point at "Cancelled (204)")*.

---

## Scene 3: Seeing it from the outside (1:05 to 1:50)

### 3a. The request id (1:05 to 1:15)

**On screen:** the terminal.

**Do:**
1. Type `cls` and press **Enter** to clear the screen.
2. Type this and press **Enter**. It prints only the response headers:

       curl.exe -s -D - -o NUL https://se480-brittonpeterson-service.onrender.com/v1/tables

3. Find the line `x-request-id: ` followed by 16 letters and digits, for example `x-request-id: c871c63fe97e2e3a`.
4. Double-click the id to select it, then press **Ctrl + Shift + C** (Cursor or Windows Terminal) to copy it.

**Say:**
> Every response carries an X-Request-ID header. Here's this one.

### 3b. Finding it in Render's log (1:15 to 1:30)

**On screen:** browser tab 2, `dashboard.render.com/.../logs`.

**Do:**
1. Click tab 2.
2. Click the **Search** box at the top of the logs, next to the "Application logs" button.
3. Press **Ctrl + V** to paste the id, then press **Enter**.
4. Wait a few seconds for one line to appear. If it doesn't, press **Enter** again. Logs can take about 10 seconds to arrive.
5. Hover the mouse over the line.

**What you'll see:** one line like

    {"ts":"2026-11-24T22:22:10.123Z","level":"INFO","request_id":"c871c63fe97e2e3a","method":"GET","route":"/v1/tables","status":200,"duration_ms":1.2}

**Say:**
> In Render's log, that id finds exactly one line. Each request writes one JSON line with the method, the route template, the status, and the duration. The route is the template, never the real path, so reservation ids and names don't end up in the log.

### 3c. Health (1:30 to 1:40)

**On screen:** browser tab 3, `https://se480-brittonpeterson-service.onrender.com/health`.

**Do:**
1. Click tab 3.
2. Press **F5** to refresh, so the numbers are current.
3. Point at `started_at`, then `commit`, then `store`.

**What you'll see:**

    {"status":"ok","started_at":"...","uptime_seconds":...,"commit":"<latest commit on main>","store":{"tables":2,"reservations":...,"confirmed":...}}

**Say:**
> Health reports when this instance started, which commit is deployed, and how many holds are in memory. That's what the proposal promised for this milestone.

### 3d. Metrics (1:40 to 1:50)

**On screen:** the same tab, at `/metrics`.

**Do:**
1. Click the address bar (or press **Ctrl + L**), type this, and press **Enter**:

       https://se480-brittonpeterson-service.onrender.com/metrics

2. Press **Ctrl + F** and type `http_requests_total{`. Point at one of the lines, for example `http_requests_total{route="/v1/tables",status="2xx"}`.
3. Clear the find box and type `table_conflicts_total`. Press **Enter** until the highlight lands on the line that starts `table_conflicts_total ` followed by a number, not the `# HELP` line.
4. Press **Esc** to close the find box.

**Say:**
> Metrics counts requests by route and status class, keeps a duration histogram, and has one counter from the service's own rules: holds refused because the table was already taken.

---

## Scene 4: The failure that matters (1:50 to 2:40)

### 4a. The race (1:50 to 2:15)

**On screen:** the terminal.

**Do:**
1. Switch to the terminal. Type `cls` and press **Enter**.
2. Type this and press **Enter**:

       .\.venv\Scripts\python.exe scripts\double_hold.py https://se480-brittonpeterson-service.onrender.com 20

3. It takes about 5 seconds and prints 20 rows. Most rows read `[201, 409]`. Scroll up if needed and look for a row ending in `DOUBLE BOOKED`.
4. Point at the summary line near the bottom: "N of 20 pairs were both given the table."

**Say**, if no row says DOUBLE BOOKED (this is the likely case):
> This script sends twenty pairs of identical holds at the same instant. Every pair this time got one 201 and one 409, which is correct. But when I ran it yesterday, one pair got two 201s: two groups, one table. It depends on timing, which is what makes it dangerous. There's also a test that reproduces it every time, and it's marked as an expected failure.

**Say**, if a row does say DOUBLE BOOKED:
> This script sends twenty pairs of identical holds at the same instant. Most pairs got one 201 and one 409, which is correct. But this one *(point at the row)* got two 201s: two groups, one table. It depends on timing, which is what makes it dangerous. There's also a test that reproduces it every time, and it's marked as an expected failure.

### 4b. The postmortem (2:15 to 2:40)

**On screen:** browser tab 4, `github.com/.../docs/postmortem.md`.

**Do:**
1. Click tab 4.
2. Pause on the **Summary** section for a couple of seconds.
3. Scroll down to **Detection** and point at "Nothing in the service noticed."
4. Scroll down past the Timeline to **Contributing factors** and point at the first bullet, the one about the check and the write being two separate steps.

**Say:**
> The postmortem is blameless, and its main point is that nothing in the service noticed *(at Detection)*. Both requests were logged as normal successes, and health said ok. The cause is that the service checks for an overlap and then saves, with nothing holding the table in between *(at Contributing factors)*.

---

## Scene 5: What shipped and what's next (2:40 to 3:00)

**On screen:** browser tab 5, `github.com/.../docs/milestone2.md`.

**Do:**
1. Click tab 5.
2. Point at the **What shipped, against the proposal** list.
3. Scroll to **What is next for the final** and point at it.
4. Stop speaking, wait one second, then stop the recording.

**Say:**
> Everything the proposal put in Milestone 2 shipped: all eight operations deployed, structured logs, and a health check that reports the store. Next, for the final, is deciding how the check and the save become one step, making that test pass, and moving to a store that survives restarts. Thanks for watching.

---

## After recording

1. Watch it once. Check that the terminal text is readable and the length is close to 3 minutes. If it runs long, talk a little faster in scenes 2 and 4. Don't cut scenes.
2. Upload it somewhere the instructor can open: YouTube set to **Unlisted**, or OneDrive or Google Drive set to **Anyone with the link can view**.
3. Send me the link. It goes on the "Demo video" line of `docs/milestone2.md`, and this file is already linked there as the transcript.
