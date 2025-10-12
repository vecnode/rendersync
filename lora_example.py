# MATERIALS TO READ AND INSPIRATION

#!/usr/bin/env python3
"""
ModelTrainer TUI — Textual + PyTorch + Ignite

What changed in this rev:
- Kept your UI (Local / Models / Training) with the sidebar-driven Local tab.
- Added an **Ignite-powered Training tab** (still all in one file) that can:
  • Capture a training config (dataset, model module, LoRA rank/alpha, LR, steps, AMP, etc.)
  • Generate a reusable training script:  ~/.loralab/ignite_train.py
  • Launch the script locally (single or multi-GPU via torchrun) and stream logs

Design goals:
- Stay generic for SD/Hunyuan/GANs/LLMs while focusing first on *image* models.
- The generated script expects your **model module** to provide three functions:
    def get_model(args) -> nn.Module
    def get_dataloaders(args) -> tuple[DataLoader, Optional[DataLoader]]
    def loss_fn(model, batch, args) -> torch.Tensor
  …so you can plug-in Stable Diffusion UNet or any custom image model.
- LoRA injection is built-in (pure PyTorch) and is applied to layers by name patterns.

"""



from __future__ import annotations
import os
import io
import sys
import json
import shutil
import platform
import ctypes
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Iterable

from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, Static, Input, Button, DirectoryTree, TabbedContent, TabPane,
    Label, ListView, ListItem, DataTable, Switch
)
from textual.containers import Vertical, Horizontal, Container
from textual.reactive import reactive


# Optional perf/OS helpers
try:
    import psutil  # type: ignore
except Exception:
    psutil = None  # type: ignore

try:
    import torch  # type: ignore
except Exception:
    torch = None  # type: ignore

APP_NAME = "trainlab"
# Use local environment variables if set, otherwise fall back to home directory
CONFIG_DIR = Path(os.environ.get("TRAINLAB_CONFIG_DIR", str(Path.home() / f".{APP_NAME}")))
CONFIG_PATH = CONFIG_DIR / "config.json"
DEFAULT_MODELS_ROOT = Path(os.environ.get("TRAINLAB_MODELS_ROOT", str(Path.cwd() / "models")))
TRAIN_SCRIPT_PATH = CONFIG_DIR / "ignite_train.py"
JOB_CFG_PATH = CONFIG_DIR / "job.json"


# ---------------- Config helpers ----------------
def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            pass
    return {
        "models_root": str(DEFAULT_MODELS_ROOT),
        "last_job": {}
    }


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


# ---------------- System info helpers ----------------
def human_bytes(n: Optional[int]) -> str:
    if n is None:
        return "?"
    step = 1024.0
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    v = float(n)
    for u in units:
        if v < step:
            return f"{v:,.1f} {u}"
        v /= step
    return f"{v:,.1f} EiB"


def get_total_ram_bytes() -> Optional[int]:
    if psutil is not None:
        try:
            return int(psutil.virtual_memory().total)
        except Exception:
            pass
    try:
        if platform.system() == "Linux":
            for line in Path("/proc/meminfo").read_text().splitlines():
                if line.startswith("MemTotal:"):
                    kB = int(line.split()[1])
                    return kB * 1024
    except Exception:
        pass
    if platform.system() == "Darwin":
        try:
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"]).strip()
            return int(out)
        except Exception:
            pass
    if platform.system() == "Windows":
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return int(stat.ullTotalPhys)
        except Exception:
            pass
    return None


def get_cpu_name() -> str:
    try:
        if platform.system() == "Windows":
            return platform.processor() or "Unknown CPU"
        elif platform.system() == "Darwin":
            return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
        else:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.platform()


