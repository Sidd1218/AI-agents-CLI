#!/usr/bin/env python3
# host-cli/ai.py
import os, sys, requests, json, subprocess, time, argparse, shutil

SERVER_URL = os.getenv("AI_SERVER_URL", "http://127.0.0.1:5005/query")
LOGDIR = os.path.expanduser("~/.ai-cli")
os.makedirs(LOGDIR, exist_ok=True)
LOGFILE = os.path.join(LOGDIR, "logs.txt")

UNSAFE_PATTERNS = [
    r"\brm\b", r"\brm\s+-rf\b", r"\bdd\b", r"\bmkfs\b", r"/dev/", r"\bshutdown\b", r"\breboot\b"
]
ALLOWED_FRAGMENTS = ["find", "ls", "wc", "grep", "chmod", "chown", "stat", "du", "head", "tail", "file"]

def log(msg):
    ts = time.asctime()
    with open(LOGFILE, "a") as f:
        f.write(f"{ts} | {msg}\n")

def check_safe(cmd):
    low = cmd.lower()
    for p in UNSAFE_PATTERNS:
        if __import__("re").search(p, low):
            return False
    if not any(f in low for f in ALLOWED_FRAGMENTS):
        return False
    return True

def send_prompt(prompt):
    resp = requests.post(SERVER_URL, json={"prompt": prompt}, timeout=120)
    resp.raise_for_status()
    return resp.json()

def confirm_and_run(cmd, auto_yes=False, dry_run=False):
    print(f"Suggested: {cmd}")
    if not check_safe(cmd):
        print("Command flagged as unsafe. Refusing to run.")
        log(f"REFUSED UNSAFE: {cmd}")
        return "(refused unsafe)"
    if dry_run:
        print("[dry-run] Not executing.")
        return "(dry-run)"
    if not auto_yes:
        ans = input("Execute on host? (y/N): ").strip().lower()
        if ans not in ("y","yes"):
            print("Aborted by user.")
            log(f"ABORTED: {cmd}")
            return "(aborted)"

    # Run locally
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        out = result.stdout.strip()
        err = result.stderr.strip()
        log(f"EXECUTED: {cmd}\nEXIT:{result.returncode}\nOUT:{out}\nERR:{err}")
        if result.returncode != 0:
            return f"(exit {result.returncode})\nSTDOUT:\n{out}\nSTDERR:\n{err}"
        return out or "(no stdout)"
    except Exception as e:
        log(f"EXECUTION_ERROR: {cmd} -> {e}")
        return f"Execution error: {e}"

def main():
    ap = argparse.ArgumentParser(description="ai: Natural-language CLI assistant")
    ap.add_argument("prompt", nargs="+", help="natural language prompt")
    ap.add_argument("--yes", "-y", action="store_true", help="auto confirm suggested command")
    ap.add_argument("--dry-run", action="store_true", help="don't execute; show suggested command only")
    args = ap.parse_args()
    prompt = " ".join(args.prompt)
    print("Sending to AI server...")
    j = send_prompt(prompt)
    # handle server error shapes
    if "error" in j:
        print("AI server error:", j.get("error"))
        print("Raw output:", j.get("raw"))
        return
    obj = j["result"]
    reasoning = obj.get("reasoning","(no reasoning)")
    print("== Model reasoning ==\n", reasoning, "\n== End reasoning ==\n")
    if obj["action"] == "run_command":
        cmd = obj["command"]
        out = confirm_and_run(cmd, auto_yes=args.yes, dry_run=args.dry_run)
        print("=== Command output ===\n", out)
    elif obj["action"] == "reply":
        print("Assistant:", obj.get("message","(no message)"))
    else:
        print("Unknown action from AI:", obj)

if __name__ == "__main__":
    main()
