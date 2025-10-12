import subprocess

def detect_vram_gb() -> int | None:
    """Try to detect NVIDIA GPU VRAM (GB) using nvidia-smi. Returns int GB or None."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=3,
        )
        # If multiple GPUs, take the first line
        line = out.strip().splitlines()[0]
        # value is in MiB; convert to GiB approximated
        mib = int(line.strip())
        gib = max(1, round(mib / 1024))
        return gib
    except Exception:
        return None
