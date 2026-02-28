import streamlit as st
import requests
import json
import random

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

st.set_page_config(page_title="AI Academic Ecosystem", layout="wide")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "granite3.3:2b"

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "user_data" not in st.session_state:
    st.session_state.user_data = None

if "roadmap" not in st.session_state:
    st.session_state.roadmap = None

if "approved" not in st.session_state:
    st.session_state.approved = False

if "current_semester" not in st.session_state:
    st.session_state.current_semester = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_store" not in st.session_state:
    st.session_state.session_store = {}

# --------------------------------------------------
# OLLAMA CALL (JSON)
# --------------------------------------------------

def call_ai(prompt):

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
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


# --------------------------------------------------
# NORMAL CHAT CALL
# --------------------------------------------------

def call_chat(prompt):

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]


# --------------------------------------------------
# SESSION GENERATOR
# --------------------------------------------------

def generate_sessions(course):

    prompt = f"""
Return only JSON.

Break the course into 6 learning sessions.

Course: {course}

Format:
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


# --------------------------------------------------
# TIMETABLE GENERATOR
# --------------------------------------------------

def generate_timetable(session_data):

    days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]

    timetable = {d: [] for d in days}

    topics = []

    for course in session_data:
        for s in session_data[course]:
            topics.append({
                "course": course,
                "topic": s["topic"]
            })

    i = 0
    for t in topics:
        day = days[i % len(days)]
        timetable[day].append(t)
        i += 1

    return timetable


# --------------------------------------------------
# PAGE 1 INPUT
# --------------------------------------------------

def page_input():

    st.title("🎓 AI Academic Planner")

    with st.form("input_form"):

        degree = st.selectbox("Degree", ["B.Tech", "MBA", "BSc", "MSc"])
        domain = st.text_input("Domain")
        focus = st.text_input("Focus Area")
        level = st.selectbox("Knowledge Level", ["Beginner","Intermediate","Advanced"])
        duration = st.number_input("Duration (Years)",1,6,4)
        weekly = st.number_input("Weekly Study Hours",5,60,20)

        submit = st.form_submit_button("Save Details")

    if submit:

        st.session_state.user_data = {
            "degree": degree,
            "domain": domain,
            "focus": focus,
            "level": level,
            "duration": duration,
            "weekly": weekly
        }

        st.success("Details Saved")


# --------------------------------------------------
# ROADMAP GENERATOR
# --------------------------------------------------

def generate_roadmap():

    data = st.session_state.user_data
    semesters = data["duration"] * 2

    prompt = f"""
Return only JSON.

Generate roadmap.

Degree: {data['degree']}
Domain: {data['domain']}
Focus: {data['focus']}
Semesters: {semesters}

Format:
{{
 "semesters":[
   {{
    "semester_number":1,
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


# --------------------------------------------------
# PAGE 2 COURSE PLANNER
# --------------------------------------------------

def page_course_planner():

    st.title("📚 Course Planner")

    if not st.session_state.user_data:
        st.warning("Complete User Input first")
        return

    if st.button("Generate Roadmap"):

        st.session_state.roadmap = generate_roadmap()
        st.session_state.approved = False

    roadmap = st.session_state.roadmap

    if roadmap:

        for sem in roadmap["semesters"]:

            st.subheader(f"Semester {sem['semester_number']}")

            for c in sem["courses"]:
                st.write("-", c["name"])

        if st.button("Approve Roadmap"):
            st.session_state.approved = True
            st.success("Roadmap Approved")


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

def page_dashboard():

    st.title("📊 Semester Dashboard")

    if not st.session_state.approved:
        st.warning("Approve roadmap first")
        return

    for sem in st.session_state.roadmap["semesters"]:

        st.subheader(f"Semester {sem['semester_number']}")

        if st.button(f"Open Semester {sem['semester_number']}"):
            st.session_state.current_semester = sem
            st.rerun()


# --------------------------------------------------
# SEMESTER VIEW
# --------------------------------------------------

def page_semester():

    if not st.session_state.current_semester:
        st.warning("Open semester from dashboard")
        return

    sem = st.session_state.current_semester

    st.title(f"Semester {sem['semester_number']}")

    tab1, tab2, tab3 = st.tabs(["Subjects","Sessions","Timetable"])

    # SUBJECTS
    with tab1:
        for c in sem["courses"]:
            st.write("•", c["name"])

    # SESSIONS
    with tab2:

        for c in sem["courses"]:

            if st.button(f"Generate Sessions - {c['name']}"):

                result = generate_sessions(c["name"])

                if result:
                    st.json(result)
                    st.session_state.session_store[c["name"]] = result["sessions"]

    # TIMETABLE (UPDATED UI)
    with tab3:

        if not st.session_state.session_store:
            st.warning("Generate sessions first")

        else:
            table = generate_timetable(st.session_state.session_store)

            st.subheader("📅 Weekly Study Timetable")

            for day in table:

                st.markdown(f"### {day}")

                if len(table[day]) == 0:
                    st.write("No topics scheduled")

                for item in table[day]:
                    st.write(f"• {item['course']} → {item['topic']}")

                st.markdown("---")


# --------------------------------------------------
# CHATBOT
# --------------------------------------------------

def page_chatbot():

    st.title("🤖 AI Academic Chatbot")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask anything...")

    if prompt:

        st.session_state.messages.append({"role":"user","content":prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        reply = call_chat(prompt)

        with st.chat_message("assistant"):
            st.markdown(reply)

        st.session_state.messages.append(
            {"role":"assistant","content":reply}
        )


# --------------------------------------------------
# NAVIGATION
# --------------------------------------------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Go To",
    [
        "User Input",
        "Course Planner",
        "Dashboard",
        "Semester View",
        "AI Chatbot"
    ]
)

if page == "User Input":
    page_input()

elif page == "Course Planner":
    page_course_planner()

elif page == "Dashboard":
    page_dashboard()

elif page == "Semester View":
    page_semester()

elif page == "AI Chatbot":
    page_chatbot()