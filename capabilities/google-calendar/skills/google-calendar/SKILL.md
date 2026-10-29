---
name: google-calendar
description: Use when the user asks about their Google Calendar — schedule, agenda, availability, meetings, events, 日程, 日历, 行程, 会议, 有空吗 — including viewing, searching, creating, changing, or deleting events.
---

# Google Calendar

You read and edit the user's Google Calendar by calling the Google Calendar REST API
(`https://www.googleapis.com/calendar/v3`) with `curl` in Bash.

## Credential

The connected Google account is available as the environment variable `GOOGLE_OAUTH`.
Its value is a placeholder, not a real token: the platform swaps in the real access token
when an HTTPS request leaves for a Google API host, and refreshes it when it expires.
Always send it as a bearer header, and never print, echo, or log it.

```bash
AUTH="Authorization: Bearer $GOOGLE_OAUTH"
API=https://www.googleapis.com/calendar/v3
```

Before the first call in a conversation, check that it is set:

```bash
test -n "$GOOGLE_OAUTH" && echo connected || echo "not connected"
```

If it prints `not connected`, stop and tell the user to connect their Google account on
this capability's card. Do not retry calls.

## Time zone

Read the user's time zone from their primary calendar and use it for every time you show
or send. Do not assume one.

```bash
curl -sS -H "$AUTH" "$API/users/me/calendarList/primary" | jq -r .timeZone
```

Send times as RFC 3339 with an offset (`2026-11-03T15:00:00+08:00`). For all-day events
use `{"date": "YYYY-MM-DD"}` instead of `dateTime`; the end date is exclusive.

## Reading — do these directly, no confirmation needed

List calendars:

```bash
curl -sS -H "$AUTH" "$API/users/me/calendarList?maxResults=100" \
  | jq '[.items[] | {id, summary, primary, accessRole, timeZone}]'
```

List events in a range (expand recurring events, sorted by start):

```bash
curl -sS -G -H "$AUTH" "$API/calendars/primary/events" \
  --data-urlencode "timeMin=2026-11-03T00:00:00+08:00" \
  --data-urlencode "timeMax=2026-11-10T00:00:00+08:00" \
  --data-urlencode "singleEvents=true" \
  --data-urlencode "orderBy=startTime" \
  --data-urlencode "maxResults=50" \
  | jq '[.items[] | {id, summary, start, end, location, status, attendees: [.attendees[]?.email]}]'
```

Search events by text: add `--data-urlencode "q=<words>"` to the call above. Keep a time
range unless the user asks for all time.

Get one event:

```bash
curl -sS -H "$AUTH" "$API/calendars/primary/events/<eventId>"
```

To check availability, list the events in the range and report the gaps.

Use a calendar's `id` from the calendar list in place of `primary` to work with another
calendar. `primary` is the default unless the user names another calendar. Calendar IDs
can contain `#` and `@`, so URL-encode them before putting them in the path:

```bash
CAL=$(jq -rn --arg id "<calendarId>" '$id|@uri')
curl -sS -H "$AUTH" "$API/calendars/$CAL/events?maxResults=10"
```

## Writing — confirm first

Before creating, changing, or responding to an event, show the user what you will send —
title, start and end with time zone, calendar, attendees, location — and wait for a clear
yes. Before deleting, show the full event, say plainly that it will be deleted, and wait
for a clear yes. Never write in the same turn you first propose the change.

Inviting attendees sends them email from the user's account. Add attendees only when the
user asks, and add `sendUpdates=all` only when the user wants invitations or updates sent.

Create:

```bash
curl -sS -X POST -H "$AUTH" -H "Content-Type: application/json" \
  "$API/calendars/primary/events" \
  -d '{"summary":"Design review","start":{"dateTime":"2026-11-03T15:00:00+08:00"},"end":{"dateTime":"2026-11-03T16:00:00+08:00"}}'
```

Update only the fields that change:

```bash
curl -sS -X PATCH -H "$AUTH" -H "Content-Type: application/json" \
  "$API/calendars/primary/events/<eventId>" \
  -d '{"location":"Room 3"}'
```

Delete (a successful delete returns an empty body with HTTP 204):

```bash
curl -sS -o /dev/null -w '%{http_code}\n' -X DELETE -H "$AUTH" \
  "$API/calendars/primary/events/<eventId>"
```

Respond to an invitation: get the event, set `responseStatus` (`accepted`, `declined`,
`tentative`) on the attendee whose `self` is `true`, and PATCH the full `attendees` array
back.

For a recurring event, the IDs returned with `singleEvents=true` are single occurrences.
Ask whether the user means this occurrence or the whole series; the series ID is the
occurrence's `recurringEventId`.

After a write, report what changed and include the event's `htmlLink`.

## Errors

Check the HTTP status (`curl -w '%{http_code}'`) or the `error` object in the response.

- `401` — the connection has expired or was revoked. Ask the user to reconnect Google on
  this capability's card. Do not retry.
- `403` with `insufficientPermissions` or `ACCESS_TOKEN_SCOPE_INSUFFICIENT` — the user
  did not grant calendar access when connecting. Ask them to reconnect and allow calendar
  access.
- `403` with `requiredAccessLevel` — the user can read but not edit that calendar
  (`accessRole` is `reader` or `freeBusyReader`). Say so.
- `404` — the event or calendar does not exist. A deleted event may instead still be
  returned with `"status": "cancelled"`; treat that as deleted.
- `429` or `5xx` — wait a few seconds and retry once, then report the failure.

## Showing results

- Group events by day, in the user's time zone.
- For each event: time range, title, location if any.
- Leave out cancelled events unless the user asks.
- Keep descriptions and attendee lists short unless the user asks for detail.
