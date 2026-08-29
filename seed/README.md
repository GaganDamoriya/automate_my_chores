# Simulated activity (seed data)

`generate.py` builds a fake-but-realistic event log for a fictional org so the
agents have something to **discover**. Only the data *source* is simulated — the
agents, reasoning, execution and verification are real.

```bash
python3 seed/generate.py
```

Writes to `seed/data/` (git-ignored):

| file | what it is | consumed by |
|------|------------|-------------|
| `activity_events.json` | normalized cross-tool events, unlabeled | Observer → Pattern |
| `ticket_events.json`   | Jira ticket lifecycle incl. reopens / QA fails | Rework agent |
| `review_comments.json` | GitHub PR reviews + QA comments | Rework agent |
| `ground_truth.json`    | what a perfect agent *should* find | evaluation only |

The events carry **no workflow labels** — the agent has to find the repetition
itself. Ground truth is kept in a separate file the agents never read, so we can
score discovery accuracy honestly.

Seeded scenarios: **Weekly Engineering Report** (Gmail→Jira→Sheets→Slack, weekly,
~52 min) and **Customer CSV Cleanup** (~4×/week, ~31 min), buried in ~220 decoy
events. Rework: 28 tickets, a realistic reopen distribution, with "missing
edge-case tests" as the dominant recurring theme.
