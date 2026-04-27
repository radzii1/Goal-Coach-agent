import streamlit as st
from openai import OpenAI
import json
import os
from datetime import datetime

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ── CUSTOM CSS ──
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #FFF0F3;
        font-family: 'Georgia', serif;
    }
    
    /* Chat input */
    .stChatInput input {
        background-color: #FFE4E9;
        border: 1px solid #FFB3C1;
        border-radius: 20px;
        color: #5C2D3E;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #FFB3C1;
        color: #5C2D3E;
        border: none;
        border-radius: 20px;
        font-size: 14px;
        padding: 8px 20px;
    }
    .stButton > button:hover {
        background-color: #FF85A1;
        color: white;
    }
    
    /* Metrics */
    [data-testid="metric-container"] {
        background-color: #FFE4E9;
        border-radius: 12px;
        padding: 12px;
        border: 1px solid #FFB3C1;
    }
    
    /* Info box */
    .stAlert {
        background-color: #FFE4E9;
        border: 1px solid #FFB3C1;
        border-radius: 12px;
        color: #5C2D3E;
    }
    
    /* Chat messages */
    .stChatMessage {
        background-color: #FFF5F7;
        border-radius: 16px;
        padding: 8px;
    }

    /* Title */
    h1 {
        color: #C2185B;
        font-family: 'Georgia', serif;
        text-align: center;
    }
    
    /* Subtext */
    p {
        color: #7B3F5E;
    }

    /* Divider */
    hr {
        border-color: #FFB3C1;
    }
</style>
""", unsafe_allow_html=True)

# ── MEMORY FUNCTIONS ──
def load_memory():
    try:
        with open('goal_coach_memory.json', 'r') as f:
            return json.load(f)
    except:
        return {
            "goal": None,
            "plan": [],
            "current_day": 1,
            "completed_days": [],
            "created_at": str(datetime.now().date())
        }

def save_memory(memory):
    with open('goal_coach_memory.json', 'w') as f:
        json.dump(memory, f, indent=2)

def create_plan(goal):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": """You are a no-nonsense goal coach.
Create a realistic 30-day action plan. Each day ONE clear task.
Be direct and specific. Return ONLY a JSON object with key 'plan' containing array of 30 strings."""},
            {"role": "user", "content": f"Create a 30-day plan for: {goal}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.7
    )
    data = json.loads(response.choices[0].message.content)
    if isinstance(data, dict):
        plan = list(data.values())[0]
    else:
        plan = data
    return plan

def get_todays_task(memory):
    current_day = memory["current_day"]
    plan = memory["plan"]
    if current_day > 30:
        return {"day": current_day, "task": "🎉 You've completed your 30-day plan!", "completed_so_far": 30, "remaining": 0}
    if not plan:
        return {"day": 1, "task": "No plan found. Set your goal first!", "completed_so_far": 0, "remaining": 30}
    return {
        "day": current_day,
        "task": plan[current_day - 1],
        "completed_so_far": len(memory["completed_days"]),
        "remaining": 30 - len(memory["completed_days"])
    }

def mark_complete(memory):
    current_day = memory["current_day"]
    if current_day not in memory["completed_days"]:
        memory["completed_days"].append(current_day)
    memory["current_day"] = current_day + 1
    save_memory(memory)
    return f"Day {current_day} marked complete! Moving to Day {current_day + 1} ✅"

def generate_nudge(memory, user_message):
    current_day = memory["current_day"]
    completed = len(memory["completed_days"])
    goal = memory["goal"]
    todays_task = memory["plan"][current_day - 1] if memory["plan"] and current_day <= 30 else "Plan complete"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": """You are a goal coach who is:
- Direct and honest — no toxic positivity
- Warm but firm — like a good friend who holds you accountable
- Short — max 3 sentences
- Always end with one specific action
Never say "you've got this" or "believe in yourself". Just be real."""},
            {"role": "user", "content": f"""
Goal: {goal}
Day: {current_day} of 30
Completed: {completed} days
Today's task: {todays_task}
User says: {user_message}
Respond as their coach."""}
        ],
        temperature=0.8
    )
    return response.choices[0].message.content

def run_agent(user_message, memory):
    if not memory["goal"]:
        memory["goal"] = user_message
        memory["plan"] = create_plan(user_message)
        save_memory(memory)
        todays = get_todays_task(memory)
        return f"""✅ Goal set! Your 30-day plan is ready.

📅 Today's task (Day 1):
{todays['task']}

Come back tomorrow and tell me what you did."""

    todays = get_todays_task(memory)
    complete_keywords = ["done", "completed", "finished", "did it", "complete"]

    if any(word in user_message.lower() for word in complete_keywords):
        result = mark_complete(memory)
        nudge = generate_nudge(memory, user_message)
        return f"{result}\n\n{nudge}"

    nudge = generate_nudge(memory, user_message)
    return f"""📅 Day {todays['day']} of 30
✅ Completed: {todays['completed_so_far']} days

Today's task: {todays['task']}

{nudge}"""

# ── UI ──
st.title("🌸 Goal Coach")
st.markdown("<p style='text-align:center; font-size:16px;'>Set your goal. Show up daily. Get held accountable.</p>", unsafe_allow_html=True)

memory = load_memory()

if memory["goal"]:
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("📅 Day", f"{memory['current_day']}/30")
    col2.metric("✅ Done", f"{len(memory['completed_days'])}")
    col3.metric("🎯 Left", f"{30 - len(memory['completed_days'])}")
    st.divider()
    st.markdown(f"<p style='font-size:14px;'>🌷 <b>Your goal:</b> {memory['goal']}</p>", unsafe_allow_html=True)
    if memory["plan"] and memory["current_day"] <= 30:
        st.info(f"📅 **Today (Day {memory['current_day']}):** {memory['plan'][memory['current_day']-1]}")

st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

placeholder = "Tell me your 30-day goal..." if not memory["goal"] else "How's it going today? 🌸"

if prompt := st.chat_input(placeholder):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("🌸 Thinking..."):
            memory = load_memory()
            response = run_agent(prompt, memory)
        st.write(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

if memory["goal"]:
    st.divider()
    if st.button("🔄 Reset and start fresh"):
        if os.path.exists('goal_coach_memory.json'):
            os.remove('goal_coach_memory.json')
        st.session_state.messages = []
        st.rerun()
