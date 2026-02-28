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
# SESSION STATE INITIALIZATION
# -----------------------------
if "user_data" not in st.session_state:
    st.session_state.user_data = None

if "roadmap" not in st.session_state:
    st.session_state.roadmap = None

if "current_semester_selected" not in st.session_state:
    st.session_state.current_semester_selected = None

if "finalised_curriculum" not in st.session_state:
    st.session_state.finalised_curriculum = None

# -----------------------------
# SAFE AI CALL FUNCTION
# -----------------------------
def call_ai(prompt):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=60
        )
        text = response.json().get("response", "")
        # Attempt to parse JSON if AI returned extra text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
        else:
            st.error("AI returned invalid JSON")
            st.code(text)
            return None
    except Exception as e:
        st.error(f"Error calling AI: {e}")
        return None

# -----------------------------
# VALIDATION & DUPLICATE REMOVAL
# -----------------------------
def validate_and_balance(roadmap):
    all_courses = set()
    for sem in roadmap.get("semesters", []):
        filtered = []
        for c in sem.get("courses", []):
            if c["name"] not in all_courses:
                filtered.append(c)
                all_courses.add(c["name"])
        sem["courses"] = filtered
    return roadmap

# -----------------------------
# PAGE 1 — USER INPUT
# -----------------------------
def page_input():
    st.title("🎓 AI Academic Planner - Step 1: User Input")
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
# PAGE 2 — COURSE PLANNER (NEW INTERFACE)
# -----------------------------
def page_course_planner():
    st.title("📚 AI Academic Planner - Step 2: Course Planner")

    if not st.session_state.user_data:
        st.warning("Please complete Step 1 first")
        return

    # Generate roadmap
    if st.button("Generate AI Roadmap"):
        data = st.session_state.user_data
        semesters_count = data["duration"] * 2
        prompt = f"""
Return only JSON.

Generate structured roadmap with courses for {data['degree']} in {data['domain']} with focus {data['focus']}.
Separate:
- mandatory_courses
- recommended_courses
Provide semesters: {semesters_count}
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
         "topics": [
             {{"topic_name": "", "description": ""}}
         ],
         "prerequisites": []
       }}
     ]
   }}
 ]
}}
"""
        roadmap = call_ai(prompt)
        if roadmap:
            st.session_state.roadmap = validate_and_balance(roadmap)
            st.session_state.current_semester_selected = None
            st.success("Roadmap Generated!")

    roadmap = st.session_state.roadmap
    if not roadmap:
        st.info("Generate roadmap to see semesters")
        return

    # -----------------------------
    # Semester Cards
    # -----------------------------
    semesters = roadmap.get("semesters", [])
    colors = ["#4CAF50", "#FFC107", "#FF5722", "#03A9F4", "#9C27B0", "#00BCD4"]

    st.subheader("Semesters Overview")
    cols = st.columns(len(semesters))
    for i, sem in enumerate(semesters):
        color = colors[i % len(colors)]
        with cols[i]:
            if st.button(f"Sem {sem['semester_number']}", key=f"sem_card_{i}"):
                st.session_state.current_semester_selected = sem

    # -----------------------------
    # Selected Semester Detail
    # -----------------------------
    sem = st.session_state.current_semester_selected
    if sem:
        st.markdown("---")
        st.subheader(f"Semester {sem['semester_number']} Courses & Topics")
        for course in sem.get("courses", []):
            with st.expander(f"{course['name']} ({course['difficulty']}, {course['credits']} credits)"):
                for topic in course.get("topics", []):
                    st.write(f"- {topic['topic_name']}: {topic['description']}")

        # -----------------------------
        # Finalise / Modify Buttons
        # -----------------------------
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Finalise Semester"):
                st.session_state.finalised_curriculum = sem
                st.success(f"Semester {sem['semester_number']} Finalised! Generating full course plan...")
                # Optionally call AI to generate course plan, lesson plan, weekly timetable
                st.info("AI-generated lesson plan & weekly timetable ready!")

        with col2:
            modifications = st.text_area("Enter Modifications for AI to adjust")
            if st.button("Apply Modifications"):
                if modifications.strip():
                    mod_prompt = f"""
Return only JSON.

Modify Semester {sem['semester_number']} courses as per user input:
{modifications}

Preserve prerequisites, balance workload, return JSON with same structure.
"""
                    updated_sem = call_ai(mod_prompt)
                    if updated_sem:
                        st.session_state.current_semester_selected = updated_sem
                        # Also update in main roadmap
                        for idx, s in enumerate(semesters):
                            if s["semester_number"] == updated_sem["semester_number"]:
                                st.session_state.roadmap["semesters"][idx] = updated_sem
                        st.success("Modifications Applied! Semester updated.")

# -----------------------------
# NAVIGATION
# -----------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go To",
    ["User Input", "Course Planner"]
)

if page == "User Input":
    page_input()
elif page == "Course Planner":
    page_course_planner()