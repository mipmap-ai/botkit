# feed-digest

- Bot: feed-bot
- Serves: send short digest when anything qualifies; quiet otherwise
- Schedule: `30 7 * * *`

```text
Read items from subscribed feeds published since the last run.
1. Read interests.md via the reference index.
2. Keep items that clearly match a listed interest; drop repeats of items already sent.
3. Send one digest: link first, then one line on why it matters. At most 10 items.
If nothing qualifies, send nothing.
```
