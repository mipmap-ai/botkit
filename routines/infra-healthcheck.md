# infra-healthcheck

- Bot: infra-bot
- Serves: watch disk, memory, uptime, cert expiry; report breakage with likely cause
- Schedule: `*/30 * * * *`

```text
Check each server listed in runbook.md.
1. Collect disk use, memory, uptime and days to cert expiry.
2. Compare with the runbook thresholds.
3. For a breach with a runbook fix, run your Safety check with the action and target; apply the fix only on ALLOW.
4. Report each breach once, status first: server, metric, value, likely cause, what you did.
If everything is within thresholds, say nothing.
```
