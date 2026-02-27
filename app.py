import streamlit as st
import google.generativeai as genai
import os
import json
import random

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

st.set_page_config(page_title="AI Academic Planner", layout="wide")

# Configure Gemini API
genai.configure(api_key=os.getenv("AIzaSyDqFRVUulQM_ne8BRBbXRc6kLgVEKItUfU"))

model_pro = genai.GenerativeModel("gemini-1.5-pro")
model_flash = genai.GenerativeModel("gemini-1.5-flash")

# --------------------------------------------------
# SESSION STATE INIT
# --------------------------------------------------

if "roadmap" not in st.session_state:
    st.session_state.roadmap = None

if "user_data" not in st.session_state:
    st.session_state.user_data = None

if "current_semester" not in st.session_state:
    st.session_state.current_semester = None

if "capability" not in st.session_state:
    st.session_state.capability = None


# --------------------------------------------------
# SAFE GEMINI JSON CALL
# --------------------------------------------------

def call_gemini_json(prompt, model=model_pro):
    response = model.generate_content(prompt)
    text = response.text.strip()

    # Remove markdown wrapping if exists
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    return json.loads(text)


# --------------------------------------------------
# PAGE 1 – USER INPUT
# --------------------------------------------------

def page_user_input():
    st.title("🎓 AI Academic Planning System")

    with st.form("input_form"):
        degree = st.selectbox("Degree Type", ["B.Tech", "MBA", "Master's"])
        domain = st.text_input("Domain")
        focus = st.text_input("Focus Area")
        level = st.selectbox("Current Knowledge Level", ["Beginner", "Intermediate", "Advanced"])
        duration = st.number_input("Duration (Years)", 1, 6, 4)
        weekly_hours = st.number_input("Weekly Study Hours", 5, 60, 20)

        submit = st.form_submit_button("Predict Capability")

    if submit:
        total_hours = duration * 52 * weekly_hours

        st.session_state.user_data = {
            "degree": degree,
            "domain": domain,
            "focus": focus,
            "level": level,
            "duration": duration,
            "weekly_hours": weekly_hours,
            "total_hours": total_hours
        }

        prompt = f"""
        Return ONLY valid JSON.
        No markdown.
        No explanation.

        Based on:
        Degree: {degree}
        Domain: {domain}
        Focus: {focus}
        Current Level: {level}
        Total Study Hours: {total_hours}

        Return:
        {{
            "predicted_level": "",
            "reasoning": ""
        }}
        """

        result = call_gemini_json(prompt)

        st.session_state.capability = result
        st.success("Capability Predicted")
        st.json(result)


# --------------------------------------------------
# PAGE 2 – ROADMAP GENERATION
# --------------------------------------------------

def generate_roadmap():
    data = st.session_state.user_data
    semesters = data["duration"] * 2

    prompt = f"""
    Return ONLY valid JSON.
    No markdown.
    No explanation.

    Generate semester-wise roadmap.

    Degree: {data['degree']}
    Domain: {data['domain']}
    Focus: {data['focus']}
    Semesters: {semesters}

    Format:
    {{
      "semesters": [
        {{
          "semester_number": 1,
          "credits": 20,
          "focus_summary": "",
          "courses": [
            {{
              "name": "",
              "credits": 4,
              "difficulty": "Easy/Medium/Hard",
              "prerequisites": []
            }}
          ]
        }}
      ]
    }}
    """

    return call_gemini_json(prompt)


def page_course_planner():
    st.title("📚 Intelligent Course Planner")

    if not st.session_state.user_data:
        st.warning("Complete Page 1 first.")
        return

    if st.button("Generate Roadmap"):
        st.session_state.roadmap = generate_roadmap()
        st.success("Roadmap Generated")

    if st.session_state.roadmap:
        st.json(st.session_state.roadmap)


# --------------------------------------------------
# PAGE 3 – DASHBOARD
# --------------------------------------------------

def page_dashboard():
    st.title("📊 Semester Overview")

    roadmap = st.session_state.roadmap

    if not roadmap:
        st.warning("Generate roadmap first.")
        return

    for sem in roadmap["semesters"]:
        st.subheader(f"Semester {sem['semester_number']}")
        st.write(f"Credits: {sem['credits']}")
        st.write(f"Focus: {sem['focus_summary']}")

        if st.button(f"Open Semester {sem['semester_number']}"):
            st.session_state.current_semester = sem
            st.rerun()


# --------------------------------------------------
# SESSION BREAKDOWN
# --------------------------------------------------

def generate_sessions(course_name):
    prompt = f"""
    Return ONLY valid JSON.
    No markdown.
    No explanation.

    Break the course into sessions.

    Course: {course_name}

    {{
      "sessions": [
        {{
          "session_number": 1,
          "topic": "",
          "description": ""
        }}
      ]
    }}
    """

    return call_gemini_json(prompt, model=model_flash)


# --------------------------------------------------
# TIMETABLE GENERATION (PURE PYTHON)
# --------------------------------------------------

def generate_timetable(courses, weekly_hours):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    timetable = {day: [] for day in days}

    if not courses:
        return timetable

    hours_per_course = weekly_hours // len(courses)

    for course in courses:
        chosen_days = random.sample(days, 2)

        for day in chosen_days:
            timetable[day].append({
                "course": course["name"],
                "hours": max(1, hours_per_course // 2)
            })

    return timetable


# --------------------------------------------------
# PAGE 4 – SEMESTER VIEW
# --------------------------------------------------

def page_semester_view():
    sem = st.session_state.current_semester

    if not sem:
        st.warning("Select a semester from Dashboard.")
        return

    st.title(f"📘 Semester {sem['semester_number']}")

    tab1, tab2 = st.tabs(["Subjects", "Timetable"])

    with tab1:
        for course in sem["courses"]:
            with st.expander(course["name"]):
                if st.button(f"Generate Sessions - {course['name']}"):
                    sessions = generate_sessions(course["name"])
                    st.json(sessions)

    with tab2:
        timetable = generate_timetable(
            sem["courses"],
            st.session_state.user_data["weekly_hours"]
        )
        st.json(timetable)


# --------------------------------------------------
# NAVIGATION
# --------------------------------------------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Go to",
    ["User Input", "Course Planner", "Dashboard", "Semester View"]
)

if page == "User Input":
    page_user_input()

elif page == "Course Planner":
    page_course_planner()

elif page == "Dashboard":
    page_dashboard()

elif page == "Semester View":
    page_semester_view()