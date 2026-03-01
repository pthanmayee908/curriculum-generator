import streamlit as st
import google.generativeai as genai
import json
import random

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

st.set_page_config(page_title="AI Academic Planner", layout="wide")
  
genai.configure(api_key=API_KEY)

# Latest working Gemini models
model_pro = genai.GenerativeModel("gemini-1.5-pro-latest")
model_flash = genai.GenerativeModel("gemini-1.5-flash-latest")

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "user_data" not in st.session_state:
    st.session_state.user_data = None

if "roadmap" not in st.session_state:
    st.session_state.roadmap = None

if "current_semester" not in st.session_state:
    st.session_state.current_semester = None

if "capability" not in st.session_state:
    st.session_state.capability = None


# --------------------------------------------------
# SAFE GEMINI JSON FUNCTION (FIXED)
# --------------------------------------------------

def call_gemini_json(prompt, model=model_pro):

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "response_mime_type": "application/json"
            }
        )

        text = response.text.strip()

        # Remove markdown if present
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()

        # Extract JSON safely
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:
            text = text[start:end+1]

        return json.loads(text)

    except Exception as e:
        st.error("AI returned invalid JSON")
        st.write("Raw Output:")
        st.code(response.text if 'response' in locals() else "No response")
        return None


# --------------------------------------------------
# PAGE 1 – USER INPUT
# --------------------------------------------------

def page_user_input():

    st.title("🎓 AI Academic Planner")

    with st.form("form"):

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
Return ONLY valid JSON.
Do not include explanation.
Do not include markdown.

Based on:
Degree: {degree}
Domain: {domain}
Focus: {focus}
Current Level: {level}
Total Study Hours: {total_hours}

Return:
{{
 "predicted_level":"",
 "reason":""
}}
"""

        result = call_gemini_json(prompt)

        if result:
            st.session_state.capability = result
            st.success("Capability Generated")
            st.json(result)


# --------------------------------------------------
# ROADMAP GENERATION
# --------------------------------------------------

def generate_roadmap():

    data = st.session_state.user_data
    semesters = data["duration"] * 2

    prompt = f"""
Return ONLY valid JSON.
Do not include explanation.
Do not include markdown.

Generate semester roadmap.

Degree: {data['degree']}
Domain: {data['domain']}
Focus: {data['focus']}
Semesters: {semesters}

Format:
{{
 "semesters":[
  {{
   "semester_number":1,
   "credits":20,
   "focus_summary":"",
   "courses":[
     {{
       "name":"",
       "credits":4,
       "difficulty":"Easy",
       "prerequisites":[]
     }}
   ]
  }}
 ]
}}
"""

    return call_gemini_json(prompt)


# --------------------------------------------------
# PAGE 2 – COURSE PLANNER
# --------------------------------------------------

def page_course_planner():

    st.title("📚 Course Planner")

    if not st.session_state.user_data:
        st.warning("Complete Page 1 first")
        return

    if st.button("Generate AI Roadmap"):
        st.session_state.roadmap = generate_roadmap()
        st.success("Roadmap Generated")

    if st.session_state.roadmap:
        st.json(st.session_state.roadmap)


# --------------------------------------------------
# PAGE 3 – DASHBOARD
# --------------------------------------------------

def page_dashboard():

    st.title("📊 Semester Dashboard")

    roadmap = st.session_state.roadmap

    if not roadmap:
        st.warning("Generate roadmap first")
        return

    for sem in roadmap["semesters"]:

        st.subheader(f"Semester {sem['semester_number']}")
        st.write("Credits:", sem["credits"])
        st.write("Focus:", sem["focus_summary"])

        if st.button(f"Open Semester {sem['semester_number']}"):
            st.session_state.current_semester = sem
            st.rerun()


# --------------------------------------------------
# SESSION GENERATION
# --------------------------------------------------

def generate_sessions(course):

    prompt = f"""
Return ONLY valid JSON.
Do not include explanation.

Break course into sessions.

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

    return call_gemini_json(prompt, model_flash)


# --------------------------------------------------
# TIMETABLE
# --------------------------------------------------

def generate_timetable(courses, weekly_hours):

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    table = {d: [] for d in days}

    if not courses:
        return table

    per = max(1, weekly_hours // len(courses))

    for course in courses:
        chosen = random.sample(days, 2)

        for d in chosen:
            table[d].append({
                "course": course["name"],
                "hours": per // 2
            })

    return table


# --------------------------------------------------
# PAGE 4 – SEMESTER VIEW
# --------------------------------------------------

def page_semester():

    sem = st.session_state.current_semester

    if not sem:
        st.warning("Open a semester first")
        return

    st.title(f"Semester {sem['semester_number']}")

    tab1, tab2 = st.tabs(["Subjects", "Timetable"])

    with tab1:
        for course in sem["courses"]:
            with st.expander(course["name"]):
                if st.button(f"Generate Sessions {course['name']}"):
                    sessions = generate_sessions(course["name"])
                    if sessions:
                        st.json(sessions)

    with tab2:
        table = generate_timetable(
            sem["courses"],
            st.session_state.user_data["weekly"]
        )
        st.json(table)


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

    page_semester()
