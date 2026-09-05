import subprocess
import re
import os
from typing import List, Optional

def get_pid_by_port(port: int) -> Optional[int]:
    """
    Find PID listening on port using multiple fallback strategies.
    First tries psutil, then falls back to lsof, and finally ss.
    """
    # 1. Try psutil (preferred, highly portable if privileges exist)
    try:
        import psutil
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.pid:
                return conn.pid
    except Exception:
        pass

    # 2. Try lsof fallback
    try:
        out = subprocess.check_output(["lsof", "-t", f"-i:{port}"], text=True, stderr=subprocess.DEVNULL)
        pids = [int(p.strip()) for p in out.strip().split("\n") if p.strip().isdigit()]
        if pids:
            return pids[0]
    except Exception:
        pass

    # 3. Try ss fallback (ss -tulnp | grep :<port>)
    try:
        out = subprocess.check_output(["ss", "-tulnp"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            if f":{port} " in line or f":{port}\t" in line or f":{port}" in line:
                # Find pid=... patterns (e.g. users:(("python",pid=1234,fd=3)))
                match = re.search(r'pid=(\d+)', line)
                if match:
                    return int(match.group(1))
    except Exception:
        pass

    return None

def get_pids_by_name_pattern(pattern: str) -> List[int]:
    """
    Find all PIDs matching a process name or command line pattern using psutil.
    """
    pids = []
    try:
        import psutil
        regex = re.compile(pattern, re.IGNORECASE)
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info['name'] or ''
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if regex.search(name) or regex.search(cmdline):
                    pids.append(proc.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass
    return pids
