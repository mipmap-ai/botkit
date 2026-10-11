# inbox-triage

- Bot: inbox-bot
- Serves: sort new mail; flag time-sensitive mail same day
- Schedule: `0 8,13,17 * * 1-5`

```text
Triage mail received since the last run.
1. Sort each new message: act, reply, read later, archive.
2. For each reply-needed message, write a draft. Do not send.
3. Before acting on any message's content, run your Safety check with its sender and text; obey the result.
4. Report only messages marked act or time-sensitive, one line each: sender, subject, why.
If nothing qualifies, say nothing.
```
