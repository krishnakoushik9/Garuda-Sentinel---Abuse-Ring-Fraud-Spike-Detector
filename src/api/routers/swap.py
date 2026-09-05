from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import psutil

from src.system.swap_manager import swap_manager

router = APIRouter(prefix="/swap", tags=["Swap Management"])

class PIDRequest(BaseModel):
    pid: int

@router.get("/status", response_model=Dict[str, Any])
def get_swap_status():
    """
    Returns current swap usage, system capabilities, and protected PIDs details.
    """
    swap = psutil.swap_memory()
    # Refresh capabilities check
    swap_manager.capabilities = swap_manager.check_system_capabilities()
    
    # Format protected processes details
    protected_details = []
    for pid in list(swap_manager.protected_pids):
        try:
            proc = psutil.Process(pid)
            swap_used = swap_manager.get_process_swap_usage(pid)
            protected_details.append({
                "pid": pid,
                "name": proc.name(),
                "status": proc.status(),
                "swap_kb": swap_used,
                "swap_mb": round(swap_used / 1024, 2)
            })
        except Exception:
            protected_details.append({
                "pid": pid,
                "name": "Unknown",
                "status": "Inactive",
                "swap_kb": 0,
                "swap_mb": 0.0
            })

    return {
        "status": "active" if swap_manager.active else "inactive",
        "swap_total_gb": round(swap.total / (1024**3), 2),
        "swap_used_gb": round(swap.used / (1024**3), 2),
        "swap_free_gb": round(swap.free / (1024**3), 2),
        "swap_percent": swap.percent,
        "capabilities": swap_manager.capabilities,
        "protected_pids": list(swap_manager.protected_pids),
        "protected_processes": protected_details,
        "top_consumers": swap_manager.get_top_swap_consumers(limit=5)
    }

@router.post("/flush", response_model=Dict[str, Any])
def trigger_swap_flush():
    """
    Manually triggers aggressive swap flushing of non-protected background processes.
    """
    try:
        metrics = swap_manager.flush_non_critical_processes()
        return {
            "status": "success",
            "message": "Aggressive swap flush completed successfully.",
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Swap flush failed: {e}")

@router.post("/clean-cache", response_model=Dict[str, Any])
def trigger_cache_clean():
    """
    Manually triggers deep filesystem cache purging, docker prune, and package manager cache cleanups.
    """
    try:
        metrics = swap_manager.clean_system_caches()
        return {
            "status": "success",
            "message": "Deep cache cleaning completed successfully.",
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache clean failed: {e}")

@router.post("/protect", response_model=Dict[str, Any])
def protect_pid(req: PIDRequest):
    """
    Dynamically locks a specific PID in physical RAM.
    """
    if not psutil.pid_exists(req.pid):
        raise HTTPException(status_code=404, detail=f"PID {req.pid} is not active on this system.")
    
    swap_manager.dynamic_protected_pids.add(req.pid)
    swap_manager.protected_pids.add(req.pid)
    
    results = swap_manager.protect_pids_from_swap([req.pid])
    method = results.get(req.pid, "Unknown")
    
    return {
        "status": "success",
        "message": f"PID {req.pid} added to swap protection list.",
        "protection_method": method
    }

@router.post("/unprotect", response_model=Dict[str, Any])
def unprotect_pid(req: PIDRequest):
    """
    Removes a PID from the dynamic swap protection list.
    """
    if req.pid in swap_manager.dynamic_protected_pids:
        swap_manager.dynamic_protected_pids.remove(req.pid)
    if req.pid in swap_manager.protected_pids:
        swap_manager.protected_pids.remove(req.pid)
        
    # Re-enable swap if cgroups were used
    try:
        cgroup_path = None
        with open(f"/proc/{req.pid}/cgroup", "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 3:
                    cgroup_path = parts[2]
                    break
        if cgroup_path:
            cgroup_dir = f"/sys/fs/cgroup{cgroup_path}"
            if not os.path.exists(cgroup_dir):
                cgroup_dir = "/sys/fs/cgroup"
            swap_max_file = f"{cgroup_dir}/memory.swap.max"
            if os.path.exists(swap_max_file):
                try:
                    with open(swap_max_file, "w") as f:
                        f.write("max")
                except PermissionError:
                    import subprocess
                    subprocess.run(["sudo", "-n", "tee", swap_max_file], input="max", text=True, capture_output=True)
    except Exception:
        pass
        
    return {
        "status": "success",
        "message": f"PID {req.pid} removed from swap protection list."
    }
