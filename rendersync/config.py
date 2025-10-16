import os

# TODO ComfyUI configs

# Default Ollama HTTP endpoint
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
# Choose a small, efficient default model. Override with OLLAMA_MODEL env var.
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

OLLAMA_GENERATION_OPTIONS = {
    "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
    "top_p": float(os.getenv("OLLAMA_TOP_P", "0.9")),
    "top_k": int(os.getenv("OLLAMA_TOP_K", "40")),
    "repeat_penalty": float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.1")),
    # num_ctx can be increased if you have RAM/VRAM. Keep conservative by default.
    "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "4096")),
    # Threads: use CPU cores by default; Ollama will auto-tune if omitted.
    # You can set OLLAMA_NUM_THREAD to pin it.
    **({"num_thread": int(os.getenv("OLLAMA_NUM_THREAD"))}
       if os.getenv("OLLAMA_NUM_THREAD") else {}),
    # GPU config: Ollama generally auto-detects. This exists for advanced users.
    **({"num_gpu": int(os.getenv("OLLAMA_NUM_GPU"))}
       if os.getenv("OLLAMA_NUM_GPU") else {}),
}
