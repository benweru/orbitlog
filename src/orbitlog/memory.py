"""Memory measurement under a hard cgroup v2 cap.

Plan: systemd-run --scope -p MemoryMax=512M -p MemorySwapMax=0 llama-cli ...
then read memory.peak (includes page cache, so mmap'd weights are counted).
Also report RSS, flash bytes read per token, tok/s, hardware/kernel fingerprint.
"""
import platform


def fingerprint() -> dict:
    """Hardware/kernel fingerprint logged with every result."""
    return {
        "machine": platform.machine(),
        "system": platform.system(),
        "release": platform.release(),
        "python": platform.python_version(),
    }


def run_capped(cmd: list[str], max_mib: int) -> dict:
    """TODO(sprint 1): run cmd in a cgroup v2 scope, return memory.peak, RSS, tok/s."""
    raise NotImplementedError("cgroup memory harness not yet implemented")
