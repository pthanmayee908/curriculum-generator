import streamlit as st
import requests
import json
import random

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(page_title="AI Academic Planning System", layout="wide")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "granite3.3:2b"

# =====================================================
# AI JSON CALL
# =====================================================

def call_ai(prompt, temperature=0.2):
    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature}
        }

        response = requests.post(OLLAMA_URL, json=payload)

        if response.status_code != 200:
            st.error("AI request failed")
            st.code(response.text)
            return None

        result = response.json()
        text = result.get("response", "").strip()

        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()

        return json.loads(text)

    except Exception:
        st.error("Invalid JSON returned by AI")
        if 'text' in locals():
            st.code(text)
        return None


# =====================================================
# SESSION STATE INIT
# =====================================================

for key in [
    "page",
    "user_data",
    "capability",
    "roadmap",
    "approved",
    "current_semester"
]:
    if key not in st.session_state:
        st.session_state[key] = None

if not st.session_state.page:
    st.session_state.page = "User Input"


# =====================================================
# PAGE 1 — USER INPUT & CAPABILITY
# =====================================================

def page_user_input():

    st.title("🎓 AI Academic Planning & Execution System")

    with st.form("user_form"):

        degree = st.selectbox("Degree Type", ["B.Tech", "MBA", "MSc", "BSc"])
        domain = st.text_input("Domain")
        focus = st.text_input("Focus Area")
        level = st.selectbox("Current Knowledge Level", ["Beginner", "Intermediate", "Advanced"])
        duration = st.number_input("Duration (Years)", 1, 6, 4)
        weekly = st.number_input("Weekly Study Hours", 5, 60, 20)

        submit = st.form_submit_button("Predict Capability")

    if submit:

        total_hours = duration * 52 * weekly

        st.session_state.user_data = {
            "degree": degree,
            "domain": domain,
            "focus": focus,
            "level": level,
            "duration": duration,
            "weekly": weekly,
            "total_hours": total_hours
        }

        prompt = f"""
Respond ONLY in valid JSON.

Predict achievable academic level.

Degree: {degree}
Domain: {domain}
Focus: {focus}
Current Level: {level}
Total Study Hours: {total_hours}

{{
 "predicted_level":"",
 "reason":""
}}
"""

        result = call_ai(prompt)

        if result:
            st.session_state.capability = result
            st.success("Capability Predicted")
            st.json(result)

            if st.button("Next → Course Planning"):
                st.session_state.page = "Course Planning"
                st.rerun()


# =====================================================
# PAGE 2 — INTELLIGENT COURSE PLANNING
# =====================================================

def generate_roadmap():

    data = st.session_state.user_data
    semesters = data["duration"] * 2

    prompt = f"""
You are an academic architect.

Respond ONLY with valid JSON.

Create structured semester roadmap.

Degree: {data['degree']}
Domain: {data['domain']}
Focus: {data['focus']}
Knowledge Level: {data['level']}
Semesters: {semesters}

Return:
{{
 "semesters":[
  {{
   "semester_number":1,
   "total_credits":20,
   "summary":"",
   "courses":[
     {{
       "name":"",
       "difficulty":"Easy/Medium/Hard",
       "credits":4,
       "prerequisites":[]
     }}
   ]
  }}
 ]
}}
"""
    return call_ai(prompt)


def page_course_planning():

    st.title("📘 Intelligent Course Planning")

    if not st.session_state.roadmap:
        if st.button("Generate AI Roadmap"):
            roadmap = generate_roadmap()
            if roadmap:
                st.session_state.roadmap = roadmap
                st.success("Roadmap Generated")

    if st.session_state.roadmap:

        roadmap = st.session_state.roadmap

        for sem in roadmap["semesters"]:
            st.subheader(f"Semester {sem['semester_number']}")
            st.write("Credits:", sem["total_credits"])
            st.write("Summary:", sem["summary"])
            for c in sem["courses"]:
                st.write("•", c["name"])

        st.divider()
        st.subheader("➕ Modify or Add Course (AI Chatbot)")

        user_course = st.text_input("Suggest a course to add or modify")

        if st.button("Ask AI to Validate & Add"):

            prompt = f"""
Respond ONLY in JSON.

Current Curriculum:
{json.dumps(roadmap)}

User Suggestion:
{user_course}

You must:
- Check duplicates
- Validate prerequisites
- Adjust semester if needed
- Maintain balanced workload

Return updated roadmap in same structure.
"""

            updated = call_ai(prompt)

            if updated:
                st.session_state.roadmap = updated
                st.success("Curriculum Updated")

        if st.button("Approve & Continue"):
            st.session_state.approved = True
            st.session_state.page = "Dashboard"
            st.rerun()


# =====================================================
# PAGE 3 — DASHBOARD
# =====================================================

def page_dashboard():

    st.title("📊 Semester Overview Dashboard")

    roadmap = st.session_state.roadmap

    if not roadmap:
        st.warning("No roadmap found.")
        return

    for sem in roadmap["semesters"]:
        st.subheader(f"Semester {sem['semester_number']}")
        st.write("Total Credits:", sem["total_credits"])
        st.write("Main Focus:", sem["summary"])

        if st.button(
            f"Open Semester {sem['semester_number']}",
            key=f"open_{sem['semester_number']}"
        ):
            st.session_state.current_semester = sem
            st.session_state.page = "Semester View"
            st.rerun()


# =====================================================
# PAGE 4 — SEMESTER VIEW
# =====================================================

def generate_sessions(course_name):

    prompt = f"""
Respond ONLY in JSON.

Break course into progressive sessions.

Course: {course_name}

{{
 "sessions":[
  {{
   "session_number":1,
   "topic":"",
   "description":""
  }}
 ]
}}
"""
    return call_ai(prompt)


def generate_timetable(courses, weekly_hours):

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    table = {d: [] for d in days}

    if not courses:
        return table

    per_course = weekly_hours / len(courses)

    for c in courses:
        chosen = random.sample(days, 2)
        for d in chosen:
            table[d].append({
                "course": c["name"],
                "hours": round(per_course / 2, 1)
            })

    return table


def page_semester_view():

    sem = st.session_state.current_semester

    if not sem:
        st.warning("No semester selected.")
        return

    st.title(f"Semester {sem['semester_number']}")

    tab1, tab2 = st.tabs(["Subjects", "Timetable"])

    with tab1:
        for c in sem["courses"]:
            with st.expander(c["name"]):

                if st.button(
                    f"Generate Sessions for {c['name']}",
                    key=f"sess_{c['name']}"
                ):
                    sessions = generate_sessions(c["name"])
                    if sessions:
                        st.json(sessions)

    with tab2:
        table = generate_timetable(
            sem["courses"],
            st.session_state.user_data["weekly"]
        )
        st.json(table)


# =====================================================
# NAVIGATION
# =====================================================

pages = [
    "User Input",
    "Course Planning",
    "Dashboard",
    "Semester View"
]

page = st.sidebar.radio(
    "Navigate",
    pages,
    index=pages.index(st.session_state.page)
)

st.session_state.page = page

if page == "User Input":
    page_user_input()

elif page == "Course Planning":
    page_course_planning()

elif page == "Dashboard":
    page_dashboard()

elif page == "Semester View":
    page_semester_view()
