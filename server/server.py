# server/server.py
from fastapi import FastAPI
from pydantic import BaseModel
from llm_client import ask_model
import re, json

app = FastAPI()

class Query(BaseModel):
    prompt: str

# System instruction: ask the model to always return EXACT JSON
SYSTEM_INSTRUCTION = """
You are an assistant that, when given a user instruction, MUST respond with a single JSON object ONLY and NOTHING ELSE.
Two allowed outputs:
1) Run a command:
{"action":"run_command", "command":"<shell command>", "reasoning":"<brief reasoning>"}
2) Reply:
{"action":"reply", "message":"<text>", "reasoning":"<brief reasoning>"}

Rules:
- If you choose run_command, prefer POSIX commands (find, ls, wc, grep, chmod, etc.) and avoid pipes or complex shell constructs. Use simple commands.
- DO NOT include dangerous commands (rm, dd, mkfs, shutdown, reboot, /dev/). If the user intent is destructive, respond with action=reply and a safe explanation.
- Workspace path for file actions is '/workspace' on the host. Use 'find /workspace ...' for searches.
Return JSON only.
"""

def build_prompt(user_prompt: str) -> str:
    return SYSTEM_INSTRUCTION + "\nUser request: " + user_prompt

@app.post("/query")
def query(q: Query):
    prompt = build_prompt(q.prompt)
    text = ask_model(prompt)
    # Try to extract a JSON object
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        raw = m.group(0)
    else:
        raw = text  # fallback
    # validate JSON
    try:
        obj = json.loads(raw)
    except Exception:
        return {"error": "model_output_not_json", "raw": text}
    # basic schema check
    if obj.get("action") not in ("run_command","reply"):
        return {"error": "invalid_action", "raw": text}
    return {"result": obj, "raw": text}
