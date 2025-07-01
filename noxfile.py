import nox
from nox import Session, session

nox.options.default_venv_backend = "uv"
nox.options.error_on_external_run = True
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["fmt", "ty", "tests", "cov_report"]


@session(python=["3.8", "3.9", "3.10"])
def tests(s: Session) -> None:
    s.run_install(
        "uv",
        "sync",
        "--frozen",
        "--group=test",
        "--no-default-groups",
        f"--python={s.virtualenv.location}",
        env={"UV_PROJECT_ENVIRONMENT": s.virtualenv.location},
    )
    # Determine if --cov and/or --cov-report is passed
    with_cov = "--cov" in s.posargs
    with_cov_report = "--cov-report" in s.posargs
    if with_cov:
        s.run("coverage", "run", "-m", "unittest", "discover", "-s", "tests")
        if with_cov_report:
            s.notify("cov_report")
    else:
        s.run("python", "-m", "unittest", "discover", "-s", "tests")


@session(python=["3.10"])
def cov_report(s: Session) -> None:
    """Combine coverage data and generate report."""
    s.run_install(
        "uv",
        "sync",
        "--frozen",
        "--group=coverage",
        "--no-default-groups",
        f"--python={s.virtualenv.location}",
        env={"UV_PROJECT_ENVIRONMENT": s.virtualenv.location},
    )
    s.run("coverage", "combine")
    s.run("coverage", "report", "-m", "--skip-covered")
    s.run("coverage", "json")


@session(python=["3.8"])
def fmt(s: Session) -> None:
    s.run_install(
        "uv",
        "sync",
        "--frozen",
        "--group=lint",
        "--no-default-groups",
        f"--python={s.virtualenv.location}",
        env={"UV_PROJECT_ENVIRONMENT": s.virtualenv.location},
    )
    s.run("ruff", "format", "src", "tests")


@session(python=["3.8", "3.9", "3.10"])
def ty(s: Session) -> None:
    s.run_install(
        "uv",
        "sync",
        "--frozen",
        "--group=typing",
        "--no-default-groups",
        f"--python={s.virtualenv.location}",
        env={"UV_PROJECT_ENVIRONMENT": s.virtualenv.location},
    )
    s.run("mypy", "src")
