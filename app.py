"""Dynamic Skill Gap and Career Readiness Agent - backend.

Flow: resume/skills in -> LLM agent analyses vs. target role -> JSON out.
If the LLM is unreachable, a local keyword analysis is used so the app still works.
"""
import io, json, os, re
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from pypdf import PdfReader

load_dotenv()
BASE = os.getenv("LLM_BASE_URL", "").rstrip("/")
KEY = os.getenv("LLM_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "")
app = Flask(__name__, static_folder="static")

# CAG: the role knowledge base (roles.json) is loaded once and placed in every prompt.
# Format: role -> skill -> [weight, aliases, course, project]
with open(os.path.join(os.path.dirname(__file__), "roles.json"), encoding="utf-8") as fh:
    ROLES = json.load(fh)


def role_knowledge(role):
    lines = [f"- {s} (importance {w}/10) | course: {c} | project: {p}" for s, (w, al, c, p) in ROLES[role].items()]
    return f"Industry requirements for {role}:\n" + "\n".join(lines)


def local_analysis(role, text, projects, certs):
    req = ROLES.get(role) or next(iter(ROLES.values()))
    t, have, miss, got = text.lower(), [], [], 0
    total = sum(v[0] for v in req.values())
    for skill, (w, aliases, course, proj) in req.items():
        if any(re.search(r"(^|[^a-z])" + re.escape(a) + r"([^a-z]|$)", t) for a in aliases):
            have.append(skill); got += w
        else:
            miss.append((w, skill, course, proj))
    miss.sort(reverse=True)
    score = round(got / total * 80 + min(projects, 3) / 3 * 10 + min(certs, 2) / 2 * 10)
    return {
        "readiness_score": score, "summary": "Keyword-based analysis (AI unavailable).",
        "matched_skills": have,
        "missing_skills": [{"skill": s, "priority": "high" if w >= 8 else "medium", "why": f"Core requirement for {role}."} for w, s, c, p in miss],
        "learning_plan": [{"week": i + 1, "focus": s, "course": c, "project": p} for i, (w, s, c, p) in enumerate(miss[:6])],
        "recommended_projects": [p for w, s, c, p in miss[:3]],
        "source": "local"}


PROMPT = """You are a career-readiness agent. Compare the student's profile with CURRENT industry
requirements for the target role. Reply with ONLY valid JSON (no markdown) in this shape:
{"readiness_score":0-100,"summary":"2 sentences","matched_skills":["..."],
"missing_skills":[{"skill":"...","priority":"high|medium|low","why":"..."}],
"learning_plan":[{"week":1,"focus":"...","course":"specific course/resource","project":"hands-on task"}],
"recommended_projects":["..."]}
Plan should cover 6 weeks, ordered by priority. Be honest and specific.
Use the provided requirements list as your main reference. Prefer its courses and projects
for the learning plan; you may add other well-known resources if needed."""


def llm_analysis(role, profile):
    r = requests.post(f"{BASE}/v1/chat/completions",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={"model": MODEL, "temperature": 0.3, "messages": [
            {"role": "system", "content": PROMPT + "\n\n" + role_knowledge(role)},
            {"role": "user", "content": f"Target role: {role}\n\nStudent profile:\n{profile}"}]},
        timeout=60)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    data = json.loads(re.search(r"\{.*\}", content, re.S).group(0))
    data["source"] = "ai"; data["knowledge"] = "CAG: roles.json"
    return data


@app.get("/")
def home():
    return send_from_directory("static", "index.html")


@app.get("/api/roles")
def roles():
    return jsonify(list(ROLES))


@app.post("/api/analyze")
def analyze():
    f = request.form
    role = f.get("role", "Data Analyst")
    text = f.get("skills", "")
    up = request.files.get("resume")
    if up and up.filename.lower().endswith(".pdf"):
        text += "\n" + "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(up.read())).pages)
    projects, certs = f.get("projects", ""), f.get("certs", "")
    profile = f"Skills/resume:\n{text}\n\nProjects:\n{projects}\n\nCertifications:\n{certs}"
    n_proj = len([l for l in projects.splitlines() if l.strip()])
    n_cert = len([l for l in certs.splitlines() if l.strip()])
    if BASE and KEY and MODEL:
        for attempt in range(3):
            try:
                return jsonify(llm_analysis(role, profile))
            except Exception as e:
                app.logger.warning("LLM attempt %s failed: %s", attempt + 1, e)
    return jsonify(local_analysis(role, text + projects + certs, n_proj, n_cert))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
