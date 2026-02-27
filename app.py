import streamlit as st
import google.generativeai as genai
import json
import re

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(page_title="AI Academic Planner", layout="wide")

# --------------------------------------------------
# API KEY INPUT
# --------------------------------------------------
st.sidebar.title("🔑 API Configuration")
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

# --------------------------------------------------
# MODEL INITIALIZATION WITH AUTO-DETECTION
# --------------------------------------------------
model = None
if api_key:
    try:
        genai.configure(api_key=api_key)

        # List all available models
        available_models = genai.list_models()

        # Pick first Gemini model that supports generate_content
        for m in available_models:
            if "gemini" in m.name.lower() and "generate_content" in m.supported_generation_methods:
                model = genai.GenerativeModel(m.name)
                st.sidebar.success(f"Using model: {m.name}")
                break

        if not model:
            st.sidebar.error("No valid Gemini model available for generate_content")

    except Exception as e:
        st.sidebar.error("Model initialization failed")
        st.sidebar.write(str(e))

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
for key in ["user_data", "roadmap", "current_semester", "capability"]:
    if key not in st.session_state:
        st.session_state[key] = None

# --------------------------------------------------
# SAFE GEMINI JSON FUNCTION
# --------------------------------------------------
def call_gemini_json(prompt):
    if not api_key:
        st.warning("Please enter your Gemini API key.")
        return None

    if not model:
        st.error("Model not initialized.")
        return None

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 2048
            }
        )

        raw = response.text.strip()

        # Remove markdown
        raw = raw.replace("```json", "").replace("```", "").strip()

        # Extract JSON safely
        match = re.search(r"\{.*\}|\[.*\]", raw, re.DOTALL)
        if not match:
            st.error("No valid JSON found.")
            st.code(raw)
            return None

        json_text = match.group(0)
        return json.loads(json_text)

    except json.JSONDecodeError:
        st.error("JSON parsing failed.")
        st.code(raw)
        return None
    except Exception as e:
        st.error("Gemini request failed.")
        st.write(str(e))
        return None

# --------------------------------------------------
# PAGE 1 – USER INPUT
# --------------------------------------------------
def page_user_input():
    st.title("🎓 AI Academic Planning System")

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
Return valid JSON only.

{{
 "predicted_level":"", 
 "reason":""
}}

Degree: {degree}
Domain: {domain}
Focus: {focus}
Level: {level}
Total Hours: {total_hours}
"""
        result = call_gemini_json(prompt)
        if result:
            st.session_state.capability = result
            st.success("Capability Generated")
            st.json(result)

# --------------------------------------------------
# ROADMAP
# --------------------------------------------------
def generate_roadmap():
    data = st.session_state.user_data
    semesters = data["duration"] * 2

    prompt = f"""
Return valid JSON only.

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
       "difficulty":"",
       "prerequisites":[]
     }}
   ]
  }}
 ]
}}

Degree: {data['degree']}
Domain: {data['domain']}
Focus: {data['focus']}
Semesters: {semesters}
"""
    return call_gemini_json(prompt)

# --------------------------------------------------
# COURSE PLANNER
# --------------------------------------------------
def page_course_planner():
    st.title("📚 Intelligent Course Planner")

    if not st.session_state.user_data:
        st.warning("Complete Page 1 first")
        return

    if st.button("Generate AI Roadmap"):
        st.session_state.roadmap = generate_roadmap()
        if st.session_state.roadmap:
            st.success("Roadmap Generated")

    if st.session_state.roadmap:
        st.json(st.session_state.roadmap)

# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------
def page_dashboard():
    st.title("📊 Semester Dashboard")
    roadmap = st.session_state.roadmap
    if not roadmap:
        st.warning("Generate roadmap first")
        return

    for sem in roadmap.get("semesters", []):
        st.subheader(f"Semester {sem['semester_number']}")
        st.write("Credits:", sem["credits"])
        st.write("Focus:", sem["focus_summary"])

        if st.button(f"Open Semester {sem['semester_number']}", key=f"open_{sem['semester_number']}"):
            st.session_state.current_semester = sem
            st.rerun()

# --------------------------------------------------
# SEMESTER VIEW
# --------------------------------------------------
def page_semester():
    sem = st.session_state.current_semester
    if not sem:
        st.warning("Open a semester first")
        return

    st.title(f"Semester {sem['semester_number']}")
    for course in sem.get("courses", []):
        st.subheader(course["name"])

# --------------------------------------------------
# NAVIGATION
# --------------------------------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["User Input", "Course Planner", "Dashboard", "Semester View"])

if page == "User Input":
    page_user_input()
elif page == "Course Planner":
    page_course_planner()
elif page == "Dashboard":
    page_dashboard()
elif page == "Semester View":
    page_semester()

       
    

    
          
           
