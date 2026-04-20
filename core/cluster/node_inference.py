"""
BR3 Cluster — Node 5: Below (Workhorse)
Local LLM inference via Ollama. Dual RTX 3090 + NVLink by default; single-GPU
fallback path preserved so Phase 1 pre-NVLink test rigs still work.

Capabilities (advertised via /api/capabilities):
  - dual_gpu: 2x RTX 3090, 48GB total VRAM when NVLink NV# detected
  - single_gpu: fallback (11–24GB VRAM, no 70B models)
NVLink detection rule: `nvidia-smi nvlink --status` must report ≥4 active
Link rows with non-zero GB/s before declaring dual-GPU healthy.

Run: uvicorn core.cluster.node_inference:app --host 0.0.0.0 --port 8100
"""

import os
import subprocess
import time
from typing import Optional

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from core.cluster.base_service import create_app

# --- Config ---
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL_SMALL = os.environ.get("OLLAMA_MODEL_SMALL", "qwen3:8b")
OLLAMA_MODEL_LARGE = os.environ.get("OLLAMA_MODEL_LARGE", "llama3.3:70b-instruct-q4_K_M")
# Back-compat: OLLAMA_MODEL still honored; defaults to small model for classify/draft.
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", OLLAMA_MODEL_SMALL)
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "30"))

# Dual-GPU constants (Phase 1 hardware). Single-GPU fallback uses whatever nvidia-smi reports.
EXPECTED_GPUS_DUAL = 2
EXPECTED_VRAM_MB_PER_GPU = 24576  # RTX 3090
NVLINK_MIN_ACTIVE_LINKS = 4  # P3669 bridge exposes 4 links per GPU

# --- App ---
app = create_app(role="inference", version="0.1.0")


# --- Request Models ---
class ClassifyRequest(BaseModel):
    text: str
    categories: list[str] = [
        "backend", "frontend", "fullstack", "docs",
        "infra", "testing", "data-migration",
    ]


class DraftRequest(BaseModel):
    prompt: str
    max_tokens: int = 500
    system: Optional[str] = None
    model: Optional[str] = None  # None = small default; pass OLLAMA_MODEL_LARGE for 70B routing


class SummarizeRequest(BaseModel):
    text: str
    max_length: int = 300
    model: Optional[str] = None  # Same routing semantics as DraftRequest


# --- Ollama Client ---
async def _ollama_generate(
    prompt: str,
    system: str = "",
    max_tokens: int = 500,
    json_mode: bool = False,
    model: Optional[str] = None,
) -> str:
    """Call Ollama /api/chat. Returns the response text or raises.
    model=None uses the small default (OLLAMA_MODEL); caller passes
    OLLAMA_MODEL_LARGE to route to 70B on the dual-GPU path."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model or OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {"num_predict": max_tokens, "temperature": 0},
        }
        if json_mode:
            payload["format"] = "json"

        resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")


# --- Endpoints ---

@app.post("/api/classify")
async def classify(req: ClassifyRequest):
    """Classify text into one of the given categories."""
    categories_str = ", ".join(req.categories)
    system = (
        "You are a strict classifier. Given text describing a task, respond with ONLY "
        "a JSON object: {\"category\": \"<one of the categories>\", \"confidence\": <0.0-1.0>}. "
        "No explanation, no markdown, just the JSON object."
    )
    prompt = (
        f"Categories: {categories_str}\n\n"
        f"Text to classify:\n{req.text}\n\n"
        "Respond with JSON only."
    )

    try:
        raw = await _ollama_generate(prompt, system=system, max_tokens=100, json_mode=True)
    except httpx.TimeoutException:
        return {"error": "Ollama timeout", "category": None, "confidence": 0.0}
    except httpx.HTTPError as e:
        return {"error": f"Ollama error: {e}", "category": None, "confidence": 0.0}

    # Parse the JSON from the LLM response
    import json
    import re
    try:
        # Strip Qwen3 thinking tags if present
        cleaned = raw.strip()
        cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()
        # Strip markdown fences if present
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        # Extract first JSON object if surrounded by text
        json_match = re.search(r"\{[^}]+\}", cleaned)
        if json_match:
            cleaned = json_match.group(0)
        result = json.loads(cleaned)
        category = result.get("category", "").lower()
        confidence = float(result.get("confidence", 0.0))

        # Validate category is in the allowed list
        if category not in [c.lower() for c in req.categories]:
            # Pick closest match or return raw
            category = raw.strip().lower()
            confidence = max(0.5, confidence)

        return {"category": category, "confidence": round(confidence, 2)}
    except (json.JSONDecodeError, ValueError, AttributeError):
        # Fallback: try to extract category from raw text
        raw_lower = raw.strip().lower()
        for cat in req.categories:
            if cat.lower() in raw_lower:
                return {"category": cat.lower(), "confidence": 0.6}
        return {"category": raw_lower[:50], "confidence": 0.3}


@app.post("/api/draft")
async def draft(req: DraftRequest):
    """Draft text from a prompt."""
    system = req.system or (
        "You are a skilled technical writer. Write clear, concise text. "
        "No preamble or meta-commentary — just the requested content."
    )

    try:
        text = await _ollama_generate(req.prompt, system=system, max_tokens=req.max_tokens, model=req.model)
        return {"text": text.strip(), "model": req.model or OLLAMA_MODEL}
    except httpx.TimeoutException:
        return {"error": "Ollama timeout", "text": ""}
    except httpx.HTTPError as e:
        return {"error": f"Ollama error: {e}", "text": ""}


@app.post("/api/summarize")
async def summarize(req: SummarizeRequest):
    """Summarize text."""
    system = (
        "You are a summarizer. Produce a concise summary of the given text. "
        "Keep it under the requested length. No preamble — just the summary."
    )
    prompt = (
        f"Summarize the following text in {req.max_length} characters or fewer:\n\n"
        f"{req.text}"
    )

    try:
        summary = await _ollama_generate(prompt, system=system, max_tokens=req.max_length, model=req.model)
        return {"summary": summary.strip(), "model": req.model or OLLAMA_MODEL}
    except httpx.TimeoutException:
        return {"error": "Ollama timeout", "summary": ""}
    except httpx.HTTPError as e:
        return {"error": f"Ollama error: {e}", "summary": ""}


@app.get("/api/models")
async def list_models():
    """List available Ollama models (proxy to Ollama /api/tags)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = [
                {
                    "name": m.get("name", ""),
                    "size_gb": round(m.get("size", 0) / (1024**3), 1),
                    "modified": m.get("modified_at", ""),
                    "family": m.get("details", {}).get("family", ""),
                    "parameters": m.get("details", {}).get("parameter_size", ""),
                    "quantization": m.get("details", {}).get("quantization_level", ""),
                }
                for m in data.get("models", [])
            ]
            return {"models": models, "count": len(models), "default": OLLAMA_MODEL}
    except httpx.TimeoutException:
        return {"error": "Ollama timeout", "models": [], "count": 0}
    except httpx.HTTPError as e:
        return {"error": f"Ollama error: {e}", "models": [], "count": 0}


