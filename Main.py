import requests
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Online Code Runner (via Piston API)")

# Enable CORS (so frontend / Postman can access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Models -----
class RunRequest(BaseModel):
    language: str            # e.g. "python", "java", "cpp"
    code: str
    stdin: Optional[str] = ""    # Optional user input
    timeout_seconds: Optional[int] = 5

class RunResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: Optional[int] = None
    timed_out: bool = False


# ----- Helper -----
def get_piston_lang(language: str):
    lang = language.lower()
    if lang == "python":
        return ("python", "3.10.0", "main.py")
    elif lang == "java":
        return ("java", "15.0.2", "Main.java")
    elif lang in ("cpp", "c++"):
        return ("cpp", "10.2.0", "main.cpp")
    else:
        raise HTTPException(status_code=400, detail="Unsupported language. Use 'python', 'java', or 'cpp'.")


# ----- Main Endpoint -----
@app.post("/run", response_model=RunResponse)
def run_code(req: RunRequest):
    try:
        language, version, filename = get_piston_lang(req.language)

        payload = {
            "language": language,
            "version": version,
            "files": [{"name": filename, "content": req.code}],
            "stdin": req.stdin or "",
            "args": [],
            "compile_timeout": req.timeout_seconds * 1000,
            "run_timeout": req.timeout_seconds * 1000
        }

        # Call Piston API
        response = requests.post(
            "https://emkc.org/api/v2/piston/execute",
            json=payload,
            timeout=req.timeout_seconds + 3
        )

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Piston API error: {response.text}")

        result = response.json().get("run", {})

        return RunResponse(
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            exit_code=result.get("code", 0),
            timed_out=False
        )

    except requests.Timeout:
        return RunResponse(stdout="", stderr="Execution timed out.", timed_out=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----- Root -----
@app.get("/")
def root():
    return {"message": "Welcome to the Online Code Runner! Use POST /run with {language, code, stdin (optional)}."}