def get_gpu_info() -> list[dict]:
    gpus: list[dict] = []
    if torch is None:
        return gpus
    try:
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                total = getattr(props, "total_memory", 0)
                free = used = None
                try:
                    free, total_rt = torch.cuda.mem_get_info(i)
                    used = total_rt - free
                    total = total_rt
                except Exception:
                    pass
                gpus.append({
                    "index": i,
                    "name": props.name,
                    "total": int(total) if total is not None else None,
                    "free": int(free) if free is not None else None,
                    "used": int(used) if used is not None else None,
                    "sm": f"{getattr(props, 'major', '?')}.{getattr(props, 'minor', '?')}",
                })
        elif getattr(torch, "backends", None) and getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            gpus.append({"index": 0, "name": "Apple MPS", "total": None, "free": None, "used": None, "sm": "-"})
    except Exception:
        pass
    return gpus


# ---------------- LoRA (pure PyTorch) ----------------
import torch.nn as nn
from torch import Tensor

class LoRALinear(nn.Module):
    def __init__(self, base: nn.Linear, r: int = 8, alpha: int = 16):
        super().__init__()
        assert isinstance(base, nn.Linear)
        self.base = base
        for p in self.base.parameters():
            p.requires_grad = False
        self.r = r
        self.alpha = alpha
        self.scaling = alpha / max(1, r)
        self.lora_A = nn.Linear(base.in_features, r, bias=False)
        self.lora_B = nn.Linear(r, base.out_features, bias=False)
        nn.init.kaiming_uniform_(self.lora_A.weight, a=5**0.5)
        nn.init.zeros_(self.lora_B.weight)

    def forward(self, x: Tensor) -> Tensor:
        return self.base(x) + self.lora_B(self.lora_A(x)) * self.scaling


class LoRAConv2d(nn.Module):
    def __init__(self, base: nn.Conv2d, r: int = 8, alpha: int = 16):
        super().__init__()
        assert isinstance(base, nn.Conv2d)
        self.base = base
        for p in self.base.parameters():
            p.requires_grad = False
        self.r, self.alpha = r, alpha
        self.scaling = alpha / max(1, r)
        Cin, Cout = base.in_channels, base.out_channels
        kH, kW = base.kernel_size
        self.A = nn.Conv2d(Cin, self.r, kernel_size=(kH, kW), padding=base.padding, stride=base.stride, bias=False, groups=1)
        self.B = nn.Conv2d(self.r, Cout, kernel_size=1, bias=False)
        nn.init.kaiming_uniform_(self.A.weight, a=5**0.5)
        nn.init.zeros_(self.B.weight)

    def forward(self, x: Tensor) -> Tensor:
        return self.base(x) + self.B(self.A(x)) * self.scaling


def inject_lora(module: nn.Module, r=8, alpha=16, targets=("attn", "to_q", "to_k", "to_v", "proj", "fc", "conv")):
    """Wrap selected Linear/Conv2d submodules with LoRA adapters by name-match."""
    for name, child in list(module.named_children()):
        lname = name.lower()
        if isinstance(child, nn.Linear) and any(t in lname for t in targets):
            setattr(module, name, LoRALinear(child, r=r, alpha=alpha))
        elif isinstance(child, nn.Conv2d) and any(t in lname for t in targets):
            setattr(module, name, LoRAConv2d(child, r=r, alpha=alpha))
        else:
            inject_lora(child, r=r, alpha=alpha, targets=targets)


def lora_parameters(module: nn.Module):
    for n,p in module.named_parameters():
        if p.requires_grad:
            yield p


# ---------------- Widgets: Local (unchanged look) ----------------
class HBar(Static):
    def __init__(self, title: str) -> None:
        super().__init__(f"[b]{title}[/b]", classes="hbar")


class SectionItem(ListItem):
    def __init__(self, key: str, label: str) -> None:
        super().__init__(Label(label))
        self.key = key


