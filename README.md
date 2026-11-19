# Dynamic Skill Gap and Career Readiness Agent

Helps students prepare for a target job role. It reads their skills/resume/projects/certifications,
compares them with industry requirements, scores career readiness, finds missing skills and builds a
personalised 6-week learning plan with courses and projects.

## 1. Run it locally
1. Install Python 3.10+.
2. In this folder:
   ```
   python -m venv venv
   venv\Scripts\activate        (Windows)   |   source venv/bin/activate   (Mac/Linux)
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in:
   - `LLM_BASE_URL` (https://nexusapi.navigatelabs.ai)
   - `LLM_API_KEY` - **use a NEW key** (the old one was shared in public chat, so revoke it)
   - `LLM_MODEL` - the model name from your provider's dashboard
4. `python app.py` then open http://127.0.0.1:5000

The code assumes an OpenAI-compatible endpoint: `POST {BASE}/v1/chat/completions`. If your provider
uses a different path or format, change only `llm_analysis()` in `app.py`.
Without a working key, the app still runs using the built-in keyword analysis.

## 2. Put the project on GitHub
```
git init
git add .
git commit -m "Skill gap agent"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```
`.gitignore` keeps `.env` (your key) out of the repo. Check this before pushing.

## 3. Add the repo link in OneDrive
1. Right-click inside the folder and choose **+ Add new**, then **Link** at the bottom of the dropdown.
2. Paste your project repo URL.
3. Name it after your team or project title.
4. Click **Add shortcut**.
5. Click the new link to confirm it opens the repo.

## 4. Deploy (optional)
Render, Railway or PythonAnywhere work. Start command: `gunicorn app:app` (add `gunicorn` to
requirements). Set the three env vars in the host's dashboard, never in code.

## 5. Next improvements
- Pull live job postings (e.g. an Adzuna/LinkedIn-style API) for real requirement data
- User accounts and a database to track progress over time
- Re-test skills with quizzes and update the readiness score
- Course links from real catalogs (Coursera, NPTEL, freeCodeCamp)
