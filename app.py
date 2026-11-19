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

# Fallback role requirements: skill -> (weight, aliases)
ROLES = {
    "Data Analyst": {"SQL": (10, ["sql", "mysql"]), "Python": (9, ["python"]), "Excel": (7, ["excel"]),
        "Data visualization": (9, ["tableau", "power bi", "matplotlib"]), "Statistics": (8, ["statistics", "probability"]),
        "pandas": (8, ["pandas", "numpy"]), "Git": (4, ["git", "github"])},
    "Full Stack Developer": {"JavaScript": (10, ["javascript", "typescript"]), "React": (9, ["react", "vue", "angular"]),
        "HTML/CSS": (7, ["html", "css"]), "Node.js": (8, ["node", "express"]), "Databases": (8, ["sql", "mongodb", "postgres"]),
        "REST APIs": (7, ["api", "rest"]), "Git": (6, ["git", "github"]), "Docker": (5, ["docker"])},
    "Machine Learning Engineer": {"Python": (10, ["python"]), "Machine learning": (10, ["machine learning", "scikit", "sklearn"]),
        "Deep learning": (8, ["pytorch", "tensorflow", "keras"]), "Statistics": (8, ["statistics", "linear algebra"]),
        "pandas": (7, ["pandas", "numpy"]), "MLOps": (6, ["mlops", "docker", "mlflow"]), "NLP": (5, ["nlp", "transformers", "llm"])},
    "Cloud / DevOps Engineer": {"Linux": (9, ["linux", "bash"]), "Cloud platform": (10, ["aws", "azure", "gcp"]),
        "Docker": (9, ["docker"]), "Kubernetes": (8, ["kubernetes", "k8s"]), "CI/CD": (8, ["ci/cd", "jenkins", "github actions"]),
        "Terraform": (7, ["terraform", "ansible"]), "Monitoring": (5, ["prometheus", "grafana"])},
}


def local_analysis(role, text, projects, certs):
    req = ROLES.get(role) or next(iter(ROLES.values()))
    t, have, miss, got = text.lower(), [], [], 0
    total = sum(w for w, _ in req.values())
    for skill, (w, aliases) in req.items():
        if any(re.search(r"(^|[^a-z])" + re.escape(a) + r"([^a-z]|$)", t) for a in aliases):
            have.append(skill); got += w
        else:
            miss.append((w, skill))
    miss.sort(reverse=True)
    score = round(got / total * 80 + min(projects, 3) / 3 * 10 + min(certs, 2) / 2 * 10)
    return {
        "readiness_score": score, "summary": "Keyword-based analysis (AI unavailable).",
        "matched_skills": have,
        "missing_skills": [{"skill": s, "priority": "high" if w >= 8 else "medium", "why": f"Core requirement for {role}."} for w, s in miss],
        "learning_plan": [{"week": i + 1, "focus": s, "course": f"Search '{s} for beginners' on Coursera / YouTube / freeCodeCamp",
                           "project": f"Build a small project that uses {s}"} for i, (w, s) in enumerate(miss[:6])],
        "recommended_projects": [f"Portfolio project demonstrating {s}" for w, s in miss[:3]],
        "source": "local"}


PROMPT = """You are a career-readiness agent. Compare the student's profile with CURRENT industry
requirements for the target role. Reply with ONLY valid JSON (no markdown) in this shape:
{"readiness_score":0-100,"summary":"2 sentences","matched_skills":["..."],
"missing_skills":[{"skill":"...","priority":"high|medium|low","why":"..."}],
"learning_plan":[{"week":1,"focus":"...","course":"specific course/resource","project":"hands-on task"}],
"recommended_projects":["..."]}
Plan should cover 6 weeks, ordered by priority. Be honest and specific."""


def llm_analysis(role, profile):
    r = requests.post(f"{BASE}/v1/chat/completions",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={"model": MODEL, "temperature": 0.3, "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": f"Target role: {role}\n\nStudent profile:\n{profile}"}]},
        timeout=60)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    data = json.loads(re.search(r"\{.*\}", content, re.S).group(0))
    data["source"] = "ai"
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
        try:
            return jsonify(llm_analysis(role, profile))
        except Exception as e:
            app.logger.warning("LLM failed, using fallback: %s", e)
    return jsonify(local_analysis(role, text + projects + certs, n_proj, n_cert))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
