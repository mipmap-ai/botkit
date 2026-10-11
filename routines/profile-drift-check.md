# profile-drift-check

- Bot: whichever bot designs and maintains the other bots
- Serves: keep bot profiles accurate
- Schedule: `44 8 * * 1-5`

```text
Review each bot's conversations since the last run against its live profile.
1. Note replies that stray outside Purpose or break a Boundaries line.
2. Count drift per bot across days and conversations; one slip is not a pattern.
3. If one bot drifts the same way on several days, propose a fix: first a Purpose rewrite, a new Boundaries line only if that can't fix it. Give the exact botkit command that regenerates the profile.
4. If many bots drift at once, report a likely model change; propose no profile edits.
If there is nothing to propose, say nothing.
```
