from fasthtml.common import *
from fasthtml import *
from apscheduler.schedulers.background import BackgroundScheduler
import json
import os
from datetime import datetime

# --- Settings persistence ---
SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    "water_goal_ml": 2000,
    "standup_interval_min": 45,
    "pomodoro_minutes": 25,
    "standup_enabled": True,
    "last_standup_shown": None
}

def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                merged = DEFAULT_SETTINGS.copy()
                merged.update(data)
                return merged
        return DEFAULT_SETTINGS.copy()
    except Exception as e:
        print(f"[WARN] Failed to load settings: {e}")
        return DEFAULT_SETTINGS.copy()

def persist_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save settings: {e}")
        return False

# --- State files ---
WATER_LOG = "water_log.txt"
TASKS_FILE = "tasks.json"

def get_water_total():
    try:
        with open(WATER_LOG, "r") as f:
            return sum(int(line.strip()) for line in f if line.strip().isdigit())
    except:
        return 0

def get_tasks():
    try:
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, "r") as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"[WARN] Failed to load tasks: {e}")
        return []

def save_tasks(tasks):
    try:
        with open(TASKS_FILE, "w") as f:
            json.dump(tasks, f, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save tasks: {e}")
        return False

# --- Scheduler ---
sched = BackgroundScheduler()
app = FastHTML(live=True)

# Track last standup time (in memory + persisted via settings)
last_standup_shown = None

def get_last_standup_time():
    global last_standup_shown
    if last_standup_shown is None:
        try:
            s = load_settings()
            last = s.get("last_standup_shown")
            if last:
                last_standup_shown = datetime.fromisoformat(last)
        except Exception as e:
            print(f"[WARN] Failed to parse last standup time: {e}")
    return last_standup_shown

def set_last_standup_time(dt):
    global last_standup_shown
    last_standup_shown = dt
    s = load_settings()
    s["last_standup_shown"] = dt.isoformat()
    persist_settings(s)

# --- CSS Styles (Embedded) ---
GLOBAL_STYLES = """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 20px;
}

main {
    max-width: 900px;
    margin: 0 auto;
}

header {
    text-align: center;
    margin-bottom: 30px;
    animation: slideDown 0.6s ease-out;
}

header h1 {
    font-size: 3.5em;
    font-weight: 700;
    color: white;
    text-shadow: 0 2px 10px rgba(0,0,0,0.2);
    letter-spacing: -1px;
    margin-bottom: 8px;
}

header p {
    font-size: 1.1em;
    color: rgba(255,255,255,0.9);
    font-weight: 300;
}

section {
    background: white;
    border-radius: 16px;
    padding: 25px;
    margin-bottom: 20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    animation: fadeUp 0.6s ease-out;
}

section h2 {
    font-size: 1.8em;
    color: #2c3e50;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 12px;
}

/* --- Water Tracker --- */
#water-section {
    background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
}

#water-section h2 {
    color: white;
}

.water-info {
    text-align: center;
    margin-bottom: 20px;
}

.water-info p {
    font-size: 1.1em;
    color: rgba(255,255,255,0.95);
    margin: 8px 0;
    font-weight: 500;
}

.water-progress {
    background: rgba(255,255,255,0.3);
    height: 20px;
    border-radius: 10px;
    overflow: hidden;
    margin: 15px 0;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
}

.water-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #00d4ff, #0099ff);
    border-radius: 10px;
    transition: width 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
    box-shadow: 0 0 10px rgba(0, 153, 255, 0.5);
}

.water-form {
    display: flex;
    gap: 10px;
    justify-content: center;
    margin-top: 20px;
}

.water-form input {
    padding: 12px 16px;
    border: 2px solid rgba(255,255,255,0.5);
    border-radius: 8px;
    font-size: 1em;
    width: 140px;
    background: rgba(255,255,255,0.9);
    transition: all 0.3s ease;
}

.water-form input:focus {
    outline: none;
    border-color: white;
    background: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.water-form button {
    padding: 12px 24px;
    background: white;
    color: #00d4ff;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.water-form button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.15);
}

/* --- Timer Section --- */
#timer-section {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

#timer-section h2 {
    color: white;
}

.timer-display {
    font-size: 5em;
    font-weight: 700;
    color: white;
    text-align: center;
    text-shadow: 0 4px 20px rgba(0,0,0,0.2);
    margin: 30px 0;
    font-family: 'Courier New', monospace;
    letter-spacing: 4px;
}

.timer-controls {
    display: flex;
    gap: 15px;
    justify-content: center;
    flex-wrap: wrap;
}

.timer-controls button {
    padding: 12px 24px;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    font-size: 1em;
    transition: all 0.3s ease;
    color: white;
}

#start-btn {
    background: rgba(255,255,255,0.9);
    color: #f5576c;
}

#pause-btn {
    background: rgba(255,255,255,0.7);
    color: #f5576c;
}

#reset-btn {
    background: rgba(255,255,255,0.5);
    color: white;
}

.timer-controls button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.2);
}

/* --- Tasks Section --- */
#tasks-section {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

#tasks-section h2 {
    color: white;
}

.task-form {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
}

.task-form input {
    flex: 1;
    padding: 12px 16px;
    border: 2px solid rgba(255,255,255,0.5);
    border-radius: 8px;
    font-size: 1em;
    background: rgba(255,255,255,0.9);
    transition: all 0.3s ease;
}

.task-form input:focus {
    outline: none;
    border-color: white;
    background: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.task-form button {
    padding: 12px 24px;
    background: white;
    color: #00f2fe;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
}

.task-form button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.15);
}

#task-list {
    list-style: none;
}

.task-item {
    display: flex;
    align-items: center;
    padding: 15px 16px;
    background: rgba(255,255,255,0.95);
    border-radius: 10px;
    margin-bottom: 10px;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.task-item:hover {
    transform: translateX(5px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
}

.task-item input[type="checkbox"] {
    width: 22px;
    height: 22px;
    margin-right: 15px;
    cursor: pointer;
    accent-color: #00f2fe;
}

.task-item span {
    flex: 1;
    font-size: 1.05em;
    color: #2c3e50;
    font-weight: 500;
    transition: all 0.3s ease;
}

.task-item input[type="checkbox"]:checked + span {
    text-decoration: line-through;
    color: #bdc3c7;
    font-style: italic;
}

.task-item button {
    background: #e74c3c;
    color: white;
    border: none;
    padding: 8px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9em;
    margin-left: 10px;
    transition: all 0.3s ease;
}

.task-item button:hover {
    background: #c0392b;
    transform: scale(1.05);
}

/* --- Stand-up Banner --- */
#standup-banner {
    position: fixed;
    bottom: 30px;
    right: 30px;
    background: linear-gradient(135deg, #ff9a56 0%, #ff6b6b 100%);
    color: white;
    padding: 20px 24px;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(255, 107, 107, 0.4);
    max-width: 350px;
    animation: slideUp 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
    z-index: 9999;
    display: none;
}

#standup-banner h3 {
    font-size: 1.2em;
    margin-bottom: 10px;
    font-weight: 600;
}

#standup-banner p {
    font-size: 0.95em;
    margin-bottom: 15px;
    opacity: 0.95;
}

#standup-banner button {
    background: white;
    color: #ff6b6b;
    border: none;
    padding: 10px 16px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 0.9em;
}

#standup-banner button:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

/* --- Footer --- */
footer {
    text-align: center;
    margin-top: 40px;
    padding: 20px;
}

footer a {
    color: white;
    text-decoration: none;
    margin: 0 15px;
    font-weight: 500;
    transition: all 0.3s ease;
}

footer a:hover {
    text-shadow: 0 0 10px rgba(255,255,255,0.8);
}

/* --- Settings Page --- */
.settings-form {
    max-width: 600px;
    margin: 0 auto;
}

.form-group {
    margin-bottom: 25px;
}

.form-group label {
    display: block;
    font-weight: 600;
    color: white;
    margin-bottom: 10px;
    font-size: 1.1em;
}

.form-group input {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid rgba(255,255,255,0.5);
    border-radius: 8px;
    font-size: 1em;
    background: rgba(255,255,255,0.95);
    transition: all 0.3s ease;
}

.form-group input:focus {
    outline: none;
    border-color: white;
    background: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.settings-submit {
    width: 100%;
    padding: 14px;
    background: white;
    color: #667eea;
    border: none;
    border-radius: 8px;
    font-weight: 700;
    cursor: pointer;
    font-size: 1.1em;
    margin-top: 30px;
    transition: all 0.3s ease;
}

.settings-submit:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}

/* --- Animations --- */
@keyframes slideDown {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes fadeUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(50px) scale(0.8);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

@media (max-width: 768px) {
    body {
        padding: 10px;
    }

    header h1 {
        font-size: 2.5em;
    }

    section {
        padding: 18px;
        margin-bottom: 15px;
    }

    .timer-display {
        font-size: 3.5em;
    }

    .task-form {
        flex-direction: column;
    }

    #standup-banner {
        bottom: 20px;
        right: 20px;
        left: 20px;
        max-width: none;
    }
}
"""

# --- ROUTES ---

@app.get("/")
def home():
    settings = load_settings()
    total_water = get_water_total()
    tasks = get_tasks()
    progress_pct = min(100, int((total_water / settings["water_goal_ml"]) * 100)) if settings["water_goal_ml"] > 0 else 0

    last = get_last_standup_time()
    show_banner = False
    if settings.get("standup_enabled", True):
        if last is None:
            # First load after app start: initialize timestamp so reminder starts counting properly
            set_last_standup_time(datetime.now())
        else:
            elapsed = (datetime.now() - last).total_seconds() / 60
            if elapsed >= settings["standup_interval_min"]:
                show_banner = True

    return Title("Atomic Habits"), Head(
        Style(GLOBAL_STYLES)
    ), Main(
        Header(
            H1("⚛️ Atomic Habits"),
            P("Build sustainable habits. Stay focused. Stay hydrated. Stay healthy."),
        ),

        Section(
            H2("💧 Hydration Tracker"),
            Div(
                Div(
                    P(f"Goal: {settings['water_goal_ml']} mL today"),
                    P(f"{total_water} / {settings['water_goal_ml']} mL ({progress_pct}%)", style="font-size:1.3em; font-weight:700;"),
                    Div(
                        Div(style=f"width:{progress_pct}%;", cls="water-progress-bar"),
                        cls="water-progress"
                    ),
                    cls="water-info"
                ),
                Form(
                    Input(id="mL", name="mL", placeholder="Add mL", type="number", required=True, min="1"),
                    Button("Log Water", type="submit"),
                    action="/log",
                    method="post",
                    cls="water-form"
                ),
                id="water-section-content"
            ),
            id="water-section"
        ),

        Section(
            H2("⏱️ Focus Timer"),
            Div(
                Div(f"{settings['pomodoro_minutes']:02d}:00", id="timer-display", cls="timer-display"),
                P(
                    f"Stand-up reminder every {settings['standup_interval_min']} minutes" +
                    ("" if settings.get("standup_enabled", True) else " (disabled)"),
                    style="text-align:center; color:rgba(255,255,255,0.95); font-weight:500; margin-top:-10px; margin-bottom:20px;"
                ),
                Div(
                    Button("▶ Start", id="start-btn"),
                    Button("⏸ Pause", id="pause-btn"),
                    Button("🔄 Reset", id="reset-btn"),
                    cls="timer-controls"
                ),
                cls="timer-content"
            ),
            id="timer-section"
        ),

        Section(
            H2("✅ Daily Tasks"),
            Form(
                Input(id="task", name="task", placeholder="Add a new task...", type="text", required=True),
                Button("+ Add Task", type="submit"),
                action="/add",
                method="post",
                cls="task-form"
            ),
            Ul(
                *[
                    Li(
                        Input(type="checkbox", id=f"task-check-{i}", hx_post=f"/toggle/{i}", hx_swap="none", cls="task-checkbox"),
                        Span(task, id=f"task-text-{i}"),
                        Button("✕", hx_post=f"/delete/{i}", hx_target=f"#task-{i}", hx_swap="outerHTML swap:1s", cls="delete-task-btn"),
                        id=f"task-{i}",
                        cls="task-item"
                    )
                    for i, task in enumerate(tasks)
                ],
                id="task-list"
            ),
            id="tasks-section"
        ),

        Div(
            H3("🔔 Time to Stand Up!"),
            P("Move around for 2 minutes. Your body needs a break."),
            Button("Got it!", hx_post="/dismiss-standup", hx_target="#standup-banner", hx_swap="outerHTML swap:1s"),
            id="standup-banner",
            style=f"display:{'block' if show_banner else 'none'};"
        ),

        Footer(
            A("⚙️ Settings", href="/settings"),
            A("📖 Help", href="/help"),
            A("💻 GitHub", href="https://github.com/archanapillai25/atomic-habits.git")
        ),

        Script(f"""
            // ===== POMODORO TIMER =====
            let pomodoroMinutes = {settings['pomodoro_minutes']};
            let timeLeft = pomodoroMinutes * 60;
            let timerInterval = null;
            const display = document.getElementById('timer-display');
            const startBtn = document.getElementById('start-btn');
            const pauseBtn = document.getElementById('pause-btn');
            const resetBtn = document.getElementById('reset-btn');

            function updateDisplay() {{
                const mins = Math.floor(timeLeft / 60);
                const secs = timeLeft % 60;
                display.textContent = `${{mins}}:${{secs < 10 ? '0' : ''}}${{secs}}`;
                document.title = `${{mins}}:${{secs < 10 ? '0' : ''}}${{secs}} - Atomic Habits`;
            }}

            function startTimer() {{
                if (timerInterval) return;
                timerInterval = setInterval(() => {{
                    timeLeft--;
                    updateDisplay();
                    if (timeLeft <= 0) {{
                        clearInterval(timerInterval);
                        timerInterval = null;
                        alert('🎉 Pomodoro complete! Take a 5-minute break.');
                        timeLeft = pomodoroMinutes * 60;
                        updateDisplay();
                    }}
                }}, 1000);
            }}

            function pauseTimer() {{
                if (timerInterval) {{
                    clearInterval(timerInterval);
                    timerInterval = null;
                }}
            }}

            function resetTimer() {{
                pauseTimer();
                timeLeft = pomodoroMinutes * 60;
                updateDisplay();
            }}

            startBtn.onclick = startTimer;
            pauseBtn.onclick = pauseTimer;
            resetBtn.onclick = resetTimer;
            updateDisplay();

            // ===== TASK CHECKBOX TOGGLE =====
            document.querySelectorAll('.task-checkbox').forEach(checkbox => {{
                checkbox.addEventListener('change', function() {{
                    const span = this.nextElementSibling;
                    if (this.checked) {{
                        span.style.textDecoration = 'line-through';
                        span.style.color = '#bdc3c7';
                    }} else {{
                        span.style.textDecoration = 'none';
                        span.style.color = '#2c3e50';
                    }}
                }});
            }});

            // ===== STAND-UP REMINDER =====
            function checkStandup() {{
                fetch('/standup-status')
                    .then(r => r.json())
                    .then(data => {{
                        if (data.show) {{
                            document.getElementById('standup-banner').style.display = 'block';
                        }}
                    }})
                    .catch(e => console.log('[STANDUP] Check failed:', e));
            }}

            checkStandup();
            setInterval(checkStandup, 60000);
        """)
    )

@app.get("/standup-status")
def standup_status():
    settings = load_settings()
    last = get_last_standup_time()

    if not settings.get("standup_enabled", True):
        return {"show": False}

    if last is None:
        set_last_standup_time(datetime.now())
        return {"show": False}

    elapsed = (datetime.now() - last).total_seconds() / 60
    return {"show": elapsed >= settings["standup_interval_min"]}

@app.post("/log")
def log(mL: int):
    with open(WATER_LOG, "a") as f:
        f.write(f"{mL}\n")
    return RedirectResponse("/", status_code=303)

@app.post("/add")
def add(task: str):
    tasks = get_tasks()
    tasks.append(task)
    save_tasks(tasks)
    return RedirectResponse("/", status_code=303)

@app.post("/toggle/{idx}")
def toggle_task(idx: int):
    return ""

@app.post("/delete/{idx}")
def delete_task(idx: int):
    tasks = get_tasks()
    if 0 <= idx < len(tasks):
        tasks.pop(idx)
        save_tasks(tasks)
    return ""

@app.post("/dismiss-standup")
def dismiss_standup():
    set_last_standup_time(datetime.now())
    return ""

@app.get("/settings")
def settings_page(request):
    s = load_settings()
    saved = request.query_params.get("saved") == "1"
    error = request.query_params.get("error") == "1"

    return Title("⚙️ Settings"), Head(Style(GLOBAL_STYLES)), Main(
        Header(
            H1("⚙️ Settings"),
            P("Customize your habit-building experience"),
        ),
        Section(
            Form(
                Div(
                    Label("💧 Daily Water Goal (mL):", style="display:block; margin-bottom:8px;"),
                    Input(name="water_goal_ml", type="number", value=s["water_goal_ml"], min="500", max="5000"),
                    cls="form-group"
                ),
                Div(
                    Label("🚶 Stand-Up Interval (minutes):", style="display:block; margin-bottom:8px;"),
                    Input(name="standup_interval_min", type="number", value=s["standup_interval_min"], min="15", max="120"),
                    cls="form-group"
                ),
                Div(
                    Label("🍅 Pomodoro Duration (minutes):", style="display:block; margin-bottom:8px;"),
                    Input(name="pomodoro_minutes", type="number", value=s["pomodoro_minutes"], min="5", max="60"),
                    cls="form-group"
                ),
                Div(
                    Label("🔔 Enable Stand-Up Reminders:", style="display:block; margin-bottom:8px;"),
                    Input(
                        name="standup_enabled",
                        type="checkbox",
                        checked=s.get("standup_enabled", True)
                    ),
                    cls="form-group"
                ),
                Button("💾 Save Settings", type="submit", cls="settings-submit"),
                action="/save-settings",
                method="post",
                cls="settings-form"
            ),
            style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 16px;"
        ),
        Div(
            "✅ Settings saved successfully!" if saved else ("❌ Failed to save settings." if error else ""),
            style="color:white; text-align:center; margin-top:15px; font-weight:500;"
        ),
        Footer(A("← Back to Home", href="/"))
    )

@app.post("/save-settings")
def save_settings_route(
    water_goal_ml: int,
    standup_interval_min: int,
    pomodoro_minutes: int,
    standup_enabled: str = None
):
    s = load_settings()
    s.update({
        "water_goal_ml": water_goal_ml,
        "standup_interval_min": standup_interval_min,
        "pomodoro_minutes": pomodoro_minutes,
        "standup_enabled": standup_enabled is not None
    })

    if persist_settings(s):
        return RedirectResponse("/settings?saved=1", status_code=303)
    else:
        return RedirectResponse("/settings?error=1", status_code=303)

@app.get("/help")
def help_page():
    return Title("📖 Help"), Head(Style(GLOBAL_STYLES)), Main(
        Header(
            H1("📖 How to Use"),
            P("Master your habits with Atomic Habits"),
        ),
        Section(
            Ul(
                Li("💧 Log water intake with the hydration tracker!"),
                Li("⏱️ Use the Pomodoro timer for focused work sessions"),
                Li("✅ Check off tasks as you complete them"),
                Li("🚶 Get reminders to stand up every set minutes"),
                Li("⚙️ Customize all settings to match your lifestyle"),
                style="list-style: disc; padding-left: 20px; line-height: 1.8; font-size: 1.05em;"
            ),
            style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 16px;"
        ),
        Footer(A("← Back to Home", href="/"))
    )

# --- START APP ---
if __name__ == "__main__":
    sched.start()
    serve(host="0.0.0.0", port=8000)