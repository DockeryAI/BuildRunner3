"""
BR3 Cluster — Node 5: Below (Workhorse)
Local LLM inference via Ollama (Qwen 3 8B on RTX 2080Ti).

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
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "30"))

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


class SummarizeRequest(BaseModel):
    text: str
    max_length: int = 300


# --- Ollama Client ---
async def _ollama_generate(
    prompt: str,
    system: str = "",
    max_tokens: int = 500,
    json_mode: bool = False,
) -> str:
    """Call Ollama /api/chat. Returns the response text or raises."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": OLLAMA_MODEL,
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
        text = await _ollama_generate(req.prompt, system=system, max_tokens=req.max_tokens)
        return {"text": text.strip()}
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
        summary = await _ollama_generate(prompt, system=system, max_tokens=req.max_length)
        return {"summary": summary.strip()}
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
