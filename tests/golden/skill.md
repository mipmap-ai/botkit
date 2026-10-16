---
name: weekly-cleanup
description: "Use when asked to clean up old drafts: archive, never delete."
---
Purpose:
- archive drafts untouched for 30 days

Input:
- drafts folder

Steps:
- 1. list drafts older than 30 days
- 2. archive each
- 3. report count

Decide:
- none found: say nothing
- archive fails: stop, report error

Confirm:
- when a decision or possible decision appears, show the decision card with the multiple-choice options; wait for a yes before doing anything

Run:
- mailtool archive --older-than 30d --folder drafts

Never:
- delete a draft
