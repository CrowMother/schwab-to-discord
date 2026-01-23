# Logging

## `setup_logging()`
**What it does:** Configures Python logging once, early in startup, so every module can do:
`logger = logging.getLogger(__name__)`

**Needs to run:**
- `import logging`
- Called once at startup (usually in `main()`)

**Notes:**
- Do NOT “import the logger” from main into modules.
- Configure logging globally once; each file gets its own `getLogger(__name__)`.
