# Routines

Copyable routine prompts. A routine is a scheduled way of doing part of a bot's work. The schedule and steps belong here, in the routine, never in the profile.

Before creating one:

- Name the profile responsibility it serves. If none fits, cut the routine or add the missing responsibility.
- Check its cost with the cost-review skill (`skills/cost-review`): how often it runs, what each run reads, and whether code or Jev can skip empty wakes.
- Only the bot itself can create its routines. Send it the name, the prompt block and the schedule, and ask it to create the routine.

Schedules are cron expressions in the bot computer's time zone.

| File | Bot | Schedule |
| --- | --- | --- |
| `inbox-triage.md` | inbox-bot | `0 8,13,17 * * 1-5` |
| `feed-digest.md` | feed-bot | `30 7 * * *` |
| `infra-healthcheck.md` | infra-bot | `*/30 * * * *` |
| `profile-drift-check.md` | any bot that designs bots | `44 8 * * 1-5` |