class LocalDetail(Container):
    section: reactive[str] = reactive("overview")
    _cache: dict = {}
    _last_update: float = 0

    def on_mount(self) -> None:  # type: ignore[override]
        self.dt = DataTable(id="detail-table")
        self.mount(self.dt)
        # Load initial data
        self.refresh_section()

    def refresh_section(self) -> None:
        import time
        current_time = time.time()
        
        # Cache results for 5 seconds to reduce system calls
        cache_key = f"{self.section}_{int(current_time // 5)}"
        
        if cache_key in self._cache:
            data = self._cache[cache_key]
        else:
            data = []
            if self.section == "overview":
                data = self._overview_rows()
            elif self.section == "cpu":
                data = self._cpu_rows()
            elif self.section == "mem":
                data = self._mem_rows()
            elif self.section == "gpu":
                data = self._gpu_rows()
            elif self.section == "disk":
                data = self._disk_rows()
            elif self.section == "net":
                data = self._net_rows()
            
            # Cache the result
            self._cache[cache_key] = data
            # Clean old cache entries less frequently
            if len(self._cache) > 10:  # Only clean when cache gets large
                self._clean_cache()
        
        self.dt.clear(columns=True)
        self.dt.add_columns("Property", "Value")
        for k, v in data:
            self.dt.add_row(k, v)
    
    def _clean_cache(self) -> None:
        """Clean old cache entries to prevent memory leaks"""
        import time
        current_time = time.time()
        cutoff = int(current_time // 5) - 3  # Keep only last 3 cache periods (15 seconds)
        keys_to_remove = [k for k in self._cache.keys() if int(k.split('_')[-1]) < cutoff]
        for key in keys_to_remove:
            del self._cache[key]

    def _overview_rows(self) -> list[tuple[str, str]]:
        rows = [
            ("OS", f"{platform.system()} {platform.release()}"),
            ("Python", platform.python_version()),
        ]
        if torch is not None:
            rows += [
                ("PyTorch", getattr(torch, "__version__", "?")),
                ("CUDA available", str(bool(getattr(torch.cuda, "is_available", lambda: False)()))),
            ]
            cuda_v = getattr(getattr(torch, "version", None), "cuda", None)
            rows.append(("CUDA version", str(cuda_v or "n/a")))
        else:
            rows.append(("PyTorch", "not installed / failed to import"))
        rows += [
            ("CPU", get_cpu_name()),
            ("Cores (logical)", str(os.cpu_count() or 0)),
            ("RAM total", human_bytes(get_total_ram_bytes())),
        ]
        gpus = get_gpu_info()
        rows.append(("GPU count", str(len(gpus))))
        if gpus:
            rows.append(("GPU 0", f"{gpus[0]['name']} (SM {gpus[0]['sm']})"))
        return rows

    def _cpu_rows(self) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = [("CPU", get_cpu_name()), ("Cores (logical)", str(os.cpu_count() or 0))]
        if psutil is not None:
            try:
                # Use interval=None for instant, non-blocking CPU reading
                per = psutil.cpu_percent(interval=None, percpu=True)
                # Limit to first 8 cores to avoid UI clutter
                rows += [(f"CPU {i}", f"{p}%") for i, p in enumerate(per[:8])]
                if len(per) > 8:
                    rows.append((f"CPU 8-{len(per)-1}", f"{sum(per[8:])/len(per[8:]):.1f}% avg"))
            except Exception:
                pass
        return rows

    def _mem_rows(self) -> list[tuple[str, str]]:
        if psutil is not None:
            try:
                vm = psutil.virtual_memory()
                sm = psutil.swap_memory()
                return [
                    ("RAM total", human_bytes(vm.total)),
                    ("RAM used", human_bytes(vm.used)),
                    ("RAM free", human_bytes(vm.available)),
                    ("Swap total", human_bytes(sm.total)),
                    ("Swap used", human_bytes(sm.used)),
                ]
            except Exception:
                pass
        total = get_total_ram_bytes()
        return [("RAM total", human_bytes(total))]

    def _gpu_rows(self) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        try:
            gpus = get_gpu_info()
            for g in gpus:
                rows += [
                    (f"GPU {g['index']} name", g['name']),
                    (f"GPU {g['index']} SM", g['sm']),
                    (f"GPU {g['index']} VRAM used", human_bytes(g.get("used"))),
                    (f"GPU {g['index']} VRAM free", human_bytes(g.get("free"))),
                    (f"GPU {g['index']} VRAM total", human_bytes(g.get("total"))),
                ]
            if not rows:
                rows.append(("GPU", "No CUDA/MPS detected"))
        except Exception:
            rows.append(("GPU", "Error reading GPU info"))
        return rows

    def _disk_rows(self) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        cfg = load_config()
        mr = Path(cfg.get("models_root", str(DEFAULT_MODELS_ROOT))).expanduser()
        try:
            du = shutil.disk_usage(mr)
            rows += [
                ("Models root", str(mr)),
                ("Models total", human_bytes(du.total)),
                ("Models used", human_bytes(du.used)),
                ("Models free", human_bytes(du.free)),
            ]
        except Exception:
            rows.append(("Models root", str(mr)))
        if psutil is not None:
            try:
                # Only show main system partitions to reduce system calls
                main_partitions = ["/", "/home", "/tmp", "/var"]
                for p in psutil.disk_partitions(all=False):
                    if p.mountpoint in main_partitions:
                        try:
                            usage = psutil.disk_usage(p.mountpoint)
                            rows += [
                                (f"Disk {p.device}", p.mountpoint),
                                (f"{p.mountpoint} total", human_bytes(usage.total)),
                                (f"{p.mountpoint} used", human_bytes(usage.used)),
                                (f"{p.mountpoint} free", human_bytes(usage.free)),
                            ]
                        except Exception:
                            pass
            except Exception:
                pass
        return rows

    def _net_rows(self) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        if psutil is not None:
            try:
                addrs = psutil.net_if_addrs()
                stats = psutil.net_io_counters(pernic=True)
                # Only show main network interfaces to reduce clutter
                main_interfaces = ["lo", "eth0", "wlan0", "en0", "en1"]
                for nic, infos in addrs.items():
                    if nic in main_interfaces or any(nic.startswith(prefix) for prefix in ["eth", "wlan", "en", "wl"]):
                        rows.append((f"Interface", nic))
                        for info in infos:
                            if getattr(info, 'address', None):
                                rows.append((f"  addr", info.address))
                        s = stats.get(nic)
                        if s:
                            rows += [
                                ("  bytes sent", human_bytes(int(s.bytes_sent))),
                                ("  bytes recv", human_bytes(int(s.bytes_recv))),
                            ]
            except Exception:
                pass
        else:
            rows.append(("Network", "Install psutil for details"))
        return rows


class LocalPane(Vertical):
    selected: reactive[str] = reactive("overview")

    def compose(self) -> ComposeResult:  # type: ignore[override]
        yield HBar("System Explorer")
        with Horizontal():
            with Vertical(classes="sidebar"):
                with ListView(id="sections"):
                    yield SectionItem("overview", "Overview")
                    yield SectionItem("cpu", "CPU")
                    yield SectionItem("mem", "Memory")
                    yield SectionItem("gpu", "GPUs")
                    yield SectionItem("disk", "Disks")
                    yield SectionItem("net", "Network")
            with Vertical(classes="detail"):
                yield Static("Property/Value", classes="table-header")
                yield LocalDetail(id="detail")

    def on_list_view_selected(self, event: ListView.Selected) -> None:  # type: ignore[override]
        item = event.item
        if isinstance(item, SectionItem):
            self.selected = item.key
            detail = self.query_one("#detail", LocalDetail)
            detail.section = item.key
            detail.refresh_section()
    



# ---------------- Models tab ----------------
class ModelsPane(Vertical):
    models_root: reactive[Path] = reactive(Path(load_config().get("models_root", str(DEFAULT_MODELS_ROOT))).expanduser())

    def compose(self) -> ComposeResult:  # type: ignore[override]
        yield HBar("Model Root")
        row = Horizontal(
            Input(str(self.models_root), id="root_input"),
            Button("Save", id="save_root"),
            classes="row",
        )
        self.models_root.mkdir(parents=True, exist_ok=True)
        yield row
        yield DirectoryTree(str(self.models_root), id="tree")

    def on_button_pressed(self, event: Button.Pressed) -> None:  # type: ignore[override]
        if event.button.id == "save_root":
            self._save_from_input()

    def on_input_submitted(self, event: Input.Submitted) -> None:  # type: ignore[override]
        if event.input.id == "root_input":
            self._save_from_input()

    def _save_from_input(self) -> None:
        inp = self.query_one("#root_input", Input)
        new_path = Path(inp.value).expanduser()
        try:
            new_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.app.notify(f"Failed to create directory: {e}", severity="error")
            return
        self.models_root = new_path
        self.query_one("#tree", DirectoryTree).path = str(self.models_root)
        cfg = load_config(); cfg["models_root"] = str(self.models_root); save_config(cfg)
        self.app.notify("Models root updated.")


# ---------------- Training tab (Ignite) ----------------
class TrainingPane(Vertical):
    running: reactive[bool] = reactive(False)
    proc: Optional[subprocess.Popen] = None

    def on_mount(self) -> None:  # type: ignore[override]
        """Initialize the training pane."""
        pass
    
    def on_unmount(self) -> None:  # type: ignore[override]
        """Clean up when the pane is unmounted."""
        if self.proc and self.running:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
            except Exception:
                pass
            finally:
                self.proc = None
                self.running = False

    def compose(self) -> ComposeResult:  # type: ignore[override]
        yield HBar("Training • Ignite")
        # Config row 1
        with Horizontal(classes="row"):
            yield Label("Dataset root:")
            yield Input("/path/to/images", id="ds_root")
            yield Label("Output dir:")
            out = str((CONFIG_DIR / "runs").expanduser())
            yield Input(out, id="out_dir")
        # Config row 2
        with Horizontal(classes="row"):
            yield Label("Model module (import path):")
            yield Input("my_model_module", id="model_mod")
            yield Label("Model fn:")
            yield Input("get_model", id="model_fn")
        # Config row 3 (LoRA)
        with Horizontal(classes="row"):
            yield Label("Use LoRA:")
            yield Switch(value=True, id="use_lora")
            yield Label("rank r:")
            yield Input("8", id="lora_r")
            yield Label("alpha:")
            yield Input("16", id="lora_alpha")
            yield Label("targets (comma):")
            yield Input("attn,proj,fc,conv", id="lora_targets")
        # Config row 4 (optim)
        with Horizontal(classes="row"):
            yield Label("LR:")
            yield Input("1e-4", id="lr")
            yield Label("Batch:")
            yield Input("2", id="batch")
            yield Label("Grad Accum:")
            yield Input("8", id="grad_accum")
            yield Label("Steps:")
            yield Input("2000", id="steps")
        # Config row 5 (engine)
        with Horizontal(classes="row"):
            yield Label("AMP:")
            yield Switch(value=True, id="amp")
            yield Label("compile():")
            yield Switch(value=True, id="compile")
            yield Label("nproc per node:")
            yield Input("1", id="nproc")
        # Buttons
        with Horizontal(classes="row"):
            yield Button("Save job", id="save_job")
            yield Button("Write script", id="write_script")
            yield Button("Launch (local)", id="launch_local")
            yield Button("Stop", id="stop", disabled=True)
        yield Static("", id="log")

    # -------- helpers --------
    def _collect_job(self) -> dict:
        j = {}
        j["dataset_root"] = self.query_one("#ds_root", Input).value
        j["output_dir"] = self.query_one("#out_dir", Input).value
        j["model_module"] = self.query_one("#model_mod", Input).value
        j["model_fn"] = self.query_one("#model_fn", Input).value
        j["use_lora"] = self.query_one("#use_lora", Switch).value
        j["lora_r"] = int(self.query_one("#lora_r", Input).value)
        j["lora_alpha"] = int(self.query_one("#lora_alpha", Input).value)
        j["lora_targets"] = [s.strip() for s in self.query_one("#lora_targets", Input).value.split(",") if s.strip()]
        j["lr"] = float(self.query_one("#lr", Input).value)
        j["batch_size"] = int(self.query_one("#batch", Input).value)
        j["grad_accum"] = int(self.query_one("#grad_accum", Input).value)
        j["max_steps"] = int(self.query_one("#steps", Input).value)
        j["amp"] = self.query_one("#amp", Switch).value
        j["compile"] = self.query_one("#compile", Switch).value
        j["nproc_per_node"] = int(self.query_one("#nproc", Input).value)
        return j

    def _save_job(self) -> None:
        job = self._collect_job()
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        JOB_CFG_PATH.write_text(json.dumps(job, indent=2))
        cfg = load_config(); cfg["last_job"] = job; save_config(cfg)
        self.app.notify("Job saved → ~/.loralab/job.json")

    def _write_script(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        TRAIN_SCRIPT_PATH.write_text(self._ignite_script_text())
        self.app.notify("Wrote ~/.loralab/ignite_train.py")


    
    def _append_log(self, text: str) -> None:
        """Append log messages directly to the UI."""
        try:
            log_widget = self.query_one("#log", Static)
            current_text = log_widget.renderable
            if current_text:
                log_widget.update(f"{current_text}\n{text}")
            else:
                log_widget.update(text)
        except Exception:
            pass  # Widget might not exist yet

    def _run_training(self, cmd: list[str], cwd: Optional[str] = None) -> None:
        """Run training command synchronously."""
        try:
            self.running = True
            self._append_log(f"$ {' '.join(cmd)}")
            
            # Start the process
            self.proc = subprocess.Popen(
                cmd, 
                cwd=cwd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                bufsize=1, 
                universal_newlines=True
            )
            
            # Stream output
            if self.proc.stdout:
                for line in self.proc.stdout:
                    if not self.running:  # Check if stopped
                        break
                    self._append_log(line.rstrip())
            
            # Wait for process completion
            rc = self.proc.wait()
            self._append_log(f"[process exited {rc}]")
            
        except Exception as e:
            self._append_log(f"[error] {e}")
        finally:
            # Always clean up
            self.running = False
            self.proc = None
    


    # -------- events --------
    def on_button_pressed(self, event: Button.Pressed) -> None:  # type: ignore[override]
        if event.button.id == "save_job":
            self._save_job()
        elif event.button.id == "write_script":
            self._write_script()
        elif event.button.id == "launch_local":
            self._save_job()
            job = json.loads(JOB_CFG_PATH.read_text())
            nproc = int(job.get("nproc_per_node", 1))
            cmd = [sys.executable, str(TRAIN_SCRIPT_PATH), "--config", str(JOB_CFG_PATH)]
            if nproc > 1:
                cmd = ["torchrun", f"--nproc_per_node={nproc}", str(TRAIN_SCRIPT_PATH), "--config", str(JOB_CFG_PATH)]
            self._run_training(cmd)
        elif event.button.id == "stop":
            if self.proc and self.running:
                try:
                    self.running = False
                    self.proc.terminate()
                    # Give it a moment to terminate gracefully
                    try:
                        self.proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        # Force kill if it doesn't terminate gracefully
                        self.proc.kill()
                        self.proc.wait()
                except Exception:
                    pass

    # -------- generated training script --------
    def _ignite_script_text(self) -> str:
        return f'''#!/usr/bin/env python3
# Auto-generated by LoRA Lab TUI (Ignite)
import os, json, argparse, importlib
from pathlib import Path
import torch
import torch.nn as nn
from torch.cuda.amp import autocast, GradScaler
from ignite.engine import Engine, Events
from ignite.handlers import ModelCheckpoint, TerminateOnNan
from ignite.contrib.handlers import ProgressBar
from ignite.metrics import RunningAverage
from ignite.distributed import idist

# ---- LoRA adapters (same as TUI) ----
{LoRALinear.__code__.co_consts[0] if False else ''}
# We embed simplified versions to avoid importing the TUI file.
class LoRALinear(nn.Module):
    def __init__(self, base: nn.Linear, r: int = 8, alpha: int = 16):
        super().__init__(); self.base=base
        for p in self.base.parameters(): p.requires_grad=False
        self.r=r; self.scaling=alpha/max(1,r)
        self.lora_A=nn.Linear(base.in_features,r,bias=False)
        self.lora_B=nn.Linear(r,base.out_features,bias=False)
        nn.init.kaiming_uniform_(self.lora_A.weight, a=5**0.5); nn.init.zeros_(self.lora_B.weight)
    def forward(self,x): return self.base(x) + self.lora_B(self.lora_A(x))*self.scaling
class LoRAConv2d(nn.Module):
    def __init__(self, base: nn.Conv2d, r: int = 8, alpha: int = 16):
        super().__init__(); self.base=base
        for p in self.base.parameters(): p.requires_grad=False
        self.r=r; self.scaling=alpha/max(1,r)
        kH,kW=base.kernel_size; Cin=base.in_channels; Cout=base.out_channels
        self.A=nn.Conv2d(Cin,self.r,kernel_size=(kH,kW),padding=base.padding,stride=base.stride,bias=False)
        self.B=nn.Conv2d(self.r,Cout,kernel_size=1,bias=False)
        nn.init.kaiming_uniform_(self.A.weight, a=5**0.5); nn.init.zeros_(self.B.weight)
    def forward(self,x): return self.base(x) + self.B(self.A(x))*self.scaling

def inject_lora(module: nn.Module, r=8, alpha=16, targets=("attn","to_q","to_k","to_v","proj","fc","conv")):
    for name, child in list(module.named_children()):
        lname=name.lower()
        if isinstance(child, nn.Linear) and any(t in lname for t in targets):
            setattr(module,name,LoRALinear(child,r,alpha))
        elif isinstance(child, nn.Conv2d) and any(t in lname for t in targets):
            setattr(module,name,LoRAConv2d(child,r,alpha))
        else:
            inject_lora(child,r,alpha,targets)

def lora_parameters(module: nn.Module):
    for n,p in module.named_parameters():
        if p.requires_grad: yield p


def build_args():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config', type=str, default='')
    # Job fields
    ap.add_argument('--dataset_root', type=str, default='.')
    ap.add_argument('--output_dir', type=str, default='./runs')
    ap.add_argument('--model_module', type=str, default='my_model_module')
    ap.add_argument('--model_fn', type=str, default='get_model')
    ap.add_argument('--use_lora', action='store_true')
    ap.add_argument('--lora_r', type=int, default=8)
    ap.add_argument('--lora_alpha', type=int, default=16)
    ap.add_argument('--lora_targets', type=str, default='attn,proj,fc,conv')
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--batch_size', type=int, default=2)
    ap.add_argument('--grad_accum', type=int, default=8)
    ap.add_argument('--max_steps', type=int, default=2000)
    ap.add_argument('--amp', action='store_true')
    ap.add_argument('--compile', action='store_true')
    args=ap.parse_args()
    if args.config and Path(args.config).exists():
        cfg=json.loads(Path(args.config).read_text())
        for k,v in cfg.items():
            if hasattr(args,k): setattr(args,k,v)
    return args


def main():
    args=build_args()
    output_dir=Path(args.output_dir); output_dir.mkdir(parents=True, exist_ok=True)

    # Launch under Ignite distributed context (works for CPU/CUDA, single/multi-GPU)
    with idist.Parallel(backend="nccl" if torch.cuda.is_available() else "gloo") as p:
        device=idist.device()
        rank=idist.get_rank()
        # Dynamically import your model & data hooks
        mod=importlib.import_module(args.model_module)
        get_model=getattr(mod, args.model_fn)
        get_dataloaders=getattr(mod, 'get_dataloaders')
        loss_fn=getattr(mod, 'loss_fn')

        model=get_model(args)
        if args.compile and hasattr(torch, 'compile'):
            try: model=torch.compile(model)
            except Exception: pass
        if args.use_lora:
            inject_lora(model, r=args.lora_r, alpha=args.lora_alpha, targets=tuple(t.strip() for t in args.lora_targets.split(',')))
        model=idist.auto_model(model)

        # Only train LoRA params if enabled, otherwise all params
        params=list(lora_parameters(model)) if args.use_lora else list(model.parameters())
        opt=torch.optim.AdamW(params, lr=args.lr)
        opt=idist.auto_optim(opt)
        scaler=GradScaler(enabled=args.amp)

        train_loader, val_loader = get_dataloaders(args)
        train_loader=idist.auto_dataloader(train_loader, batch_size=args.batch_size, shuffle=True)
        if val_loader is not None:
            val_loader=idist.auto_dataloader(val_loader, batch_size=max(1,args.batch_size))

        step_state={'accum':0, 'loss_accum':0.0}

        def train_step(engine, batch):
            model.train(); opt.zero_grad(set_to_none=True)
            with autocast(enabled=args.amp):
                loss=loss_fn(model, batch, args)
            scaler.scale(loss).backward()
            scaler.step(opt); scaler.update()
            return float(loss.detach().item())

        trainer=Engine(train_step)
        RunningAverage(output_transform=lambda out: out).attach(trainer, 'loss')
        TerminateOnNan().attach(trainer)
        pbar=ProgressBar(persist=True);
        if rank==0: pbar.attach(trainer, metric_names=['loss'])

        @trainer.on(Events.ITERATION_COMPLETED)
        def save_periodic(engine):
            i=engine.state.iteration
            if i % 500 == 0 and rank==0:
                ckpt={'model': model.state_dict(), 'opt': opt.state_dict(), 'it': i}
                torch.save(ckpt, output_dir/f"ckpt_{i}.pt")
            if i >= args.max_steps:
                engine.terminate()

        # Optional: simple evaluate hook if provided
        if val_loader is not None:
            def eval_step(engine, batch):
                model.eval()
                with torch.no_grad(), autocast(enabled=args.amp):
                    loss=loss_fn(model, batch, args)
                return float(loss.detach().item())
            evaluator=Engine(eval_step)
            RunningAverage(output_transform=lambda out: out).attach(evaluator, 'val_loss')
            @trainer.on(Events.EPOCH_COMPLETED)
            def run_eval(engine):
                evaluator.run(val_loader)
                if rank==0:
                    vl=evaluator.state.metrics.get('val_loss')
                    print(f"val_loss: {vl}")

        # Kick off
        trainer.run(train_loader)
        if rank==0:
            torch.save({'model': model.state_dict()}, output_dir/"final.pt")

if __name__=='__main__':
    main()
'''





# ---------------- App ----------------
class ModelTrainer(App):
    TITLE = "ModelTrainer"
    CSS_THEME = "nord"
    
    CSS = """
    Screen { layout: vertical; }
    .sidebar { width: 28; min-width: 24; padding: 1; }
    .detail { padding: 1; }
    .table-header { text-style: bold; }
    .hbar { padding: 0 1; height: 3; content-align: left middle; border-bottom: solid $accent 20%; }
    .row { height: 3; padding: 0 1; }
    #detail-table { height: 1fr; }
    #log { height: 1fr; border: solid $accent 15%; }
    
    /* Remove tab animations */
    TabbedContent {
        transition: none !important;
    }
    /* Make horizontal rows fit properly */
    .row {
        width: 100%;
        margin: 0;
        padding: 0;
    }
    .row > Input {
        width: 1fr;
        height: 3;
    }
    .row > Button {
        width: auto;
        height: 3;
    }

    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh System"),
    ]

    def compose(self) -> ComposeResult:  # type: ignore[override]
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("Local", id="tab-local"):
                yield LocalPane()
            with TabPane("Models", id="tab-models"):
                yield ModelsPane()
            with TabPane("Training", id="tab-training"):
                yield TrainingPane()
        yield Footer()

    def action_refresh(self) -> None:  # type: ignore[override]
        # Clear cache and refresh current section in Local tab
        for d in self.query(LocalDetail):
            d._cache.clear()
            d.refresh_section()
    





if __name__ == "__main__":
    ModelTrainer().run()


