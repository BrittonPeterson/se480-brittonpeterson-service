# Milestone 2 demo: transcript

Hi, I'm Britton Peterson, and this is my Milestone 2 demo for SE 480. My project is called Table Hold. It's a small web API that lets a player reserve a table at a game store for a block of time, like two hours on Thursday afternoon. It's written in Python with FastAPI, and it's deployed on Render at the URL you can see here. The failure that matters most for this project is two groups both being told the same table is theirs, and I'll show that at the end.

First, the normal journey. This is my sample client, and it's calling the live service on Render, not my laptop.

It starts by asking for tables that seat four or more, and the store has two: Table 4 in the back room and Table 12 by the front window.

Next it asks when Table 4 is free on a day two days from now. That's the openings operation. It isn't in the course example; I added it after feedback that my service was too close to the example. Right now the whole day is open, nine to ten.

Then it holds Table 4 from noon to two, and the service answers with a 201 and a reservation id.

Then it sends the exact same request again, on purpose. This time the service refuses with a 409 conflict. It says Table 4 is already held from twelve to two and suggests another time or another table. It doesn't say who holds it, so one player's details never leak to another.

Finally it cancels the first hold, so the table is free again.

Now, what an operator sees. Every response from the service comes back with a request id in the X-Request-ID header. Here's the one for the request I just sent. I'll copy it.

This is Render's log for the service. When I search for that request id, I get exactly one line, the one for my request. Every request writes one line of JSON with a timestamp, the request id, the method, the route, the status code, and how long it took in milliseconds. The route is the template, slash v1 slash tables, never the actual path. So reservation ids, names, and email addresses never end up in the log.

This is the health endpoint, which Render also checks to see if the service is up. It reports when this instance started, which git commit is deployed, so I can tell exactly what code is running, and how many reservations are in memory. That reservation count is what my proposal promised for this milestone.

And this is the metrics endpoint. It counts requests by route and by status class, 2xx, 4xx, or 5xx, and keeps a histogram of how long requests take. It also has one counter that comes from my own business rule: table conflicts total, the number of holds refused because the table was already taken.

Now the failure that matters. This script sends twenty pairs of identical holds, and both requests in each pair go out at the same instant. Each pair should get one 201 and one 409, and this time every pair did. But when I ran this yesterday against the same deployed service, one pair got two 201s: two groups, both told they have the same table. It depends on timing, which is exactly what makes it dangerous. I also wrote a test that reproduces it every single time. It's marked as an expected failure until I fix it.

I wrote this up as a blameless postmortem. The summary: two requests for the same table and the same two hours both got confirmed. The most important finding is that nothing in the service noticed. Both requests were logged as normal successes, health said ok the whole time, and no alert fired. In real life, the first sign would have been two groups showing up at the same table. The cause is that the service checks for an overlap and then saves the reservation as two separate steps, with nothing holding the table in between. So two requests can both pass the check before either one is saved.

To wrap up: everything my proposal put in Milestone 2 shipped. All eight operations are deployed, the logs are structured, and the health check reports what's in the store. For the final, I'll decide how the check and the save become a single step so double booking can't happen, make that failing test pass, and move to a store that keeps reservations across restarts. Thanks for watching.
