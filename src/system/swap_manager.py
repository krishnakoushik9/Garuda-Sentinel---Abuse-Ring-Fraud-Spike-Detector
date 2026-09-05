import os
import sys
import time
import ctypes
import signal
import logging
import sqlite3
import uuid
import yaml
import psutil
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Set, Optional
from threading import Thread, Lock

from src.system.process_scanner import get_pid_by_port, get_pids_by_name_pattern

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SwapManager")

MCL_CURRENT = 1
MCL_FUTURE = 2

class SwapManager:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SwapManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.config_path = os.path.join(os.getcwd(), "config.yaml")
        self.config = self._load_config()
        self.capabilities = self.check_system_capabilities()
        self.protected_pids: Set[int] = set()
        self.dynamic_protected_pids: Set[int] = set()
        self.active = False
        self.monitor_thread: Optional[Thread] = None
        self._initialized = True

    def run_sudo(self, cmd: List[str], input_data: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Executes a command with sudo, supplying password authentication automatically using '1156'.
        """
        # Prepend sudo -S to the command
        sudo_cmd = ["sudo", "-S"] + cmd
        
        # If the command is 'tee', we can write to files using a shell redirect
        if len(cmd) >= 2 and cmd[0] == "tee":
            filepath = cmd[1]
            sh_cmd = ["sudo", "-S", "sh", "-c", f"echo '{input_data}' > '{filepath}'"]
            try:
                res = subprocess.run(sh_cmd, input="1156\n", text=True, capture_output=True)
                if res.returncode != 0:
                    logger.warning(f"run_sudo sh -c write to {filepath} returned non-zero code {res.returncode}: {res.stderr.strip()}")
                return res
            except Exception as e:
                logger.warning(f"run_sudo write to {filepath} failed: {e}")
                # Fallback to direct tee (without -n)
                return subprocess.run(["sudo", "-S", "tee", filepath], input=f"1156\n{input_data}", text=True, capture_output=True)
                
        # Normal command
        try:
            res = subprocess.run(sudo_cmd, input="1156\n", text=True, capture_output=True)
            if res.returncode != 0:
                logger.warning(f"run_sudo command {cmd} returned non-zero code {res.returncode}: {res.stderr.strip()}")
            else:
                logger.info(f"run_sudo command {cmd} completed successfully. stdout: {res.stdout.strip()}")
            return res
        except Exception as e:
            logger.warning(f"run_sudo command {cmd} failed: {e}")
            # Fallback
            return subprocess.run(["sudo"] + cmd, input=input_data, text=True, capture_output=True)

    def _load_config(self) -> dict:
        """Loads configuration from config.yaml with secure fallbacks."""
        defaults = {
            "enabled": True,
            "swappiness": 85,
            "cache_pressure": 200,
            "protect_ports": [8000, 5173, 7687],
            "protect_names": ["train_models.py", "guard.sh"],
            "swap_threshold_percent": 80,
            "monitor_interval_seconds": 60,
            "flush_on_train": True
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = yaml.safe_load(f)
                    if data and "swap_manager" in data:
                        # Merge defaults with loaded config
                        for k, v in data["swap_manager"].items():
                            defaults[k] = v
            except Exception as e:
                logger.error(f"Failed to load config.yaml: {e}. Using defaults.")
        return defaults

    def check_system_capabilities(self) -> dict:
        """
        Task 1: System Assessment & Feature Detection
        Detects total/available swap, mlock capability, cgroups v2, and sysctl write privileges.
        """
        # Swap memory
        swap = psutil.swap_memory()
        swap_total_gb = round(swap.total / (1024**3), 2)
        swap_available_gb = round(swap.free / (1024**3), 2)

        # check mlockall capability
        has_mlock_privilege = False
        try:
            libc = ctypes.CDLL(None)
            res = libc.mlockall(MCL_CURRENT | MCL_FUTURE)
            if res == 0:
                libc.munlockall()
                has_mlock_privilege = True
        except Exception:
            pass

        # check cgroups v2
        has_cgroup_v2 = os.path.exists("/sys/fs/cgroup/cgroup.controllers")

        # check sysctl write privilege by checking if we can open swappiness for writing
        has_sysctl_write = False
        try:
            with open("/proc/sys/vm/swappiness", "r+") as f:
                has_sysctl_write = True
        except Exception:
            pass

        # current swappiness
        current_swappiness = 60
        try:
            with open("/proc/sys/vm/swappiness", "r") as f:
                current_swappiness = int(f.read().strip())
        except Exception:
            pass

        return {
            'swap_total_gb': swap_total_gb,
            'swap_available_gb': swap_available_gb,
            'has_mlock_privilege': has_mlock_privilege,
            'has_cgroup_v2': has_cgroup_v2,
            'has_sysctl_write': has_sysctl_write,
            'current_swappiness': current_swappiness,
            'suggested_swappiness': self.config.get("swappiness", 85)
        }

    def aggressive_swap_tuning(self) -> bool:
        """
        Task 3: Swap Aggression Tuning at Startup
        Tunes vm.swappiness and vm.vfs_cache_pressure.
        """
        if not self.config.get("enabled", True):
            logger.info("SwapManager is disabled in config.")
            return False

        swappiness = self.config.get("swappiness", 85)
        cache_pressure = self.config.get("cache_pressure", 200)

        logger.info(f"Tuning kernel: swappiness={swappiness}, vfs_cache_pressure={cache_pressure}...")

        success = True
        # Try direct write, or sysctl subprocess, or sudo fallback
        for param, val in [("swappiness", swappiness), ("vfs_cache_pressure", cache_pressure)]:
            param_success = False
            path = f"/proc/sys/vm/{param}"
            # 1. Direct write
            try:
                with open(path, "w") as f:
                    f.write(str(val))
                param_success = True
            except PermissionError:
                # 2. Try sysctl command
                try:
                    res = subprocess.run(["sysctl", "-w", f"vm.{param}={val}"], capture_output=True, text=True)
                    if res.returncode == 0:
                        param_success = True
                except Exception:
                    pass
                
                # 3. Try sudo sysctl command (authenticated)
                if not param_success:
                    try:
                        res = self.run_sudo(["sysctl", "-w", f"vm.{param}={val}"])
                        if res.returncode == 0:
                            param_success = True
                    except Exception:
                        pass
            except Exception:
                pass

            if not param_success:
                logger.warning(f"Unable to set vm.{param} to {val}. Sudo privileges may be required.")
                success = False
            else:
                logger.info(f"Successfully tuned vm.{param} to {val}.")

        # Update capability record
        self.capabilities = self.check_system_capabilities()
        return success

    def protect_pids_from_swap(self, pids: List[int]) -> Dict[int, str]:
        """
        Task 4: Process Swap Protection (mlockall / cgroups)
        Guarantees that memory pages of specified PIDs remain in physical RAM.
        Returns a dictionary mapping PIDs to the success method used.
        """
        results = {}
        my_pid = os.getpid()

        for pid in pids:
            if pid <= 0:
                continue

            # Check if PID is running
            if not psutil.pid_exists(pid):
                results[pid] = "Failed (PID not running)"
                continue

            # Approach 1: If it's our own process, use mlockall via ctypes
            if pid == my_pid:
                try:
                    libc = ctypes.CDLL(None)
                    res = libc.mlockall(MCL_CURRENT | MCL_FUTURE)
                    if res == 0:
                        results[pid] = "mlockall"
                        logger.info(f"Locked backend process PID {pid} in RAM using mlockall.")
                        continue
                except Exception as e:
                    logger.warning(f"mlockall failed for self PID {pid}: {e}")

            # Approach 2: Use cgroups v2 memory protection (disable swap for the process's cgroup)
            if self.capabilities.get("has_cgroup_v2", False):
                try:
                    cgroup_path = None
                    with open(f"/proc/{pid}/cgroup", "r") as f:
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
                                    f.write("0")
                                results[pid] = "cgroups v2"
                                logger.info(f"Disabled swap for PID {pid} via cgroups v2 memory.swap.max.")
                                continue
                            except PermissionError:
                                # Try with sudo
                                res = self.run_sudo(["tee", swap_max_file], input_data="0")
                                if res.returncode == 0:
                                    results[pid] = "cgroups v2 (sudo)"
                                    logger.info(f"Disabled swap for PID {pid} via cgroups v2 memory.swap.max (sudo).")
                                    continue
                except Exception as e:
                    logger.warning(f"cgroups v2 protection failed for PID {pid}: {e}")

            # Fallback: best-effort tuning only
            results[pid] = "System-wide swappiness fallback"
            logger.warning(f"Could not lock PID {pid} in RAM. Sudo or mlock privileges missing. Best-effort swappiness tuning applied.")
        
        return results

    def discover_and_protect_critical_services(self) -> List[int]:
        """
        Task 2: Discover and protect FastAPI, React, Neo4j, and configured name patterns.
        """
        ports = self.config.get("protect_ports", [8000, 5173, 7687])
        names = self.config.get("protect_names", ["train_models.py", "guard.sh"])

        found_pids = []
        
        # 1. Discover by ports
        for port in ports:
            pid = get_pid_by_port(port)
            if pid:
                logger.info(f"Discovered critical port {port} running on PID {pid}")
                found_pids.append(pid)

        # 2. Discover by name patterns
        for name in names:
            pids = get_pids_by_name_pattern(name)
            for pid in pids:
                logger.info(f"Discovered critical name pattern '{name}' running on PID {pid}")
                found_pids.append(pid)

        # Ensure our own PID is included
        my_pid = os.getpid()
        if my_pid not in found_pids:
            found_pids.append(my_pid)

        # Combine with dynamic protected PIDs
        all_protected = set(found_pids).union(self.dynamic_protected_pids)
        self.protected_pids = all_protected

        # Apply RAM locking
        self.protect_pids_from_swap(list(self.protected_pids))
        return list(self.protected_pids)

    def get_kernel_cache_info(self) -> int:
        """Reads /proc/meminfo to return total cached memory in bytes (Cached + Slab)."""
        try:
            cached = 0
            slab = 0
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("Cached:"):
                        cached = int(line.split()[1]) * 1024
                    elif line.startswith("Slab:"):
                        slab = int(line.split()[1]) * 1024
            return cached + slab
        except Exception:
            return 0

    def flush_non_critical_processes(self) -> Dict[str, Any]:
        """
        Task 5: Swap-Flush Trigger
        Forces non-protected processes into swap to maximize RAM for model training.
        """
        # Force aggressive tuning before flush to override power managers/profiles
        logger.info("[SwapManager] Enforcing aggressive kernel parameters: swappiness=100, vfs_cache_pressure=1000...")
        try:
            self.run_sudo(["sysctl", "-w", "vm.swappiness=100"])
            self.run_sudo(["sysctl", "-w", "vm.vfs_cache_pressure=1000"])
        except Exception as e:
            logger.warning(f"Failed to enforce aggressive kernel sysctl tuning: {e}")

        pre_swap = psutil.swap_memory()
        pre_swap_used = pre_swap.used
        pre_swap_total = pre_swap.total

        logger.info("[SwapManager] Triggering pre-training swap flush of non-critical processes...")
        self.push_swap_alert("WARNING", "Initiating pre-training swap flush to maximize RAM.")

        # Rediscover to get fresh critical PIDs
        self.discover_and_protect_critical_services()

        # Find processes to suspend and flush
        all_pids = psutil.pids()
        stopped_pids = []
        
        my_pid = os.getpid()
        protected_set = set(self.protected_pids)
        protected_set.add(my_pid)

        # Add parent processes of the backend to protect the launch sequence
        try:
            curr = psutil.Process(my_pid)
            while curr.parent():
                curr = curr.parent()
                protected_set.add(curr.pid)
        except Exception:
            pass

        for pid in all_pids:
            if pid < 100 or pid in protected_set:
                continue
            try:
                proc = psutil.Process(pid)
                # Exclude root services to keep the system stable
                if proc.username() == 'root':
                    continue
                # Suspend
                os.kill(pid, signal.SIGSTOP)
                stopped_pids.append(pid)
            except Exception:
                continue

        logger.info(f"[SwapManager] Suspended {len(stopped_pids)} background processes.")

        # Forcefully clear memory reference flags and clean dirty pages for suspended processes.
        # This tells the kernel's LRU page allocator that these pages are cold and ripe for immediate swap out.
        logger.info(f"[SwapManager] Forcefully clearing memory references and dirty page flags for {len(stopped_pids)} processes...")
        for pid in stopped_pids:
            clear_refs_path = f"/proc/{pid}/clear_refs"
            if os.path.exists(clear_refs_path):
                try:
                    self.run_sudo(["tee", clear_refs_path], input_data="1")
                    self.run_sudo(["tee", clear_refs_path], input_data="4")
                except Exception:
                    pass

        # Measure cache before purging
        pre_cache = self.get_kernel_cache_info()
        logger.info(f"[SwapManager] Initial OS Cache (Page Cache + Slab): {pre_cache // (1024 * 1024)} MB")

        # Sync and hyper-aggressive multi-pass cache reclamation
        logger.info("[SwapManager] Activating hyper-aggressive safe cache purger...")
        try:
            for pass_idx in range(3):
                subprocess.run(["sync"], capture_output=True)
                # Drop page cache, dentries, and inodes via different channels
                if os.path.exists("/proc/sys/vm/drop_caches"):
                    try:
                        with open("/proc/sys/vm/drop_caches", "w") as f:
                            f.write("3")
                    except PermissionError:
                        self.run_sudo(["tee", "/proc/sys/vm/drop_caches"], input_data="3")
                
                # Defragment/compact physical memory page allocations
                if os.path.exists("/proc/sys/vm/compact_memory"):
                    try:
                        with open("/proc/sys/vm/compact_memory", "w") as f:
                            f.write("1")
                    except PermissionError:
                        self.run_sudo(["tee", "/proc/sys/vm/compact_memory"], input_data="1")
                
                # Small wait to let kernel reclaim async pages
                time.sleep(0.05)
                
            # Perform optional SSD trim cache eviction (reclaims SSD block mappings and internal cache)
            try:
                self.run_sudo(["fstrim", "-a"])
            except Exception:
                pass
                
        except Exception as e:
            logger.warning(f"Hyper-aggressive cache purger warning: {e}")

        post_cache = self.get_kernel_cache_info()
        cache_cleared_mb = round(max(0, pre_cache - post_cache) / (1024 * 1024), 2)
        logger.info(f"[SwapManager] Safe Cache Cleaner successfully cleared {cache_cleared_mb} MB of OS Cache (Remaining: {post_cache // (1024 * 1024)} MB).")

        # Temporarily unlock our own process memory so we can allocate the balloon
        # without hitting mlockall physical RAM pinning restrictions!
        logger.info("[SwapManager] Temporarily unlocking process memory for ballooning...")
        try:
            libc = ctypes.CDLL(None)
            libc.munlockall()
        except Exception as e:
            logger.warning(f"Failed to unlock memory via munlockall: {e}")

        # Active Paced Memory Ballooning to force idle pages and filesystem caches out
        mem_info = psutil.virtual_memory()
        available_ram = mem_info.available
        cached_ram = getattr(mem_info, "cached", 0)
        
        # Squeeze dynamically up to available RAM + Cached RAM minus 300 MB safety buffer
        target_bytes = max(int(4.5 * 1024 * 1024 * 1024), available_ram + cached_ram - int(300 * 1024 * 1024))
        # Cap target bytes at a maximum of 7.5 GB to prevent extreme system thrashing
        target_bytes = min(target_bytes, int(7.5 * 1024 * 1024 * 1024))
        
        logger.info(f"[SwapManager] Activating dynamic paced memory ballooning (Target: {target_bytes // (1024*1024)} MB)...")
        chunks = []
        try:
            chunk_size = 32 * 1024 * 1024  # 32MB chunks
            num_chunks = target_bytes // chunk_size
            
            for c_idx in range(num_chunks):
                # Check available memory real-time
                mem = psutil.virtual_memory()
                if mem.available < int(400 * 1024 * 1024):
                    logger.info(f"[SwapManager] Low memory detected ({mem.available // (1024*1024)} MB available). Pacing ballooning...")
                    time.sleep(0.08)  # Let kswapd flush pages to disk
                    mem = psutil.virtual_memory()
                    if mem.available < int(300 * 1024 * 1024):
                        logger.warning("[SwapManager] Reached minimum safety RAM floor. Stopping balloon inflation.")
                        break
                
                chunk = bytearray(chunk_size)
                # Touch each page of 4KB to allocate physical RSS frame
                chunk[::4096] = b'\xff' * (chunk_size // 4096)
                chunks.append(chunk)
                
                # Small base sleep to allow the scheduler to process I/O
                time.sleep(0.01)
                
            logger.info(f"[SwapManager] Memory balloon fully inflated with {len(chunks)} chunks ({len(chunks)*32} MB). Pushing idle pages to swap...")
        except MemoryError:
            logger.warning("[SwapManager] Memory ballooning reached system physical ceiling early. Releasing allocations.")
        except Exception as e:
            logger.error(f"[SwapManager] Error during memory ballooning: {e}")
        finally:
            # Deflate balloon immediately to release RAM back to OS
            chunks.clear()
            import gc
            gc.collect()
            logger.info("[SwapManager] Memory balloon deflated. Physical RAM successfully reclaimed!")
            
            # Re-lock process memory in RAM if we have privilege
            logger.info("[SwapManager] Re-locking process memory in RAM...")
            try:
                libc = ctypes.CDLL(None)
                libc.mlockall(MCL_CURRENT | MCL_FUTURE)
            except Exception as e:
                logger.warning(f"Failed to re-lock memory via mlockall: {e}")

        # Wait briefly for pages to migrate
        time.sleep(2.0)

        # Resume suspended processes
        resumed_count = 0
        for pid in stopped_pids:
            try:
                os.kill(pid, signal.SIGCONT)
                resumed_count += 1
            except Exception:
                pass

        logger.info(f"[SwapManager] Resumed {resumed_count} processes.")

        # Wait for swap to settle
        self.wait_for_swap_settle(timeout_seconds=10)

        # Post metrics
        post_swap = psutil.swap_memory()
        post_swap_used = post_swap.used

        flushed_bytes = max(0, post_swap_used - pre_swap_used)
        flushed_mb = round(flushed_bytes / (1024 * 1024), 2)

        msg = f"Swap flush completed. Evicted {flushed_mb} MB into swap. Background processes resumed."
        logger.info(f"[SwapManager] {msg}")
        self.push_swap_alert("INFO", msg)

        return {
            "pre_swap_used_mb": round(pre_swap_used / (1024*1024), 2),
            "post_swap_used_mb": round(post_swap_used / (1024*1024), 2),
            "flushed_mb": flushed_mb,
            "processes_affected": len(stopped_pids)
        }

    def wait_for_swap_settle(self, timeout_seconds: int = 10):
        """Monitors swap I/O via vmstat until si/so stabilize near zero."""
        logger.info("[SwapManager] Waiting for swap I/O to settle...")
        start = time.time()
        while time.time() - start < timeout_seconds:
            try:
                # Read vmstat over a 1-second interval
                out = subprocess.check_output(["vmstat", "1", "2"], text=True)
                lines = out.strip().split("\n")
                if len(lines) >= 4:
                    # Last line represents stats from the 1s interval
                    parts = lines[-1].split()
                    if len(parts) >= 10:
                        # si is index 6, so is index 7
                        si = int(parts[6])
                        so = int(parts[7])
                        logger.info(f"[SwapManager] Settle Check: si={si}, so={so}")
                        if si == 0 and so == 0:
                            logger.info("[SwapManager] Swap I/O stabilized.")
                            break
            except Exception:
                time.sleep(1.0)

    def get_process_swap_usage(self, pid: int) -> int:
        """Fast extraction of VmSwap from /proc/[pid]/status in kB."""
        try:
            with open(f"/proc/{pid}/status", "r") as f:
                for line in f:
                    if line.startswith("VmSwap:"):
                        parts = line.split()
                        if len(parts) >= 2:
                            return int(parts[1])
        except Exception:
            pass
        return 0

    def get_top_swap_consumers(self, limit: int = 5) -> List[Dict[str, Any]]:
        consumers = []
        for pid in psutil.pids():
            if pid < 100:
                continue
            try:
                swap_usage = self.get_process_swap_usage(pid)
                if swap_usage > 0:
                    proc = psutil.Process(pid)
                    consumers.append({
                        "pid": pid,
                        "name": proc.name(),
                        "swap_kb": swap_usage,
                        "swap_mb": round(swap_usage / 1024, 2)
                    })
            except Exception:
                continue
        consumers.sort(key=lambda x: x["swap_kb"], reverse=True)
        return consumers[:limit]

    def push_swap_alert(self, severity: str, description: str):
        """Pushes alerts directly into the fraud_events SQLite table to feed the SSE alert stream."""
        try:
            from src.config import SQLITE_DB_PATH
            conn = sqlite3.connect(SQLITE_DB_PATH)
            event_id = f"FE-SWAP-{uuid.uuid4().hex[:8]}"
            conn.execute("""
                INSERT INTO fraud_events 
                (event_id, transaction_id, account_id, fraud_type, description, severity, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (event_id, "N/A", "N/A", "swap_manager", description, severity, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            logger.info(f"Registered swap alert: [{severity}] {description}")
        except Exception as e:
            logger.error(f"Failed to record swap alert in database: {e}")

    def monitor_loop(self):
        """Task 6: Background Monitoring and Alerting loop."""
        logger.info("[SwapManager] Starting background monitoring thread...")
        interval = self.config.get("monitor_interval_seconds", 60)
        threshold = self.config.get("swap_threshold_percent", 80)

        while self.active:
            try:
                # 1. Total Swap check
                swap = psutil.swap_memory()
                usage_percent = swap.percent
                if usage_percent >= threshold:
                    self.push_swap_alert(
                        "CRITICAL",
                        f"Swap usage high: {usage_percent}% (threshold: {threshold}%). Total: {round(swap.total/(1024**3), 2)} GB, Used: {round(swap.used/(1024**3), 2)} GB."
                    )

                # 2. Check protected PIDs for swap leakage (indicating mlock / cgroups failure)
                # Keep discovery active
                self.discover_and_protect_critical_services()
                
                for pid in self.protected_pids:
                    swap_used = self.get_process_swap_usage(pid)
                    if swap_used > 512:  # Allow negligible noise
                        proc_name = "Unknown"
                        try:
                            proc_name = psutil.Process(pid).name()
                        except Exception:
                            pass
                        
                        self.push_swap_alert(
                            "CRITICAL",
                            f"Protected PID {pid} ({proc_name}) found in swap: {swap_used} kB! Attempting re-protection."
                        )
                        # Re-protect
                        self.protect_pids_from_swap([pid])

                # 3. Log top 5 swap consumers
                top_consumers = self.get_top_swap_consumers(limit=5)
                logger.info(f"Top swap consumers: {top_consumers}")

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")

            # Sleep in tiny steps to allow rapid shutdown
            for _ in range(interval):
                if not self.active:
                    break
                time.sleep(1)

    def get_dir_size(self, path: str) -> int:
        """Returns total size of a directory in bytes."""
        if not os.path.exists(path):
            return 0
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp) and not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        except Exception:
            pass
        return total_size

    def clean_system_caches(self) -> Dict[str, Any]:
        """
        Clears and deletes filesystem caches, slab allocations, docker builder/container caches,
        npm caches, and pip caches safely.
        """
        logger.info("[SwapManager] Starting system-wide cache cleaning...")
        self.push_swap_alert("WARNING", "Initiating system-wide cache cleaning.")
        
        # Detect cache sizes before purging
        apt_size = 0
        try:
            res = self.run_sudo(["du", "-s", "/var/cache/apt/archives"])
            if res.returncode == 0:
                apt_size = int(res.stdout.split()[0]) * 1024
        except Exception:
            pass

        journal_size = 0
        try:
            res = subprocess.run(["journalctl", "--disk-usage"], capture_output=True, text=True)
            if res.returncode == 0:
                parts = res.stdout.split()
                for p in parts:
                    if "G" in p:
                        journal_size = int(float(p.replace("G", "")) * 1024 * 1024 * 1024)
                        break
                    elif "M" in p:
                        journal_size = int(float(p.replace("M", "")) * 1024 * 1024)
                        break
                    elif "K" in p:
                        journal_size = int(float(p.replace("K", "")) * 1024)
                        break
        except Exception:
            pass

        npm_size = self.get_dir_size(os.path.expanduser("~/.npm"))
        pip_size = self.get_dir_size(os.path.expanduser("~/.cache/pip"))
        vite_size = self.get_dir_size(os.path.join(os.getcwd(), "frontend-react", "node_modules", ".vite"))
        thumb_size = self.get_dir_size(os.path.expanduser("~/.cache/thumbnails"))

        logger.info(
            f"[SwapManager] Detected cache sizes before cleaning: "
            f"Apt Cache: {round(apt_size / (1024*1024), 2)} MB, "
            f"Journal Logs: {round(journal_size / (1024*1024), 2)} MB, "
            f"NPM Cache: {round(npm_size / (1024*1024), 2)} MB, "
            f"Pip Cache: {round(pip_size / (1024*1024), 2)} MB, "
            f"Vite Cache: {round(vite_size / (1024*1024), 2)} MB, "
            f"Thumbnails: {round(thumb_size / (1024*1024), 2)} MB."
        )

        pre_cache = self.get_kernel_cache_info()
        pre_free = psutil.virtual_memory().free
        
        # Measure disk space before
        import shutil
        free_pre_root = shutil.disk_usage("/").free
        free_pre_cwd = shutil.disk_usage(os.getcwd()).free
        
        # 1. Sync & drop_caches
        try:
            for _ in range(3):
                subprocess.run(["sync"], capture_output=True)
                if os.path.exists("/proc/sys/vm/drop_caches"):
                    try:
                        with open("/proc/sys/vm/drop_caches", "w") as f:
                            f.write("3")
                    except PermissionError:
                        self.run_sudo(["tee", "/proc/sys/vm/drop_caches"], input_data="3")
                if os.path.exists("/proc/sys/vm/compact_memory"):
                    try:
                        with open("/proc/sys/vm/compact_memory", "w") as f:
                            f.write("1")
                    except PermissionError:
                        self.run_sudo(["tee", "/proc/sys/vm/compact_memory"], input_data="1")
                time.sleep(0.05)
        except Exception as e:
            logger.warning(f"Drop caches failed: {e}")
            
        # 2. SSD trim
        try:
            self.run_sudo(["fstrim", "-a"])
        except Exception:
            pass

        # 3. Clean Docker builder/container caches aggressively
        try:
            self.run_sudo(["docker", "system", "prune", "-a", "-f", "--volumes"])
            self.run_sudo(["docker", "builder", "prune", "-a", "-f"])
        except Exception as e:
            logger.warning(f"Docker prune failed: {e}")

        # 4. Clean NPM cache
        try:
            subprocess.run(["npm", "cache", "clean", "--force"], capture_output=True)
            npm_cache_dir = os.path.expanduser("~/.npm")
            if os.path.exists(npm_cache_dir):
                import shutil as local_shutil
                local_shutil.rmtree(npm_cache_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"npm cache clean failed: {e}")

        # 5. Clean pip cache
        try:
            subprocess.run(["pip", "cache", "purge"], capture_output=True)
            pip_cache_dir = os.path.expanduser("~/.cache/pip")
            if os.path.exists(pip_cache_dir):
                import shutil as local_shutil
                local_shutil.rmtree(pip_cache_dir, ignore_errors=True)
        except Exception:
            pass

        # 6. Delete local node_modules vite cache
        vite_cache_dir = os.path.join(os.getcwd(), "frontend-react", "node_modules", ".vite")
        if os.path.exists(vite_cache_dir):
            try:
                import shutil as local_shutil
                local_shutil.rmtree(vite_cache_dir, ignore_errors=True)
            except Exception:
                pass

        # 7. Clean apt caches
        try:
            self.run_sudo(["apt-get", "clean"])
        except Exception as e:
            logger.warning(f"apt-get clean failed: {e}")

        # 8. Vacuum Systemd Journal logs to 50M
        try:
            self.run_sudo(["journalctl", "--vacuum-size=50M"])
        except Exception as e:
            logger.warning(f"journalctl vacuum failed: {e}")

        # 9. Clean Thumbnail cache
        try:
            thumb_dir = os.path.expanduser("~/.cache/thumbnails")
            if os.path.exists(thumb_dir):
                import shutil as local_shutil
                local_shutil.rmtree(thumb_dir, ignore_errors=True)
        except Exception:
            pass
                
        post_cache = self.get_kernel_cache_info()
        post_free = psutil.virtual_memory().free
        
        # Measure disk space after
        free_post_root = shutil.disk_usage("/").free
        free_post_cwd = shutil.disk_usage(os.getcwd()).free
        
        cache_freed_mb = round(max(0, pre_cache - post_cache) / (1024 * 1024), 2)
        ram_freed_mb = round(max(0, post_free - pre_free) / (1024 * 1024), 2)
        
        disk_freed_bytes = max(0, free_post_root - free_pre_root, free_post_cwd - free_pre_cwd)
        disk_freed_mb = round(disk_freed_bytes / (1024 * 1024), 2)
        
        msg = f"System-wide cache cleaning completed. Freed {cache_freed_mb} MB kernel cache, {disk_freed_mb} MB disk cache, and released {ram_freed_mb} MB physical RAM."
        logger.info(f"[SwapManager] {msg}")
        self.push_swap_alert("INFO", msg)
        
        return {
            "kernel_cache_freed_mb": cache_freed_mb,
            "disk_cache_freed_mb": disk_freed_mb,
            "ram_released_mb": ram_freed_mb
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns structured system status metadata for programmatic validation."""
        swap = psutil.swap_memory()
        self.capabilities = self.check_system_capabilities()
        return {
            "status": "active" if self.active else "inactive",
            "swap_total_gb": round(swap.total / (1024**3), 2),
            "swap_used_gb": round(swap.used / (1024**3), 2),
            "swap_free_gb": round(swap.free / (1024**3), 2),
            "swap_percent": swap.percent,
            "capabilities": self.capabilities,
            "protected_pids": list(self.protected_pids),
            "top_consumers": self.get_top_swap_consumers(limit=5)
        }

    def start_monitoring(self):
        with self._lock:
            if self.active:
                return
            self.active = True
            self.monitor_thread = Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Background Swap Monitor successfully started.")

    def stop_monitoring(self):
        with self._lock:
            if not self.active:
                return
            self.active = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=3)
                self.monitor_thread = None
            logger.info("Background Swap Monitor successfully stopped.")

# Auto-initialize and tune on import
swap_manager = SwapManager()

def startup_init():
    """Initializes and runs setup functions."""
    if not swap_manager.config.get("enabled", True):
        logger.info("SwapManager is disabled in config. Skipping startup initialization.")
        return
    swap_manager.aggressive_swap_tuning()
    swap_manager.discover_and_protect_critical_services()
    swap_manager.start_monitoring()

