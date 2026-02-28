import streamlit as st
import requests
import json
import random

# -----------------------------
# CONFIG
# -----------------------------

st.set_page_config(page_title="AI Academic Ecosystem", layout="wide")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "granite3.3:2b"

# -----------------------------
# SESSION STATE
# -----------------------------

if "user_data" not in st.session_state:
    st.session_state.user_data = None

if "roadmap" not in st.session_state:
    st.session_state.roadmap = None

if "approved" not in st.session_state:
    st.session_state.approved = False

if "current_semester" not in st.session_state:
    st.session_state.current_semester = None


# -----------------------------
# OLLAMA JSON CALL
# -----------------------------

def call_ai(prompt):
    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": prompt, "stream": False}
    )
    text = response.json()["response"]

    try:
        start = text.find("{")
        end = text.rfind("}")
        clean = text[start:end+1]
        return json.loads(clean)
    except:
        st.error("AI returned invalid JSON")
        st.code(text)
        return None


# -----------------------------
# VALIDATION LOGIC
# -----------------------------

def validate_and_balance(roadmap):
    all_courses = set()

    for sem in roadmap["semesters"]:
        filtered = []
        for c in sem["courses"]:
            if c["name"] not in all_courses:
                filtered.append(c)
                all_courses.add(c["name"])
        sem["courses"] = filtered

    return roadmap


# -----------------------------
# PAGE 1 — INPUT
# -----------------------------

def page_input():

    st.title("🎓 AI Academic Planner")

    with st.form("input_form"):
        degree = st.selectbox("Degree", ["B.Tech", "MBA", "BSc", "MSc"])
        domain = st.text_input("Domain")
        focus = st.text_input("Focus Area")
        level = st.selectbox("Knowledge Level", ["Beginner", "Intermediate", "Advanced"])
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
Return only JSON.

Based on:
Degree: {degree}
Domain: {domain}
Focus: {focus}
Level: {level}
Total Hours: {total_hours}

Return:
{{
  "predicted_level": "",
  "reason": ""
}}
"""

        result = call_ai(prompt)

        if result:
            st.success("Capability Predicted")
            st.json(result)


# -----------------------------
# ROADMAP GENERATION
# -----------------------------

def generate_roadmap():

    data = st.session_state.user_data
    semesters = data["duration"] * 2

    prompt = f"""
Return only JSON.

Generate structured roadmap.

Separate:
- mandatory_courses
- recommended_courses

Degree: {data['degree']}
Domain: {data['domain']}
Focus: {data['focus']}
Semesters: {semesters}

Format:
{{
 "semesters": [
   {{
     "semester_number": 1,
     "mandatory_courses": [],
     "recommended_courses": [],
     "courses": [
       {{
         "name": "",
         "difficulty": "Easy/Medium/Hard",
         "credits": 4,
         "prerequisites": []
       }}
     ]
   }}
 ]
}}
"""

    result = call_ai(prompt)
    if result:
        return validate_and_balance(result)
    return None


# -----------------------------
# PAGE 2 — COURSE PLANNER
# -----------------------------

def page_course_planner():

    st.title("📚 Intelligent Course Planner")

    if not st.session_state.user_data:
        st.warning("Complete Page 1 first")
        return

    if st.button("Generate AI Roadmap"):
        st.session_state.roadmap = generate_roadmap()
        st.session_state.approved = False

    roadmap = st.session_state.roadmap

    if roadmap:
        for sem in roadmap["semesters"]:
            st.subheader(f"Semester {sem['semester_number']}")

            st.write("🔒 Mandatory:", sem["mandatory_courses"])
            st.write("⭐ Recommended:", sem["recommended_courses"])

            for course in sem["courses"]:
                st.write(f"- {course['name']} ({course['difficulty']})")

        # Add / Modify Course
        st.markdown("---")
        new_course = st.text_input("Suggest New Course")

        if st.button("Ask AI To Add Course"):
            prompt = f"""
Return only JSON.

User wants to add: {new_course}

Check:
- Duplicate
- Prerequisite logic
- Balance workload

Return:
{{
  "semester_number": ,
  "course": {{
    "name": "",
    "difficulty": "",
    "credits": 4,
    "prerequisites": []
  }},
  "reason": ""
}}
"""
            result = call_ai(prompt)

            if result:
                st.write("AI Opinion:", result["reason"])
                if st.button("Confirm Add"):
                    for sem in roadmap["semesters"]:
                        if sem["semester_number"] == result["semester_number"]:
                            sem["courses"].append(result["course"])

        if st.button("Approve Roadmap"):
            st.session_state.approved = True
            st.success("Roadmap Approved")


# -----------------------------
# PAGE 3 — DASHBOARD
# -----------------------------

def page_dashboard():

    st.title("📊 Semester Dashboard")

    if not st.session_state.approved:
        st.warning("Approve roadmap first")
        return

    roadmap = st.session_state.roadmap

    for sem in roadmap["semesters"]:
        st.subheader(f"Semester {sem['semester_number']}")
        st.write("Total Subjects:", len(sem["courses"]))

        if st.button(f"Open Semester {sem['semester_number']}"):
            st.session_state.current_semester = sem
            st.rerun()


# -----------------------------
# SESSION GENERATION
# -----------------------------

def generate_sessions(course):
    prompt = f"""
Return only JSON.

Break into sessions.

Course: {course}

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


# -----------------------------
# SMART TIMETABLE
# -----------------------------

def generate_timetable(courses, weekly_hours):

    days = ["Mon","Tue","Wed","Thu","Fri","Sat"]
    table = {d: [] for d in days}

    total_courses = len(courses)
    hours_per = weekly_hours // max(1,total_courses)

    for c in courses:
        chosen = random.sample(days, 2)
        for d in chosen:
            table[d].append({
                "course": c["name"],
                "hours": hours_per // 2
            })

    return table


# -----------------------------
# PAGE 4 — SEMESTER VIEW
# -----------------------------

def page_semester():

    sem = st.session_state.current_semester

    if not sem:
        st.warning("Open a semester first")
        return

    st.title(f"Semester {sem['semester_number']}")

    tab1, tab2 = st.tabs(["Subjects", "Timetable"])

    with tab1:
        for c in sem["courses"]:
            with st.expander(c["name"]):
                if st.button(f"Generate Sessions {c['name']}"):
                    sessions = generate_sessions(c["name"])
                    if sessions:
                        st.json(sessions)

    with tab2:
        table = generate_timetable(
            sem["courses"],
            st.session_state.user_data["weekly"]
        )
        st.json(table)


# -----------------------------
# NAVIGATION
# -----------------------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Go To",
    ["User Input","Course Planner","Dashboard","Semester View"]
)

if page == "User Input":
    page_input()

elif page == "Course Planner":
    page_course_planner()

elif page == "Dashboard":
    page_dashboard()

elif page == "Semester View":
    page_semester()