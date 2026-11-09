# Table Hold — design sheet

A player who wants a table at their game store tonight needs to see which tables are free and hold one for a session. It does that by listing tables and creating a reservation for a block of time. It goes wrong when two groups are both told the same table is theirs.

## 1. Name and purpose

Table Hold: find an open table in one game store and hold it for a session, without giving that table to two groups.

## 2. Users

- Primary: a player booking from their phone before they head to the store.
- Overlooked: the group that already holds the table. They never call the API, and a wrong answer costs them the seat.

## 3. Resources

`tables`. Identifier `table_id`, an opaque string such as `tbl_7f3k9q2d`. Seeded by the store and read-only in v1.

| Field | Type | Required |
| --- | --- | --- |
| name | string | yes |
| seats | integer, 1 or more | yes |
| zone | string, for example "back room" | yes |
| game_tags | array of enum: board_game, card_game, miniature, roleplaying, puzzle | yes, may be empty |
| wheelchair_accessible | boolean | yes |
| time_zone | IANA name, for example America/Chicago | yes |
| open_hours | array of {weekday, opens, closes}; opens and closes are local HH:MM | yes |

A weekday missing from `open_hours` is closed. An unknown `game_tags` value is unsupported, not an error, so new tags can be added inside v1.

`reservations`. Identifier `reservation_id`, an opaque string such as `rsv_8s2k1m0v4q7x3n9bw5zc`. Not a counter.

| Field | Type | Required on create |
| --- | --- | --- |
| table_id | string, taken from the path | no |
| starts_at | RFC 3339 date-time with an offset | yes |
| ends_at | RFC 3339 date-time with an offset | yes |
| title | string, 120 characters or fewer | no |
| requester.display_name | string, 1 to 200 characters, one field, any script | yes |
| requester.email | email | yes |
| player_count | integer, 1 to the table's seats | no |
| status | enum: confirmed, cancelled | read-only |
| created_at | RFC 3339 date-time with an offset | read-only |

Rules on the window: `ends_at` is after `starts_at`, the length is 1 to 6 hours, the window is inside open hours, and the start is not in the past and at most 14 days ahead. A patch that keeps the old start skips the past check, so a session already under way can be retitled. A time with no offset is rejected. Cancelled reservations stay, with status `cancelled`.

## 4. Operations

Paths in `openapi.yaml` omit `/v1` because the version is the server URL. Clients of the deployed service call `/v1/...`.

| Method | Path in the spec | Purpose | Success |
| --- | --- | --- | --- |
| GET | /tables | List tables. Filter by seats_min, game_tag, and wheelchair_accessible. | 200 |
| GET | /tables/{table_id} | One table, with its tags and open hours. | 200 |
| GET | /tables/{table_id}/openings | Free stretches on one local day: open hours minus confirmed holds. Required date, optional min_length_minutes. | 200 |
| GET | /tables/{table_id}/reservations | Reservations on that table. Optional window_start and window_end. | 200 |
| POST | /tables/{table_id}/reservations | Hold the table. The rules and the overlap check run here. | 201 and a Location header |
| GET | /reservations/{reservation_id} | One reservation, including cancelled ones. | 200 |
| PATCH | /reservations/{reservation_id} | Move or retitle. The same rules and overlap check, ignoring this reservation. | 200 |
| DELETE | /reservations/{reservation_id} | Cancel. Cancelling again returns 204. An unknown id returns 404. | 204 |

Not in v1, on purpose: accounts, payments, inventory, and store admin.

## 5. Error model

Every error is a problem-details document: `type`, `title`, `status`, `detail`, `instance`.

- 400 validation-failed. A field is missing, malformed, or breaks a rule. `errors` lists each field.
- 404 not-found. No table or reservation with that id.
- 409 table-conflict. A confirmed reservation already overlaps the window. `conflicts_with` gives the window and never the other group's name.

A request that breaks a rule is 400. A request that is valid and collides with the table's state is 409.

## 6. Versioning

`/v1` is the base URL (`https://se480-brittonpeterson-service.onrender.com/v1`). Within v1, nothing a working client depends on changes: no field or operation removed or renamed, no status code changed, no new required field, and problem type URLs keep their meaning. New optional fields, filters, operations, and `game_tags` values ship inside v1. Removing, renaming, or changing a meaning forces `/v2`, which runs beside v1 for at least six months.

## 7. Risk mark

| Operation | Wrong answer | Who is hurt |
| --- | --- | --- |
| POST /tables/{table_id}/reservations | A 201 for a window that overlaps a confirmed reservation | Both groups, and the first one most: they did nothing wrong and find another group at the table |
| DELETE /reservations/{reservation_id} | Cancelling a reservation the caller does not hold. v1 has no login, so the id is the only key | The group that loses the table with no notice |
| GET /tables/{table_id}/reservations | A window that omits a reservation, or shows it in the wrong offset | The walk-in who trusted a free-looking table |
| GET /tables/{table_id}/openings | A stretch offered as free that a confirmed hold covers | The player who plans a night around it, then gets a 409 or, through the race, a double booking |

Seeded failure: two creates a few hundred milliseconds apart. Each check sees no overlap, and both return 201. Nothing in the logs is an error. The failure shows up when both groups arrive for the same table.
