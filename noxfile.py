import nox
from nox import Session, session

nox.options.default_venv_backend = "uv"
nox.options.error_on_external_run = True
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["fmt", "types", "tests"]


@session(python=["3.8", "3.9", "3.10"])
def tests(s: Session) -> None:
    s.install("-e", ".", "coverage[toml]==7.6.1")
    s.run("coverage", "run", "-m", "unittest", "discover", "-s", "tests")

@session(python=["3.10"])
def fmt(s: Session) -> None:
    s.install(".", "ruff==0.6.1")
    s.run("ruff", "format", "src", "tests")


@session(python=["3.10"])
def types(s: Session) -> None:
    s.install(".", "mypy==1.11.1")
    s.run("mypy", "src")
