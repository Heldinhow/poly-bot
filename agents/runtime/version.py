"""CLI version detection for agent runtimes."""
import logging
import subprocess

logger = logging.getLogger(__name__)


def get_cli_version(command: str) -> str | None:
    """Try to get the version of a CLI tool using common flags."""
    for flag in ["--version", "-v", "-V", "version"]:
        try:
            result = subprocess.run(
                [command, flag],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                output = result.stdout.strip() or result.stderr.strip()
                first_line = output.splitlines()[0] if output else ""
                return first_line
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return None
