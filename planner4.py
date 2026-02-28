import streamlit as st
import requests
import json
import random

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(page_title="AI Academic Planning", layout="wide")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "granite3.3:2b"
MAX_CREDITS = 24

# =====================================================
# SAFE AI CALL
# =====================================================

def call_ai(prompt):
    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2}
        }

        r = requests.post(OLLAMA_URL, json=payload, timeout=120)

        if r.status_code != 200:
            st.error("AI request failed")
            return None

        data = r.json()
        text = data.get("response", "").strip()

        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()

        return json.loads(text)

    except:
        st.error("AI returned invalid output")
        return None


# =====================================================
# SESSION INIT
# =====================================================

if "step" not in st.session_state:
    st.session_state.step = 1

if "user_data" not in st.session_state:
    st.session_state.user_data = None

if "roadmap" not in st.session_state:
    st.session_state.roadmap = None

if "current_sem" not in st.session_state:
    st.session_state.current_sem = None


# =====================================================
# UTILITIES
# =====================================================

def total_credits(sem):
    total = 0
    for cat in ["mandatory", "recommended", "optional"]:
        for c in sem.get(cat, []):
            total += c.get("credits", 0)
    return total


def lightest_semester(roadmap):
    loads = []
    for sem in roadmap.get("semesters", []):
        loads.append((sem["semester_number"], total_credits(sem)))
    return min(loads, key=lambda x: x[1])[0]


# =====================================================
# STEP 1 — USER INPUT
# =====================================================

if st.session_state.step == 1:

    st.title("🎓 AI Academic Planning System")

    with st.form("input_form"):
        degree = st.selectbox("Degree", ["B.Tech", "MBA", "MSc", "BSc"])
        domain = st.text_input("Domain")
        focus = st.text_input("Focus")
        level = st.selectbox("Level", ["Beginner", "Intermediate", "Advanced"])
        duration = st.number_input("Duration (Years)", 1, 6, 4)
        weekly = st.number_input("Weekly Study Hours", 5, 60, 20)

        submit = st.form_submit_button("Analyze")

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

Predict achievable mastery.

Degree: {degree}
Domain: {domain}
Focus: {focus}
Level: {level}
Total Study Hours: {total_hours}

{{
 "predicted_level":"",
 "reason":""
}}
"""

        result = call_ai(prompt)

        if result:
            st.success("Capability Analysis")
            st.json(result)

            if st.button("Generate Curriculum Roadmap"):
                roadmap_prompt = f"""
Respond ONLY in valid JSON.

Create semester roadmap.

Semesters: {duration*2}

Each semester must include:
- mandatory
- recommended
- optional

{{
 "semesters":[
  {{
   "semester_number":1,
   "summary":"",
   "mandatory":[{{"name":"","credits":4}}],
   "recommended":[{{"name":"","credits":3}}],
   "optional":[{{"name":"","credits":2}}]
  }}
 ]
}}
"""
                roadmap = call_ai(roadmap_prompt)

                if roadmap and roadmap.get("semesters"):
                    st.session_state.roadmap = roadmap
                    st.session_state.step = 2
                    st.rerun()
                else:
                    st.error("Roadmap generation failed")


# =====================================================
# STEP 2 — PLANNING
# =====================================================

elif st.session_state.step == 2:

    roadmap = st.session_state.roadmap

    if not roadmap:
        st.error("No roadmap found.")
        st.session_state.step = 1
        st.rerun()

    st.title("📘 Curriculum Planning")

    for sem in roadmap.get("semesters", []):

        st.subheader(f"Semester {sem['semester_number']}")

        credits = total_credits(sem)
        st.write("Total Credits:", credits)

        if credits > MAX_CREDITS:
            st.error("Credit overload detected")

        for cat in ["mandatory", "recommended", "optional"]:
            st.markdown(f"**{cat.upper()}**")
            for c in sem.get(cat, []):
                st.write("-", c["name"], f"({c['credits']} credits)")

    st.divider()

    st.subheader("➕ Add Course")

    name = st.text_input("Course Name")
    credits = st.number_input("Credits", 1, 6, 3)
    category = st.selectbox("Category", ["mandatory", "recommended", "optional"])

    if st.button("Add Intelligently"):

        if not name:
            st.warning("Enter course name")
        else:
            target = lightest_semester(roadmap)

            for sem in roadmap["semesters"]:
                if sem["semester_number"] == target:
                    if total_credits(sem) + credits > MAX_CREDITS:
                        st.error("Exceeds credit limit")
                        break
                    sem[category].append({"name": name, "credits": credits})
                    st.success(f"Added to Semester {target}")
                    st.rerun()

    if st.button("Continue to Dashboard"):
        st.session_state.step = 3
        st.rerun()


# =====================================================
# STEP 3 — DASHBOARD
# =====================================================

elif st.session_state.step == 3:

    roadmap = st.session_state.roadmap

    st.title("📊 Dashboard")

    for sem in roadmap.get("semesters", []):

        if st.button(f"Open Semester {sem['semester_number']}"):
            st.session_state.current_sem = sem
            st.session_state.step = 4
            st.rerun()

        st.write(
            f"Semester {sem['semester_number']} - {total_credits(sem)} credits"
        )

    if st.button("Back to Planning"):
        st.session_state.step = 2
        st.rerun()


# =====================================================
# STEP 4 — EXECUTION
# =====================================================

elif st.session_state.step == 4:

    sem = st.session_state.current_sem

    if not sem:
        st.session_state.step = 3
        st.rerun()

    st.title(f"Semester {sem['semester_number']} Execution")

    all_courses = []
    for cat in ["mandatory", "recommended", "optional"]:
        all_courses.extend(sem.get(cat, []))

    tab1, tab2 = st.tabs(["Sessions", "Timetable"])

    with tab1:
        for c in all_courses:
            if st.button(f"Generate Sessions: {c['name']}"):
                prompt = f"""
Respond ONLY in valid JSON.

Break course into sessions.

Course: {c['name']}

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
                sessions = call_ai(prompt)
                if sessions:
                    st.json(sessions)

    with tab2:
        table = {d: [] for d in ["Mon","Tue","Wed","Thu","Fri","Sat"]}

        if all_courses:
            per = st.session_state.user_data["weekly"] / len(all_courses)
            for c in all_courses:
                days = random.sample(list(table.keys()), 2)
                for d in days:
                    table[d].append({
                        "course": c["name"],
                        "hours": round(per/2,1)
                    })

        st.json(table)

    if st.button("Back to Dashboard"):
        st.session_state.step = 3
        st.rerun()