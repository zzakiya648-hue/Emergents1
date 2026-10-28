from __future__ import annotations
import os, re, json, sqlite3, zipfile, io
from pathlib import Path
from datetime import datetime, date
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
UPLOAD_DIR = DATA_DIR / "submissions"
DB_PATH = DATA_DIR / "mentor.db"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Intern Mentor | HR Workspace", page_icon="🎓", layout="wide")

# ------------------------------ Storage ------------------------------------
def db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT NOT NULL,
            assignee TEXT NOT NULL, due_date TEXT, priority TEXT DEFAULT 'Medium',
            created_by TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT DEFAULT 'Assigned')""")
        con.execute("""CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER NOT NULL, intern TEXT NOT NULL,
            notes TEXT, file_name TEXT, file_path TEXT, submitted_at TEXT NOT NULL,
            status TEXT DEFAULT 'Submitted', score INTEGER, review TEXT,
            FOREIGN KEY(task_id) REFERENCES tasks(id))""")
        con.execute("""CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT NOT NULL, role TEXT NOT NULL,
            question TEXT NOT NULL, answer TEXT NOT NULL, created_at TEXT NOT NULL)""")

def rows(query, params=()):
    with db() as con:
        return con.execute(query, params).fetchall()

def execute(query, params=()):
    with db() as con:
        cur = con.execute(query, params)
        con.commit()
        return cur.lastrowid

init_db()

# ------------------------------ UI style -----------------------------------
st.markdown("""
<style>
:root { --ink:#182235; --muted:#667085; --line:#e7ebf2; --accent:#5b5bd6; }
.block-container { padding-top: 1.5rem; max-width: 1400px; }
.hero { padding: 1.4rem 1.6rem; border-radius: 20px; background: linear-gradient(120deg,#eef2ff 0%,#f5f3ff 55%,#ecfeff 100%); border:1px solid #e4e7ff; margin-bottom:1rem; }
.hero h1 { margin:0; color:#182235; font-size:2.15rem; }
.hero p { margin:.4rem 0 0; color:#596579; }
div[data-testid="stMetric"] { border:1px solid #e8ebf3; padding:14px 16px; border-radius:14px; background:#fff; }
.small-muted { color:#667085; font-size:.9rem; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🎓 Intern Mentor")
    st.caption("HR workspace · Intern learning hub")
    st.divider()
    role = st.radio("Open portal", ["Intern Portal", "HR Portal"], index=0)
    if role == "Intern Portal":
        display_name = st.text_input("Intern name", value=st.session_state.get("display_name", "Sri"), key="intern_name")
    else:
        display_name = st.text_input("HR name", value=st.session_state.get("display_name", "HR Admin"), key="hr_name")
    display_name = display_name.strip() or ("Intern" if role == "Intern Portal" else "HR Admin")
    st.session_state["display_name"] = display_name
    st.divider()
    st.caption("Demo build · Local SQLite storage")

st.markdown(f"""
<div class="hero">
  <h1>👋 Welcome to Intern Mentor</h1>
  <p>Assign meaningful work, learn with an AI-style mentor, submit projects, and review progress — all in one workspace.</p>
</div>
""", unsafe_allow_html=True)

# ------------------------------ Mentor -------------------------------------
def mentor_reply(question: str, context: str = "") -> str:
    """Use OpenAI if configured; otherwise provide a useful offline response."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    try:
        if not api_key and hasattr(st, "secrets"):
            api_key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        pass
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            result = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a supportive internship mentor. Explain concepts simply, give step-by-step guidance, ask clarifying questions when needed, and do not claim to execute or verify code you have not run. For project submissions, provide constructive review feedback."},
                    {"role": "user", "content": f"Context: {context}\nQuestion: {question}"}
                ], temperature=0.4)
            return result.choices[0].message.content or "I couldn't generate a response. Please try again."
        except Exception as exc:
            return "I couldn't reach the configured AI service, so here is an offline suggestion instead.\n\n" + offline_reply(question) + f"\n\n*Technical note: {type(exc).__name__}. Check your API key, network, and model settings.*"
    return offline_reply(question)

def offline_reply(q: str) -> str:
    text = q.lower()
    if any(k in text for k in ["resume", "cv", "linkedin"]):
        return "**Try this approach:**\n1. Start with a clear action verb.\n2. Mention the tool or technology you used.\n3. Describe the outcome with a measurable result where possible.\n4. Keep each bullet concise and be ready to explain your contribution.\n\nShare the role and your current draft if you'd like a tailored revision."
    if any(k in text for k in ["error", "bug", "exception", "not working", "traceback"]):
        return "Let's debug it step by step:\n1. Read the first error line and identify the file/line number.\n2. Reproduce the issue with the smallest example.\n3. Check variable names, input types, imports, and configuration.\n4. Fix one issue at a time and rerun the test.\n\nPaste the complete error message and the relevant code (remove passwords/API keys) and I'll help narrow it down."
    if any(k in text for k in ["python", "streamlit", "code", "program", "project", "build"]):
        return "A good workflow is **Plan → Build a small version → Test → Improve → Document**. Break the requirement into small functions, use meaningful names, validate inputs, and test both normal and edge cases. Add a README with setup steps and screenshots.\n\nTell me your current level, goal, and any error or requirement, and we can work through it together."
    if any(k in text for k in ["interview", "aptitude", "placement"]):
        return "For preparation, use a short daily cycle: **learn one concept → solve 5–10 questions → review mistakes → explain the idea aloud**. Practise a concise introduction and prepare examples that show your own contribution, problem-solving, and learning. Share the job description to make a focused plan."
    return "I'm your learning mentor. I can help you break a task into steps, understand concepts, debug code, plan a project, improve documentation, and prepare for reviews.\n\n**To get a useful answer, include:** your goal, what you've tried, the result you expected, and the error/output you received. Please don't share passwords, API keys, or private company data."

# ------------------------------ Intern portal ------------------------------
if role == "Intern Portal":
    tabs = st.tabs(["📌 My Tasks", "💬 AI Mentor", "📤 Submit Project", "📈 My Progress"])
    with tabs[0]:
        st.subheader("Tasks assigned to you")
        all_tasks = rows("SELECT * FROM tasks WHERE lower(assignee)=lower(?) OR lower(assignee)='all interns' ORDER BY id DESC", (display_name,))
        submissions = rows("SELECT * FROM submissions WHERE lower(intern)=lower(?) ORDER BY id DESC", (display_name,))
        submitted_task_ids = {r["task_id"] for r in submissions}
        c1,c2,c3 = st.columns(3)
        c1.metric("Assigned", len(all_tasks))
        c2.metric("Submitted", sum(1 for t in all_tasks if t["id"] in submitted_task_ids))
        c3.metric("Pending", sum(1 for t in all_tasks if t["id"] not in submitted_task_ids))
        if not all_tasks:
            st.info("No tasks assigned yet. Switch to the HR Portal to create a demo task.")
        for task in all_tasks:
            with st.container(border=True):
                left, right = st.columns([4,1])
                with left:
                    st.markdown(f"**{task['title']}**  ·  `{task['priority']}`")
                    st.write(task["description"])
                    st.caption(f"Due: {task['due_date'] or 'Not set'} · Assigned by {task['created_by']}")
                with right:
                    st.markdown("✅ Submitted" if task["id"] in submitted_task_ids else "🟡 In progress")
    with tabs[1]:
        st.subheader("Your AI learning mentor")
        st.write("Ask questions about coding, project planning, documentation, debugging, or internship skills.")
        if not (os.getenv("OPENAI_API_KEY") or (hasattr(st, "secrets") and st.secrets.get("OPENAI_API_KEY", ""))):
            st.info("Offline mentor mode is active. Add OPENAI_API_KEY to enable AI-generated responses.")
        with st.form("mentor_form", clear_on_submit=True):
            question = st.text_area("What would you like help with?", placeholder="Example: Explain how to structure a Streamlit project...", height=110)
            submitted = st.form_submit_button("Ask mentor", type="primary")
        if submitted and question.strip():
            answer = mentor_reply(question.strip(), context=f"User: {display_name}; portal: Intern")
            execute("INSERT INTO chat_history(user_name,role,question,answer,created_at) VALUES(?,?,?,?,?)", (display_name,"Intern",question.strip(),answer,datetime.now().isoformat(timespec="seconds")))
            st.session_state["last_mentor_answer"] = answer
            st.session_state["last_mentor_question"] = question.strip()
        if st.session_state.get("last_mentor_answer"):
            st.markdown("#### Mentor response")
            st.markdown(st.session_state["last_mentor_answer"])
        history = rows("SELECT question,answer,created_at FROM chat_history WHERE lower(user_name)=lower(?) ORDER BY id DESC LIMIT 5", (display_name,))
        if history:
            with st.expander("Recent questions"):
                for h in history:
                    st.markdown(f"**You:** {h['question']}\n\n**Mentor:** {h['answer']}")
                    st.caption(h["created_at"])
    with tabs[2]:
        st.subheader("Submit your work")
        task_options = {f"#{t['id']} · {t['title']} (due {t['due_date'] or 'not set'})": t["id"] for t in all_tasks}
        if not task_options:
            st.warning("You need an assigned task before submitting. Ask HR to create one.")
        else:
            with st.form("submission_form"):
                chosen_label = st.selectbox("Select task", list(task_options.keys()))
                notes = st.text_area("What did you complete?", placeholder="Summarize your approach, files changed, tests run, and any blockers.", height=130)
                uploaded = st.file_uploader("Attach project ZIP or source file", type=["zip","py","txt","md","html","css","js","java","c","cpp","ino","pdf"])
                submit_work = st.form_submit_button("Submit work", type="primary")
            if submit_work:
                task_id = task_options[chosen_label]
                file_name, file_path = None, None
                if uploaded:
                    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", uploaded.name)
                    dest = UPLOAD_DIR / f"task{task_id}_{re.sub(r'[^A-Za-z0-9_-]', '_', display_name)}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"
                    dest.write_bytes(uploaded.getvalue())
                    file_name, file_path = uploaded.name, str(dest.relative_to(APP_DIR))
                execute("INSERT INTO submissions(task_id,intern,notes,file_name,file_path,submitted_at,status) VALUES(?,?,?,?,?,?,?)", (task_id,display_name,notes.strip(),file_name,file_path,datetime.now().isoformat(timespec="seconds"),"Submitted"))
                execute("UPDATE tasks SET status='Submitted' WHERE id=?", (task_id,))
                st.success("Submission saved! HR can review it from the HR Portal.")
    with tabs[3]:
        st.subheader("Progress overview")
        mine = rows("SELECT s.*,t.title AS task_title FROM submissions s LEFT JOIN tasks t ON t.id=s.task_id WHERE lower(s.intern)=lower(?) ORDER BY s.id DESC", (display_name,))
        if mine:
            for item in mine:
                with st.container(border=True):
                    st.markdown(f"**{item['task_title'] or 'Task'}** · {item['status']}")
                    st.caption(f"Submitted: {item['submitted_at']}")
                    if item["file_name"]: st.write(f"Attachment: `{item['file_name']}`")
                    if item["score"] is not None: st.metric("Review score", f"{item['score']}/100")
                    if item["review"]: st.write(item["review"])
        else:
            st.info("Your submissions and review feedback will appear here.")

# ------------------------------ HR portal ----------------------------------
else:
    tabs = st.tabs(["📊 Overview", "📝 Create Task", "🧾 Review Submissions", "💬 Mentor Console"])
    with tabs[0]:
        tasks = rows("SELECT * FROM tasks ORDER BY id DESC")
        subs = rows("SELECT * FROM submissions ORDER BY id DESC")
        pending = [s for s in subs if s["status"] == "Submitted"]
        a,b,c,d = st.columns(4)
        a.metric("Total tasks", len(tasks)); b.metric("Submissions", len(subs)); c.metric("Awaiting review", len(pending)); d.metric("Reviewed", sum(1 for s in subs if s["status"] == "Reviewed"))
        st.subheader("Recent tasks")
        if tasks:
            st.dataframe([{"ID":t["id"],"Task":t["title"],"Intern":t["assignee"],"Due date":t["due_date"] or "—","Priority":t["priority"],"Status":t["status"]} for t in tasks[:12]], use_container_width=True, hide_index=True)
        else:
            st.info("Create your first task in the Create Task tab.")
        st.subheader("Submission activity")
        if subs:
            st.dataframe([{"Intern":s["intern"],"Task ID":s["task_id"],"Submitted":s["submitted_at"],"Status":s["status"],"Score":s["score"] if s["score"] is not None else "—"} for s in subs[:10]], use_container_width=True, hide_index=True)
    with tabs[1]:
        st.subheader("Create and assign a task")
        with st.form("create_task_form", clear_on_submit=True):
            title = st.text_input("Task title", placeholder="Example: Build a student attendance dashboard")
            description = st.text_area("Requirements and expected outcome", height=140, placeholder="Describe the goal, required features, deliverables, and acceptance criteria.")
            col1,col2,col3 = st.columns(3)
            with col1: assignee = st.text_input("Assign to", value="Sri", help="Use an intern's name or 'All Interns'.")
            with col2: due = st.date_input("Due date", value=date.today())
            with col3: priority = st.selectbox("Priority", ["Low","Medium","High","Urgent"], index=1)
            create = st.form_submit_button("Create task", type="primary")
        if create:
            if not title.strip() or not description.strip() or not assignee.strip():
                st.error("Please enter a title, requirements, and assignee.")
            else:
                execute("INSERT INTO tasks(title,description,assignee,due_date,priority,created_by,created_at,status) VALUES(?,?,?,?,?,?,?,?)", (title.strip(),description.strip(),assignee.strip(),due.isoformat(),priority,display_name,datetime.now().isoformat(timespec="seconds"),"Assigned"))
                st.success(f"Task assigned to {assignee.strip()}.")
                st.rerun()
    with tabs[2]:
        st.subheader("Review intern submissions")
        subs = rows("SELECT s.*,t.title AS task_title,t.description AS task_description FROM submissions s LEFT JOIN tasks t ON t.id=s.task_id ORDER BY s.id DESC")
        if not subs:
            st.info("No submissions yet. They will appear here when interns submit their work.")
        for sub in subs:
            with st.expander(f"{sub['intern']} · {sub['task_title'] or 'Task'} · {sub['status']} · #{sub['id']}", expanded=(sub["status"]=="Submitted")):
                st.markdown(f"**Task requirements:** {sub['task_description'] or '—'}")
                st.markdown("**Intern notes**")
                st.write(sub["notes"] or "No notes provided.")
                if sub["file_name"]:
                    path = APP_DIR / (sub["file_path"] or "")
                    st.write(f"Attachment: `{sub['file_name']}`")
                    if path.exists():
                        st.download_button("Download attachment", data=path.read_bytes(), file_name=sub["file_name"], key=f"download_{sub['id']}")
                        if path.suffix.lower() == ".zip":
                            try:
                                with zipfile.ZipFile(path) as zf:
                                    names = zf.namelist()
                                    st.caption(f"ZIP contains {len(names)} entries")
                                    st.code("\n".join(names[:80]) + ("\n..." if len(names)>80 else ""), language="text")
                            except zipfile.BadZipFile:
                                st.warning("The uploaded file does not appear to be a valid ZIP archive.")
                with st.form(f"review_{sub['id']}"):
                    current_score = int(sub["score"]) if sub["score"] is not None else 80
                    score = st.slider("Score", min_value=0, max_value=100, value=current_score, key=f"score_{sub['id']}")
                    review = st.text_area("Feedback", value=sub["review"] or "", key=f"review_text_{sub['id']}", placeholder="Mention strengths, improvement areas, and next steps.")
                    reviewed = st.form_submit_button("Save review")
                if reviewed:
                    execute("UPDATE submissions SET score=?,review=?,status='Reviewed' WHERE id=?", (score,review.strip(),sub["id"]))
                    st.success("Review saved and visible to the intern.")
                    st.rerun()
    with tabs[3]:
        st.subheader("Ask the mentor for review guidance")
        st.caption("Use this to draft rubric ideas, suggest next steps, or prepare constructive feedback. This does not automatically evaluate submissions.")
        with st.form("hr_mentor_form", clear_on_submit=True):
            prompt = st.text_area("Question", placeholder="Example: Create a fair 100-point rubric for a beginner Python dashboard project.", height=100)
            ask = st.form_submit_button("Ask mentor", type="primary")
        if ask and prompt.strip():
            answer = mentor_reply(prompt.strip(), context=f"User: {display_name}; portal: HR. Help HR mentor interns constructively.")
            execute("INSERT INTO chat_history(user_name,role,question,answer,created_at) VALUES(?,?,?,?,?)", (display_name,"HR",prompt.strip(),answer,datetime.now().isoformat(timespec="seconds")))
            st.session_state["hr_mentor_answer"] = answer
        if st.session_state.get("hr_mentor_answer"):
            st.markdown("#### Mentor response")
            st.markdown(st.session_state["hr_mentor_answer"])

st.divider()
with st.expander("ℹ️ Setup notes and demo limitations"):
    st.markdown("""
- This is a starter/demo application. The portal switch is **not authentication**; anyone running the app can switch roles.
- Tasks, submissions, and reviews are stored in a local SQLite database in `data/mentor.db`.
- The mentor uses helpful offline responses by default. To enable generated AI responses, set `OPENAI_API_KEY` in your environment or Streamlit secrets.
- Uploaded files are saved under `data/submissions/`. Do not deploy publicly without authentication, upload limits, access controls, and secure file handling.
- ZIP uploads are listed for review; this app does not run uploaded code.
""")
