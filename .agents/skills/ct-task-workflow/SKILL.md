---
name: ct-task-workflow
description: Deliver a named Computational Thinking sprint task or prepare its acceptance evidence and handoff. Use when a request cites a project backlog ID or asks to verify completion of a sprint task.
---

# Deliver a sprint task

1. Read [project rules](../../../AGENTS.md). If the checkout includes `docs/TASK_BREAKDOWN.md` and `docs/TASK_INSTRUCTIONS.md`, find the task there. Otherwise, use the task details supplied by the user. Capture the deliverable, dependencies, expected layer or files, and acceptance check.
2. Check dependencies in the actual working tree. Trace the affected entry point and the callers of any shared interface. If an upstream dependency is missing, keep any independent work within scope and state what is blocked. Use an existing fixture or stub only if it follows an agreed interface.
3. Use the acceptance check to choose the smallest end-to-end scenario and the failure case most likely to affect the student or a downstream task. For interview flows, use synthetic answers and a fixture provider where possible. Distinguish an isolated check from a result demonstrated through the normal application entry point.
4. Hand off with the task ID, affected MVC-S layers and files, commands and observed outcomes, and any missing integration evidence. Include dependencies that this result unblocks. Use the task ID in the PR title if the user requests a PR.
