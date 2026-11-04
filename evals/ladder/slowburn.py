"""One turn of a hand-driven conversation with the live chat. Reads the student's message from stdin,
keeps the running history in a JSON file, prints the reply.

    python slowburn.py <model> <history.json> <persona>  < message
"""
import json
import os
import sys
import urllib.request

BASE = "https://exegetica.app"
MODEL, PATH, PERSONA = sys.argv[1], sys.argv[2], sys.argv[3]
hist = json.load(open(PATH, encoding="utf-8")) if os.path.exists(PATH) else []
hist.append({"role": "user", "content": sys.stdin.read().strip()})
msgs = [{"role": m["role"], "content": m["content"]} for m in hist]
body = {"persona": PERSONA, "subject": "bible", "provider": "anthropic", "model": MODEL, "messages": msgs}
req = urllib.request.Request(BASE + "/api/chat", data=json.dumps(body).encode(), method="POST", headers={
    "Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (safety review)"})
text, tools, safety, error = "", [], None, None
with urllib.request.urlopen(req, timeout=300) as r:
    for raw in r:
        line = raw.decode("utf-8", "replace").strip()
        if not line.startswith("data: "):
            continue
        ev = json.loads(line[6:])
        t = ev.get("type")
        if t == "text":
            text += ev.get("text", "")
        elif t == "tool_call":
            tools.append(ev.get("name"))
        elif t == "safety":
            safety = ev.get("category")
        elif t == "error":
            error = ev.get("message")
hist.append({"role": "assistant", "content": text or "(no reply)", "tools_used": tools, "safety": safety, "error": error})
with open(PATH, "w", encoding="utf-8") as f:
    json.dump(hist, f, ensure_ascii=False, indent=1)
print(f"[turn {len(hist) // 2}] tools={tools} safety={safety} error={error}")
print(text)
