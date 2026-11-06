---
name: daily-headsup
description: >-
  Vince's morning headsup: a prioritized brief of what needs attention today,
  pulled from Notion (pages, initiative rows and meeting notes he touched that
  look unfinished), GitHub (his open PRs, review requests, assigned issues,
  @mentions, threads waiting on his reply — anything rotting), Google Calendar
  (meetings that need prep, unanswered invites, conflicts) and Gmail (threads
  waiting on him). Leads with the top 3 pressing things, then a full ledger of
  everything he has in flight. Keeps that ledger in a private Notion page of its
  own between runs, so it can say what's new, what got done and what hasn't
  moved, and proposes Notion status updates for him to approve. Use this
  whenever the user asks what's on their plate, what they have in flight, what
  to work on today, for a morning brief /
  headsup / daily rundown / "catch me up", what they're letting slip, or starts
  the day with something like "morning" or "what do I need to do today" — even
  if they don't name the sources, and also when they want the headsup focused
  on one upcoming thing ("…but tell me what I need to prep for X").
---

# Daily headsup

The brief does two jobs:

1. **Top of mind.** The Top 3 tells Vince in thirty seconds what's pressing
   today: time-bound items, people waiting on him, things about to slip.
2. **Everything in flight.** Below that is a complete ledger of what he has
   going. He wants to see all of it, not just the highlights: a thing that
   quietly drops out of view is how work rots. Completeness comes from
   structure, not volume: group by theme, give each item one line, link it, and
   say where it stands.

The third ingredient is change since last time: what moved, what's new, what's
done, and what hasn't budged.

## Workflow

1. Read your private tracker page (what you saw last time).
2. Gather today's signals from Notion, GitHub, Calendar and Gmail — in parallel.
3. Diff against the tracker and rank.
4. Print the brief.
5. Rewrite the tracker page for today.
6. Offer status changes on Vince's Notion items; apply only the ones he approves.

Step 5 runs before step 6 on purpose: the tracker must reflect today even if
Vince walks away without answering.

---

## 1. Your tracker page

Your memory between runs is a single **private** Notion page titled
**Claude Daily Headsup**. It belongs to you, not to Vince's workspace: he
doesn't need to read it, and none of it goes into his shared trackers (like the
quarterly DX Initiatives database) — those are things you *read* and, with his
approval, update statuses on, never places to keep your own bookkeeping.

If the user names a different tracker page (for example in a test), use that
instead, never touch the real one, and neither read nor write the state file
below.

**Finding it:** read `~/.config/daily-headsup/state.json`
(`{"page_url": ...}`). If missing or stale, search Notion with
`title_only: true` and accept only an **exact** title match (other pages like
"Claude Daily Headsup (eval-2)" exist), then rewrite the state file. If nothing
matches, this is the first run: create it with `notion-create-pages`,
`creation_mode: "draft"`, `allow_async: false`, and write the state file.

**Format** — plain Notion markdown, rewritten whole each run:

```markdown
Private working memory for the daily-headsup skill. Edited by Claude each run.

## In flight
### Webinar (Dec 9)
- `notion:5385ff07eecf4e619b7fc71216d5a5e8` · [Webinars and blog posts](https://app.notion.com/p/…) · Not started; brief has empty sections · since 2026-11-02 · moved 2026-11-04 · unchanged 3
### GitHub
- `github:VDFaller/dbt-lint-yaml#59` · [Create LICENSE](https://github.com/…) · CI failing, no reviews · since 2026-10-30 · moved 2026-10-30 · unchanged 5

## Dismissed
- `github:dbt-labs/spark-utils#37` · don't nag; Vince will close it someday (2026-11-06)

## Log
### 2026-11-06
Top 3: … · New: 2 · Resolved: dbt-checks#3 · Proposed: 2 (applied: 1)
```

Keys must stay stable since identity across runs depends on them:
`github:<owner>/<repo>#<n>`, `notion:<page-id-no-dashes>`, `gmail:<thread-id>`.
Other fields:
- **Status text** after the link is what you saw today; tomorrow you compare
  against it to spot changes.
