---
name: mention-scout
description: "Use when scanning new mentions for ones worth a reply."
---
Purpose:
- pick mentions worth a reply

Input:
- mentions since last run
- state file of seen ids

Questions:
- needs_reply (yes/no): a reply would help the asker
- tone (pick-one: friendly/neutral/hostile): tone of the mention

Steps:
- 1. drop ids already in state file
- 2. ask Jev questions per mention
- 3. list picks, one line each

Decide:
- id in state file: skip, no Jev call
- needs_reply >= 0.8: list it
- needs_reply 0.5-0.8: list under maybe
- tone hostile: never list
- Jev down (exit 2): list nothing; report Jev down once

Confirm:
- when a decision or possible decision appears, show the decision card with the multiple-choice options; wait for a yes before doing anything

Run:
- jev ask --questions mention-scout.questions --input {mention}

Never:
- reply or post
