# Expansion 

## Expansion strategy (future you will thank you)

When you add features:

New API → new file in api/

New DB logic → new function in db/queries.py

New output → new module (Slack, Email, etc.)

🚫 Never:

Keep stacking functions into one file

Cross-call APIs directly from main

##  Maintenance rules (print these mentally)

One module = one responsibility

No side effects at import time

Main orchestrates only

Use dataclasses + type hints everywhere

No hardcoded secrets or paths

Log at boundaries (API in/out, DB writes, Discord posts)

## How to actually begin tomorrow

Create folders + empty __init__.py

Write config.py

Write a fake Schwab API function that returns mock data

Write DB schema + insert/query logic

Wire everything in main.py

Replace mocks with real API calls later

This keeps momentum without blocking on integrations.

## What you’re building is already production-grade in structure, even if it starts small. If you stick to:

orchestration in main

isolation of external systems

typed models

boring SQLite usage

…this will stay maintainable years down the line.