- **since:** when the item first appeared.
- **moved:** the last date its status actually changed.
- **unchanged:** how many consecutive runs it has sat without moving.

That last count, not how often it was mentioned, is what makes something a
repeat offender.

**What belongs in In flight:** everything Vince has going that isn't finished.
That includes active Notion work, meeting action items, PRs, review requests,
threads waiting on him, emails he owes, upcoming commitments (talks, deadlines)
and pending proposals. Group items under the same themes the brief uses.

Items leave only when they're **verified done**, or when he dismisses them
(they move to Dismissed). Going quiet doesn't count: a quiet item is exactly
what the ledger exists to keep visible.

One exception: owned initiatives that have never been touched (e.g. bulk-created
Q4 rows with no content) aren't in flight yet. Keep them out of the ledger and
summarize them in one line in the brief. An initiative joins the ledger as soon
as there's activity on it: content, a meeting, a PR, a proposal.

**First run:** there's nothing to diff; say so in one line and treat everything
as new.

## 2. Gather

Run these concurrently; they're independent. If any one source fails or isn't
authenticated, note it in one line at the top of the brief and continue.

### GitHub

```bash
uv run <skill-dir>/scripts/github_snapshot.py
```

JSON with `my_prs`, `review_requests`, `assigned_issues`, `mentions`, and
`waiting_on_me` — open threads by others that he's been part of where someone
else spoke last (often a question nobody answered). Items carry `age_days`,
`idle_days`, `last_comment {by, days_ago, snippet}`, and for PRs `ci`,
`review_decision`, `mergeable`, `draft`. For `waiting_on_me`, read the snippet
and keep only threads where the last comment plausibly needs *him* (a question,
a request, "can this be closed?") — skip FYIs. If it prints `{"error": ...}`,
report GitHub unavailable and carry on. Mention any `truncated` list.

### Notion

Look-back window: since the last run's date, at least 3 days, at most 14. On a
first run, use 7 days.

- `notion-search`, `query: ""`,
  `filters: {edited_by_user_ids: ["me"], last_edited_date_range: {start_date: <window start>}}`,
  `sort: "last_edited"`, `page_size: 25`. Drop any result whose title *or
  path* starts with "Claude Daily Headsup" — tracker pages and anything nested
  under them, yours or test ones. If filtering leaves only a handful of real
  results, page further back (narrow `end_date`) rather than concluding he did
  nothing this week.
