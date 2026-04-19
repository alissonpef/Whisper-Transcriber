"""PID-based lockfile utilities used to ensure single popup instance."""

from __future__ import annotations

import os
from pathlib import Path

from src.config import LOCK_FILE
from src.logger import get_logger

logger = get_logger(__name__)


def _pid_is_running(pid: int) -> bool:
    """Return True when a process PID currently exists."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # PID exists but cannot be signaled by this user.
        return True


def _read_pid(path: Path) -> int | None:
    """Read and parse PID from the lock file."""
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def get_pid() -> int | None:
    """Get lock owner PID, or None when lock is absent/invalid."""
    return _read_pid(LOCK_FILE)


def is_locked() -> bool:
    """Check if lock exists and its PID still represents a live process."""
    pid: int | None = get_pid()
    if pid is None:
        return False
    return _pid_is_running(pid)


def _try_create_lock(path: Path, pid: int) -> bool:
    """Atomically create a lockfile and write PID."""
    flags: int = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd: int | None = None
    try:
        fd = os.open(path, flags)
        os.write(fd, f"{pid}".encode("utf-8"))
        return True
    except FileExistsError:
        return False
    finally:
        if fd is not None:
            os.close(fd)


def acquire() -> bool:
    """Acquire lock for current PID.

    Returns False if a live process already holds it.
    Stale lockfiles are removed automatically.
    """
    current_pid: int = os.getpid()

    if _try_create_lock(LOCK_FILE, current_pid):
        logger.debug("Acquired lockfile with PID %s", current_pid)
        return True

    existing_pid: int | None = get_pid()
    if existing_pid is not None and _pid_is_running(existing_pid):
        logger.debug("Lockfile already held by live PID %s", existing_pid)
        return False

    # Stale or invalid lock content; attempt recovery once.
    release()
    if _try_create_lock(LOCK_FILE, current_pid):
        logger.info("Recovered stale lockfile and acquired new lock")
        return True

    logger.debug("Failed to acquire lockfile after stale recovery")
    return False


def release() -> None:
    """Release the lock if present."""
    try:
        LOCK_FILE.unlink(missing_ok=True)
        logger.debug("Released lockfile")
    except OSError:
        # Keep release idempotent and never raise during shutdown.
        logger.exception("Unable to remove lockfile")