def _detect_nvlink_active() -> dict:
    """Parse `nvidia-smi nvlink --status`. Returns {active_links, gb_per_link, healthy}.
    Healthy requires ≥NVLINK_MIN_ACTIVE_LINKS link rows at non-zero bandwidth."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "nvlink", "--status"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return {"active_links": 0, "gb_per_link": 0.0, "healthy": False, "detail": "nvlink --status failed"}
        active = 0
        bws: list[float] = []
        for line in result.stdout.splitlines():
            s = line.strip()
            # Lines look like:  Link 0: 14.062 GB/s
            if s.startswith("Link ") and "GB/s" in s:
                try:
                    gbs = float(s.split(":", 1)[1].strip().split()[0])
                    if gbs > 0:
                        active += 1
                        bws.append(gbs)
                except (ValueError, IndexError):
                    continue
        avg = sum(bws) / len(bws) if bws else 0.0
        return {
            "active_links": active,
            "gb_per_link": round(avg, 3),
            "healthy": active >= NVLINK_MIN_ACTIVE_LINKS,
        }
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"active_links": 0, "gb_per_link": 0.0, "healthy": False, "detail": "nvlink probe unavailable"}


@app.get("/api/capabilities")
async def capabilities():
    """Advertise node capability profile. Dispatcher uses this to route 70B vs 8B work."""
    try:
        gpu_result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        gpu_count = 0
        vram_total_mb = 0
        if gpu_result.returncode == 0:
            lines = [l.strip() for l in gpu_result.stdout.strip().splitlines() if l.strip()]
            gpu_count = len(lines)
            vram_total_mb = sum(int(l) for l in lines if l.isdigit())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        gpu_count, vram_total_mb = 0, 0

    nvlink = _detect_nvlink_active()
    dual_gpu_ready = (
        gpu_count >= EXPECTED_GPUS_DUAL
        and vram_total_mb >= EXPECTED_GPUS_DUAL * EXPECTED_VRAM_MB_PER_GPU - 512
        and nvlink["healthy"]
    )
    return {
        "node": "below",
        "gpu_count": gpu_count,
        "vram_total_mb": vram_total_mb,
        "nvlink": nvlink,
        "dual_gpu_ready": dual_gpu_ready,
        "mode": "dual_gpu" if dual_gpu_ready else "single_gpu_fallback",
        "model_small": OLLAMA_MODEL_SMALL,
        "model_large": OLLAMA_MODEL_LARGE if dual_gpu_ready else None,
        "supports_70b": dual_gpu_ready,
    }


@app.get("/api/gpu")
async def gpu_status():
    """GPU status via nvidia-smi."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,power.limit",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return {"error": f"nvidia-smi failed: {result.stderr.strip()}", "available": False}

        gpus = []
        for line in result.stdout.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 7:
                gpus.append({
                    "name": parts[0],
                    "temp_c": int(parts[1]),
                    "utilization_pct": int(parts[2]),
                    "memory_used_mb": int(parts[3]),
                    "memory_total_mb": int(parts[4]),
                    "power_draw_w": float(parts[5]),
                    "power_limit_w": float(parts[6]),
                })

        return {"available": True, "gpus": gpus}
    except FileNotFoundError:
        return {"error": "nvidia-smi not found", "available": False}
    except subprocess.TimeoutExpired:
        return {"error": "nvidia-smi timed out", "available": False}
    except Exception as e:
        return {"error": str(e), "available": False}
