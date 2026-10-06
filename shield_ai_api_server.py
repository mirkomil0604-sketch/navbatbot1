from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import re
import logging
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SHIELD.AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:9b")

class AnalyzeRequest(BaseModel):
    text: str
    language: str = "uz"

class AnalyzeResponse(BaseModel):
    verdict: str
    confidence: float
    explanation: str
    category: str

@app.get("/health")
async def health():
    return {"status": "ok", "service": "shield-ai-api"}

def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "verdict": "uncertain",
            "confidence": 0.5,
            "explanation": "Tahlil qilishda xatolik yuz berdi.",
            "category": "other",
        }

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    try:
        logger.info("Analyzing text: %s", request.text[:100])
        prompt = (
            "You are an expert fact-checker for Uzbek misinformation detection. "
            "Analyze the following text and determine if it contains misinformation, "
            "disinformation, or is credible. "
            f"Text: {request.text}\n\n"
            "Respond ONLY with valid JSON object, no markdown, no extra text. JSON fields:\n"
            "- verdict: one of [misinformation, likely_false, credible, uncertain]\n"
            "- confidence: float between 0 and 1\n"
            "- explanation: brief explanation in Uzbek\n"
            "- category: one of [health, politics, finance, social, other]"
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        result_text = data.get("response", "")
        result = extract_json(result_text)
        logger.info("Analysis result: %s", result)
        return AnalyzeResponse(**result)
    except Exception as e:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