- **Database rows** (results with `parent_data_source_url`): group by data
  source and fetch each schema once.
  - *Status-tracked databases* (like the quarterly **DX Initiatives**, which
    rolls over each quarter — discover it, don't hardcode it): SQL-query rows
    owned by Vince (`Owner` contains his user id from `notion-get-self`) whose
    status isn't in the `complete` group. This catches owned work he *didn't*
    touch this week. Report them as a group ("15 owned initiatives, all Not
    started") and only call out individual rows that have a reason to matter
    today — a meeting about it, a linked PR, a deadline, a proposal.
  - *Meeting-notes databases* (no status property): fetch the most recent notes
    he attended or wrote and pull out open action items assigned to him. These
    are often the most concrete to-dos he has, and nothing else tracks them.
- **Loose pages:** fetch the top ~6–8 by recency and look for unfinished work:
  unchecked to-dos, `TODO`/`TBD`/placeholder brackets like `[Vince]`, empty
  headings, "next steps", open comment threads (`include_discussions: true`).
  Titles and highlights are enough to decide which ones are worth opening.

### Calendar

`list_events` on the primary calendar, `orderBy: startTime`, `timeZone` unset
(the server knows his zone). Two windows:

- **Now → tomorrow noon** for the day plan. An event earns a line only if it
  changes what he does: he organizes/presents, there's an attached doc or
  agenda, external attendees, prep words (demo, webinar, review, interview,
  deadline), or it's a 1:1 with his manager. Routine meetings collapse into a
  count. Note the longest free block — it's where the top-3 work fits.
- **Next 7 days, RSVP still `needsAction`** — list these compactly; unanswered
  invites are cheap to fix and embarrassing to miss.

Link events with their `htmlLink` when the event has one.

### Gmail

Search threads from the look-back window that are addressed to him and look
like they need a reply or contain commitments: direct questions, requests,
meeting-notes summaries ("Notes:" / Gemini recaps) that list action items for
him. Skip newsletters, notifications, and automated mail. Every thread he owes
a reply on goes in the ledger; this isn't inbox triage, it's catching
commitments.

## 3. Reconcile and rank

Build today's items, each with a key, title, link, source, status today, and
theme. Then reconcile them against the tracker's In flight ledger.

The ledger is the source of truth for what he has going, so **re-check every
ledger item each run**, not just the ones today's searches happened to surface:
- **GitHub items** appear in the script output if they're still open. If one is
  missing, run `gh pr view <url> --json state,mergedAt` or `gh issue view`.
- **Notion pages and rows:** fetch any that today's search didn't return, and
  check their status and to-dos.
- **Meeting action items:** re-fetch the notes page to see whether the boxes
  got checked.
- **Email threads:** check whether he has replied since.

Then classify each item:

- **New:** not in the ledger yet.
- **Moved:** status differs from what the ledger recorded (CI went red, a review
  arrived, a Notion status changed, to-dos got checked). Set `moved` to today
  and reset `unchanged` to 0. These lines are often the most actionable.
- **Unchanged:** same status as last run, so `unchanged` goes up by one. At 3 or
  more, it's a repeat offender; say so (`unchanged 5 runs 🔁`). Making quiet
  avoidance visible is the reason the tracker exists.
- **Done:** verified merged, closed, launched, replied to, or checked off.
  Report it under Since last run and drop it from the ledger. Don't assume
  something is done just because it didn't show up today; check.
- **Dismissed** items stay out of the brief unless something material changed
  (a dismissed PR got a review).

Rotting defaults (use judgment):

| Thing | Rotting when |
|---|---|
| My PR | CI failing, changes requested, merge conflict, or idle > 3 days |
| Review requested of me | waiting > 1 working day |
| Waiting on me (GitHub thread / email) | last comment > 2 days old |
| Assigned issue | idle > 14 days |
| Mention | unread > 1 day |
| Notion item he owns, not complete | In progress but untouched > 7 days, or past a milestone/date |
| Meeting action item | still open 3+ days after the meeting |

Rotting items get a ⚠️ in the ledger. Anything idle > 90 days is abandoned
rather than rotting: put it in the **Close or revive?** group at the bottom of
the ledger, with its unchanged count, and keep it out of the Top 3 unless it's
blocking someone else. A five-month-old LICENSE PR is a 30-second cleanup,
not today's priority.

Cross-reference sources — this is where the brief earns its keep. An initiative
whose open question is the topic of today's 1pm meeting; a webinar brief with
empty sections and a run-of-show invite he hasn't answered; a review request
from someone he's meeting this afternoon. Say these connections out loud.

### Status proposals

Vince is happy for you to move his own Notion items forward (e.g. Not started
→ In progress) once he approves. Propose only with evidence, and state it:

- Not started → In progress: substantive work on it in the window (content
  added, a brief drafted, a meeting held about it). Rows that were merely
  created or bulk-edited don't count — check that the page has real content
  beyond the template.
- In progress → complete group: linked PR merged, all to-dos checked, or the
  page says it shipped.
- In progress but untouched > 21 days: don't propose a status. Mark it ⚠️ in
  the ledger and ask whether it's still real.

Only propose on items he owns or created. Never change other people's rows.

## 4. The brief

Print it as Markdown in the terminal. Everything above the ledger (Top 3,
Calendar, Since last run) should read in under a minute. The ledger can be as
long as his workload; that's the point. Keep each item to one line by putting
the detail behind the link. Link every Notion page, GitHub item, email thread
and calendar event. Omit empty sections rather than writing "nothing here".

```markdown
# Headsup — <Weekday Mon D>

**Today's top 3**
1. <the most pressing thing, and why today>
2. …
3. …

## Calendar
- 13:00 [namespaces comms](…): RSVP needed; it's about your PyPI initiative
- RSVP needed this week: [Run of show](…) Fri 10:30 · [All Hands](…) Wed
- +2 routine · longest free block 11:00–13:00

## Since last run
- ✅ Done: … · 🆕 New: … · 🔄 Moved: …

## In flight
### Webinar: v2 community (Dec 9)
- [Webinar brief](…): `[Vince]` placeholder, Speaking Points empty ⚠️ · reg page due today
- [Webinars and blog posts](…): Not started, unchanged 4 runs 🔁 (see proposal 1)
- [Email: kickoff notes](…): you record your segment by 11/30
### V2 install defaults / PyPI
- [Investigate install defaults](…): open question (Elias vs Grace) · meeting today 13:00
### Meeting follow-ups
- [Jeremy 1:1](…): ask Joel re DuckDB diffs · ask Anders re Iceberg · telemetry check
- [Leith 1:1](…): FY28 tools/equipment asks due ~Wed 11/11
### Waiting on you
- [dbt Support #140453](…): retry GitHub link and reply
- [ade-bench#68](…): asked "can this be closed?" 112d ago
### GitHub
- [org/repo#123](…): CI failing 4d ⚠️ · unchanged 5 runs 🔁
### Not yet started
- 13 other owned Q4 initiatives with no activity: <short names, comma-separated>
### Close or revive?
- [repo#37](…) idle 1105d · [repo#59](…) idle 141d, unchanged 5 runs

## Proposed Notion updates
1. [Initiative](…): Not started → In progress. <evidence>
```

Pick ledger themes from the work itself (a project, a launch, an initiative,
"meeting follow-ups", "waiting on you", "GitHub") and keep them stable across
runs, so he learns where to look.

**Top 3** is what should be top of mind this morning, pressing things first.
Rank in this order:
1. Anything time-bound today or tomorrow: a meeting that needs prep, a deadline,
   an RSVP for something imminent.
2. Things blocking other people: questions or reviews waiting on him, someone's
   copy depending on his.
3. Whatever he's actively pushing on.

Use repeat offenders to break ties. The Top 3 is a synthesis: each of those
items also has its line in the ledger.

**Focused requests** ("…tell me what I need to prep for the webinar"): keep the
full brief and add a `## <Topic> prep` section right after the Top 3. For that topic, look further ahead than usual — search the calendar out
to the event date, pull the relevant Notion pages, workback plans and emails —
and give concrete prep items with their due dates. The topic should dominate the
Top 3 only if it's genuinely the most urgent thing.

## 5. Rewrite the tracker

Right after printing the brief, replace the tracker page's content in one call
(`notion-update-page`, `replace_content`) with today's version:

- **In flight:** the full ledger, grouped by theme. Each item records today's
  status, its original `since` date, `moved` and `unchanged`. Drop only items
  verified done. Quiet items stay.
- **Dismissed:** carry over unchanged, plus anything newly dismissed.
- **Log:** today's entry on top, one or two lines; keep the 14 most recent
  entries and drop older ones.

Then (first run only) write `~/.config/daily-headsup/state.json`.

## 6. Apply approved changes

If there are proposals, end with: *"Reply with the numbers to apply (e.g.
`1 3`), `all`, or `none`. Say `stop tracking <item>` to dismiss something."*
If there are none, just end with the brief.

For approved numbers: fetch the data source schema if it isn't loaded, then
`notion-update-page` → `update_properties` with the exact property and option
names. Update the item's status text in your tracker and note what was applied
in today's log line. For "stop tracking", move the item from In flight to
Dismissed with his reason.
