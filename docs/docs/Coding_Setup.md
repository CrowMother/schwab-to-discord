# Setup 

For the purpose of documenting setup of what happened

## Layout
    your_project/
    │
    ├─ .venv/               # virtual environment (not committed)
    ├─ src/
    │   └─ your_project/
    │       ├─ __init__.py
    │       └─ main.py
    │
    ├─ tests/
    │   └─ test_basic.py
    │
    ├─ docs/
    │
    ├─ requirements.txt
    ├─ README.md
    └─ pyproject.toml       # optional but recommended

## Virtual Enviroment

Execute at project root

    python -m venv .venv


### Activate it

Windows (PowerShell):

    .venv\Scripts\Activate.ps1


macOS / Linux:

    source .venv/bin/activate

### Tell VS Code to use it

`Ctrl + Shift + P` → Python: Select Interpreter

Choose the one inside .venv

## VS Code Extensions
* Core
    * Python (Microsoft)

    * Pylance (Microsoft)

    * Docker

    * Dev Containers

* Code quality (highly recommended)

    * Black Formatter

    * Ruff

    * Error Lens

* Docker deployment

    * YAML (Red Hat)

    * Hadolint (Dockerfile linting)

* SQLite tools

    * SQLite Viewer

## Documentation

* Currently all written in MD

#### MkDocs

    pip install mkdocs mkdocs-material

    mkdocs new docs

    mkdocs serve

## Dependency management

Learn how to use the project toml tool

Currently `pip freeze > requirements.txt` is what I am going to use as this will blend into docker container easier. 

## Testing
Pytest:

    pip install pytest

example test:

    def test_add():
    assert 1 + 1 == 2

run:

    pytest

## VS code settings
create `.vscode/settings.json`:

    {
    "python.defaultInterpreterPath": ".venv/bin/python",
    "editor.formatOnSave": true,
    "python.formatting.provider": "black",
    "python.linting.enabled": true
    }

## Git
`.gitignore`:

    .venv/
    __pycache__/
    *.db

`dockerignore`:

    .venv
    __pycache__
    .git
    .vscode
    *.db

## Final tips

#### Health Checks

structure code ot utilize

    def healthcheck() -> bool:
    return True

later:

    HEALTHCHECK CMD python -c "import app; app.healthcheck()"

