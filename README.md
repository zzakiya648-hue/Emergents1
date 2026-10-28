# AI HR Intern Mentor — Streamlit Starter

A small HR + intern workspace inspired by AI internship mentor platforms. Built with Python, Streamlit, and SQLite.

## Features

- **HR Portal:** create and assign tasks, set due dates and priorities, review submissions, score work, and provide feedback.
- **Intern Portal:** view assigned tasks, submit notes and project files, and see review results.
- **Mentor chat:** offline guidance works out of the box. Optional OpenAI integration provides generated responses when an API key is configured.
- **Project ZIP review:** HR can download uploaded files and inspect the file names inside ZIP submissions. Uploaded code is never executed.
- **Local persistence:** tasks, submissions, chat history, and reviews are stored in SQLite.

## Requirements

- Python 3.10 or newer recommended
- pip

## Run locally

### Windows (PowerShell or CMD)

```bash
cd AI-HR-Intern-Mentor-Streamlit
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

### macOS / Linux

```bash
cd AI-HR-Intern-Mentor-Streamlit
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Streamlit opens the app in your browser, normally at `http://localhost:8501`.

## Enable generated AI responses (optional)

The app runs without an API key using offline mentor guidance. To enable OpenAI responses, set an environment variable before starting Streamlit.

**Windows PowerShell:**

```powershell
$env:OPENAI_API_KEY="your-api-key"
streamlit run app.py
```

**macOS / Linux:**

```bash
export OPENAI_API_KEY="your-api-key"
streamlit run app.py
```

Optionally set `OPENAI_MODEL` to a model available to your API account. Never commit API keys to GitHub.

Alternatively, create `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "your-api-key"
```

Keep that file private and out of version control.

## First-use demo

1. Open **HR Portal** in the sidebar.
2. Create a task and assign it to `Sri` (or any name you choose).
3. Switch to **Intern Portal** and enter the same intern name.
4. Open **My Tasks**, then **Submit Project** to submit notes and optionally a file.
5. Switch back to HR and review the submission.
6. Switch to the intern portal to see the score and feedback under **My Progress**.

## Project structure

```text
AI-HR-Intern-Mentor-Streamlit/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── data/                 # created automatically at runtime
    └── submissions/      # uploaded submissions
```

## Important security notes

This is a learning/demo project, not a production HR system. The role selector is only a demo switch and is **not authentication**. Before public deployment, add real authentication and role-based authorization, file size/type and archive-bomb protections, rate limits, privacy controls, and secure database/storage configuration. Do not run intern-submitted code automatically. AI feedback should be checked by a human reviewer.
