from fasthtml.common import *
from fasthtml import *
from apscheduler.schedulers.background import BackgroundScheduler
import json
import os
from datetime import datetime, timedelta

# --- Settings persistence ---
SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    "water_goal_ml": 2000,
    "standup_interval_min": 45,
    "pomodoro_minutes": 25,
    "standup_enabled": True,
    "water_reminder_enabled": True,
    "water_reminder_interval_min": 60,
    "reset_time_hhmm": "00:00",
    "last_standup_shown": None,
    "last_water_reminder_shown": None,
    "last_reset_at": None
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

def clear_file(path):
    try:
        with open(path, "w") as f:
            f.write("")
    except Exception as e:
        print(f"[WARN] Failed to clear file {path}: {e}")

def parse_iso_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except:
        return None

def get_current_reset_point(now, reset_time_hhmm):
    try:
        hh, mm = reset_time_hhmm.split(":")
        hh, mm = int(hh), int(mm)
    except:
        hh, mm = 0, 0

    today_reset = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if now >= today_reset:
        return today_reset
    return today_reset - timedelta(days=1)

def check_and_reset_daily():
    s = load_settings()
    now = datetime.now()
    reset_point = get_current_reset_point(now, s.get("reset_time_hhmm", "00:00"))
    last_reset_at = parse_iso_dt(s.get("last_reset_at"))

    should_reset = False
    if last_reset_at is None:
        # Initialize without wiping immediately on first launch
        s["last_reset_at"] = reset_point.isoformat()
        persist_settings(s)
        return

    if last_reset_at < reset_point:
        should_reset = True

    if should_reset:
        clear_file(WATER_LOG)
        save_tasks([])
        s["last_reset_at"] = reset_point.isoformat()
        s["last_standup_shown"] = now.isoformat()
        s["last_water_reminder_shown"] = now.isoformat()
        persist_settings(s)

# --- Scheduler ---
sched = BackgroundScheduler()
app = FastHTML(live=True)

# Track last reminder times in memory
last_standup_shown = None
last_water_reminder_shown = None

def get_last_standup_time():
    global last_standup_shown
    if last_standup_shown is None:
        s = load_settings()
        last_standup_shown = parse_iso_dt(s.get("last_standup_shown"))
    return last_standup_shown

def set_last_standup_time(dt):
    global last_standup_shown
    last_standup_shown = dt
    s = load_settings()
    s["last_standup_shown"] = dt.isoformat()
    persist_settings(s)

def get_last_water_reminder_time():
    global last_water_reminder_shown
    if last_water_reminder_shown is None:
        s = load_settings()
        last_water_reminder_shown = parse_iso_dt(s.get("last_water_reminder_shown"))
    return last_water_reminder_shown

def set_last_water_reminder_time(dt):
    global last_water_reminder_shown
    last_water_reminder_shown = dt
    s = load_settings()
    s["last_water_reminder_shown"] = dt.isoformat()
    persist_settings(s)

# --- CSS Styles (same theme, only added water banner style mirroring standup) ---
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

/* --- Reminder Banners --- */
#standup-banner, #water-banner {
    position: fixed;
    right: 30px;
    color: white;
    padding: 20px 24px;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    max-width: 350px;
    animation: slideUp 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
    z-index: 9999;
    display: none;
}

#standup-banner {
    bottom: 30px;
    background: linear-gradient(135deg, #ff9a56 0%, #ff6b6b 100%);
    box-shadow: 0 8px 32px rgba(255, 107, 107, 0.4);
}

#water-banner {
    bottom: 170px;
    background: linear-gradient(135deg, #36d1dc 0%, #5b86e5 100%);
    box-shadow: 0 8px 32px rgba(91, 134, 229, 0.35);
}

#standup-banner h3, #water-banner h3 {
    font-size: 1.2em;
    margin-bottom: 10px;
    font-weight: 600;
}

#standup-banner p, #water-banner p {
    font-size: 0.95em;
    margin-bottom: 15px;
    opacity: 0.95;
}

#standup-banner button, #water-banner button {
    background: white;
    border: none;
    padding: 10px 16px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 0.9em;
}

#standup-banner button {
    color: #ff6b6b;
}

#water-banner button {
    color: #5b86e5;
}

#standup-banner button:hover, #water-banner button:hover {
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

.form-group input[type="checkbox"] {
    width: auto;
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

    #water-banner {
        bottom: 160px;
        right: 20px;
        left: 20px;
        max-width: none;
    }

    #standup-banner {
        bottom: 20px;
        right: 20px;
        left: 20px;
        max-width: none;
    }
}
"""

def render_task_item(task, i):
    return Li(
        Input(type="checkbox", id=f"task-check-{i}", hx_post=f"/toggle/{i}", hx_swap="none", cls="task-checkbox"),
        Span(task, id=f"task-text-{i}"),
        Button("✕", hx_post=f"/delete/{i}", hx_target=f"#task-{i}", hx_swap="outerHTML swap:1s", cls="delete-task-btn"),
        id=f"task-{i}",
        cls="task-item"
    )

# --- ROUTES ---

@app.get("/")
def home():
    check_and_reset_daily()

    settings = load_settings()
    total_water = get_water_total()
    tasks = get_tasks()

    progress_pct = min(100, int((total_water / settings["water_goal_ml"]) * 100)) if settings["water_goal_ml"] > 0 else 0

    last = get_last_standup_time()
    show_standup = False
    if settings.get("standup_enabled", True):
        if last is None:
            set_last_standup_time(datetime.now())
        else:
            elapsed = (datetime.now() - last).total_seconds() / 60
            if elapsed >= settings["standup_interval_min"]:
                show_standup = True

    last_water = get_last_water_reminder_time()
    show_water = False
    if settings.get("water_reminder_enabled", True):
        if last_water is None:
            set_last_water_reminder_time(datetime.now())
        else:
            elapsed_water = (datetime.now() - last_water).total_seconds() / 60
            if elapsed_water >= settings["water_reminder_interval_min"]:
                show_water = True

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
                    f"Stand-up reminder every {settings['standup_interval_min']} minutes",
                    style="text-align:center; color:rgba(255,255,255,0.95); font-weight:500; margin-top:-10px; margin-bottom:8px;"
                ),
                P(
                    f"Water reminder every {settings['water_reminder_interval_min']} minutes",
                    style="text-align:center; color:rgba(255,255,255,0.92); font-weight:500; margin-bottom:20px;"
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
                cls="task-form",
                id="task-form",
                hx_post="/add",
                hx_target="#task-list",
                hx_swap="beforeend"
            ),
            Ul(
                *[render_task_item(task, i) for i, task in enumerate(tasks)],
                id="task-list"
            ),
            id="tasks-section"
        ),

        Div(
            H3("💧 Time to Drink Water!"),
            P("Take a few sips and stay hydrated."),
            Button("Done", hx_post="/dismiss-water", hx_target="#water-banner", hx_swap="outerHTML swap:1s"),
            id="water-banner",
            style=f"display:{'block' if show_water else 'none'};"
        ),

        Div(
            H3("🔔 Time to Stand Up!"),
            P("Move around for 2 minutes. Your body needs a break."),
            Button("Got it!", hx_post="/dismiss-standup", hx_target="#standup-banner", hx_swap="outerHTML swap:1s"),
            id="standup-banner",
            style=f"display:{'block' if show_standup else 'none'};"
        ),

        Footer(
            A("⚙️ Settings", href="/settings"),
            A("📖 Help", href="/help"),
            A("💻 GitHub", href="https://github.com/yourusername/atomic-habits")
        ),

        Script(f"""
            // ===== POMODORO TIMER WITH PERSISTENCE =====
            const STORAGE_KEY = 'atomic_habits_timer_state';
            let pomodoroMinutes = {load_settings()['pomodoro_minutes']};
            let timerInterval = null;
            let timerState = {{
                durationMinutes: pomodoroMinutes,
                timeLeft: pomodoroMinutes * 60,
                running: false,
                endTime: null
            }};

            const display = document.getElementById('timer-display');
            const startBtn = document.getElementById('start-btn');
            const pauseBtn = document.getElementById('pause-btn');
            const resetBtn = document.getElementById('reset-btn');

            function saveTimerState() {{
                localStorage.setItem(STORAGE_KEY, JSON.stringify(timerState));
            }}

            function loadTimerState() {{
                try {{
                    const raw = localStorage.getItem(STORAGE_KEY);
                    if (!raw) {{
                        saveTimerState();
                        return;
                    }}
                    const parsed = JSON.parse(raw);

                    // If settings duration changed, keep current running/remaining if present,
                    // otherwise use new configured value
                    if (parsed && typeof parsed === 'object') {{
                        timerState = parsed;
                        if (!timerState.durationMinutes) timerState.durationMinutes = pomodoroMinutes;

                        if (!timerState.running && timerState.durationMinutes !== pomodoroMinutes && timerState.timeLeft === timerState.durationMinutes * 60) {{
                            timerState.durationMinutes = pomodoroMinutes;
                            timerState.timeLeft = pomodoroMinutes * 60;
                        }}
                    }}
                }} catch (e) {{
                    console.log('Failed to load timer state', e);
                    timerState = {{
                        durationMinutes: pomodoroMinutes,
                        timeLeft: pomodoroMinutes * 60,
                        running: false,
                        endTime: null
                    }};
                    saveTimerState();
                }}
            }}

            function formatTime(seconds) {{
                const mins = Math.floor(seconds / 60);
                const secs = seconds % 60;
                return `${{mins}}:${{secs < 10 ? '0' : ''}}${{secs}}`;
            }}

            function updateDisplay() {{
                display.textContent = formatTime(timerState.timeLeft);
                document.title = `${{formatTime(timerState.timeLeft)}} - Atomic Habits`;
            }}

            function gentleChime() {{
                try {{
                    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    const now = audioCtx.currentTime;

                    function tone(freq, start, duration, gainValue) {{
                        const osc = audioCtx.createOscillator();
                        const gain = audioCtx.createGain();

                        osc.type = 'sine';
                        osc.frequency.value = freq;

                        gain.gain.setValueAtTime(0.0001, start);
                        gain.gain.exponentialRampToValueAtTime(gainValue, start + 0.02);
                        gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);

                        osc.connect(gain);
                        gain.connect(audioCtx.destination);

                        osc.start(start);
                        osc.stop(start + duration);
                    }}

                    tone(523.25, now, 0.45, 0.08);
                    tone(659.25, now + 0.18, 0.45, 0.06);
                    tone(783.99, now + 0.36, 0.6, 0.05);
                }} catch (e) {{
                    console.log('Chime failed', e);
                }}
            }}

            function tick() {{
                if (!timerState.running || !timerState.endTime) return;

                const remaining = Math.max(0, Math.round((timerState.endTime - Date.now()) / 1000));
                timerState.timeLeft = remaining;
                updateDisplay();
                saveTimerState();

                if (remaining <= 0) {{
                    clearInterval(timerInterval);
                    timerInterval = null;
                    timerState.running = false;
                    timerState.endTime = null;
                    timerState.timeLeft = timerState.durationMinutes * 60;
                    saveTimerState();
                    updateDisplay();
                    gentleChime();
                    alert('🎉 Pomodoro complete! Take a 5-minute break.');
                }}
            }}

            function startTimer() {{
                if (timerState.running) return;

                timerState.running = true;
                timerState.endTime = Date.now() + (timerState.timeLeft * 1000);
                saveTimerState();

                if (timerInterval) clearInterval(timerInterval);
                timerInterval = setInterval(tick, 1000);
                tick();
            }}

            function pauseTimer() {{
                if (!timerState.running) return;

                timerState.timeLeft = Math.max(0, Math.round((timerState.endTime - Date.now()) / 1000));
                timerState.running = false;
                timerState.endTime = null;
                saveTimerState();

                if (timerInterval) {{
                    clearInterval(timerInterval);
                    timerInterval = null;
                }}
                updateDisplay();
            }}

            function resetTimer() {{
                if (timerInterval) {{
                    clearInterval(timerInterval);
                    timerInterval = null;
                }}

                timerState = {{
                    durationMinutes: pomodoroMinutes,
                    timeLeft: pomodoroMinutes * 60,
                    running: false,
                    endTime: null
                }};
                saveTimerState();
                updateDisplay();
            }}

            loadTimerState();
            updateDisplay();

            if (timerState.running) {{
                if (timerInterval) clearInterval(timerInterval);
                timerInterval = setInterval(tick, 1000);
                tick();
            }}

            startBtn.onclick = startTimer;
            pauseBtn.onclick = pauseTimer;
            resetBtn.onclick = resetTimer;

            // ===== TASK CHECKBOX TOGGLE =====
            document.addEventListener('change', function(e) {{
                if (e.target && e.target.classList.contains('task-checkbox')) {{
                    const span = e.target.nextElementSibling;
                    if (e.target.checked) {{
                        span.style.textDecoration = 'line-through';
                        span.style.color = '#bdc3c7';
                    }} else {{
                        span.style.textDecoration = 'none';
                        span.style.color = '#2c3e50';
                    }}
                }}
            }});

            // ===== TASK FORM UX FIXES =====
            document.body.addEventListener('htmx:beforeRequest', function(e) {{
                if (e.target && e.target.id === 'task-form') {{
                    sessionStorage.setItem('atomic_scroll_y', String(window.scrollY));
                }}
            }});

            document.body.addEventListener('htmx:afterRequest', function(e) {{
                if (e.target && e.target.id === 'task-form') {{
                    const taskInput = document.getElementById('task');
                    if (taskInput) taskInput.value = '';

                    const savedY = sessionStorage.getItem('atomic_scroll_y');
                    if (savedY !== null) {{
                        window.scrollTo({{ top: parseInt(savedY, 10), behavior: 'auto' }});
                    }}
                }}
            }});

            // ===== REMINDER POLLING =====
            function checkReminders() {{
                fetch('/reminder-status')
                    .then(r => r.json())
                    .then(data => {{
                        if (data.water_show) {{
                            const wb = document.getElementById('water-banner');
                            if (wb) wb.style.display = 'block';
                        }}
                        if (data.standup_show) {{
                            const sb = document.getElementById('standup-banner');
                            if (sb) sb.style.display = 'block';
                        }}
                    }})
                    .catch(e => console.log('[REMINDER] Check failed:', e));
            }}

            checkReminders();
            setInterval(checkReminders, 60000);
        """)
    )

@app.get("/reminder-status")
def reminder_status():
    check_and_reset_daily()
    settings = load_settings()
    now = datetime.now()

    standup_show = False
    water_show = False

    if settings.get("standup_enabled", True):
        last = get_last_standup_time()
        if last is None:
            set_last_standup_time(now)
        else:
            elapsed = (now - last).total_seconds() / 60
            standup_show = elapsed >= settings["standup_interval_min"]

    if settings.get("water_reminder_enabled", True):
        last_water = get_last_water_reminder_time()
        if last_water is None:
            set_last_water_reminder_time(now)
        else:
            elapsed_water = (now - last_water).total_seconds() / 60
            water_show = elapsed_water >= settings["water_reminder_interval_min"]

    return {"standup_show": standup_show, "water_show": water_show}

@app.post("/log")
def log(mL: int):
    check_and_reset_daily()
    with open(WATER_LOG, "a") as f:
        f.write(f"{mL}\n")
    set_last_water_reminder_time(datetime.now())
    return RedirectResponse("/", status_code=303)

@app.post("/add")
def add(task: str):
    check_and_reset_daily()
    tasks = get_tasks()
    task = (task or "").strip()
    if task:
        tasks.append(task)
        save_tasks(tasks)
        idx = len(tasks) - 1
        return render_task_item(task, idx)
    return ""

@app.post("/toggle/{idx}")
def toggle_task(idx: int):
    check_and_reset_daily()
    return ""

@app.post("/delete/{idx}")
def delete_task(idx: int):
    check_and_reset_daily()
    tasks = get_tasks()
    if 0 <= idx < len(tasks):
        tasks.pop(idx)
        save_tasks(tasks)
    return ""

@app.post("/dismiss-standup")
def dismiss_standup():
    set_last_standup_time(datetime.now())
    return ""

@app.post("/dismiss-water")
def dismiss_water():
    set_last_water_reminder_time(datetime.now())
    return ""

@app.get("/settings")
def settings_page(request):
    check_and_reset_daily()
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
                    Input(name="standup_interval_min", type="number", value=s["standup_interval_min"], min="15", max="240"),
                    cls="form-group"
                ),
                Div(
                    Label("🍅 Pomodoro Duration (minutes):", style="display:block; margin-bottom:8px;"),
                    Input(name="pomodoro_minutes", type="number", value=s["pomodoro_minutes"], min="5", max="120"),
                    cls="form-group"
                ),
                Div(
                    Label("💧 Water Reminder Interval (minutes):", style="display:block; margin-bottom:8px;"),
                    Input(name="water_reminder_interval_min", type="number", value=s["water_reminder_interval_min"], min="10", max="240"),
                    cls="form-group"
                ),
                Div(
                    Label("🕒 Auto Reset Time (HH:MM):", style="display:block; margin-bottom:8px;"),
                    Input(name="reset_time_hhmm", type="time", value=s.get("reset_time_hhmm", "00:00")),
                    cls="form-group"
                ),
                Div(
                    Label("🔔 Enable Stand-Up Reminders:", style="display:block; margin-bottom:8px;"),
                    Input(name="standup_enabled", type="checkbox", checked=s.get("standup_enabled", True)),
                    cls="form-group"
                ),
                Div(
                    Label("💧 Enable Water Reminders:", style="display:block; margin-bottom:8px;"),
                    Input(name="water_reminder_enabled", type="checkbox", checked=s.get("water_reminder_enabled", True)),
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
    water_reminder_interval_min: int,
    reset_time_hhmm: str,
    standup_enabled: str = None,
    water_reminder_enabled: str = None
):
    s = load_settings()
    s.update({
        "water_goal_ml": water_goal_ml,
        "standup_interval_min": standup_interval_min,
        "pomodoro_minutes": pomodoro_minutes,
        "water_reminder_interval_min": water_reminder_interval_min,
        "reset_time_hhmm": reset_time_hhmm or "00:00",
        "standup_enabled": standup_enabled is not None,
        "water_reminder_enabled": water_reminder_enabled is not None
    })

    if persist_settings(s):
        return RedirectResponse("/settings?saved=1", status_code=303)
    else:
        return RedirectResponse("/settings?error=1", status_code=303)

@app.get("/help")
def help_page():
    check_and_reset_daily()
    return Title("📖 Help"), Head(Style(GLOBAL_STYLES)), Main(
        Header(
            H1("📖 How to Use"),
            P("Master your habits with Atomic Habits"),
        ),
        Section(
            Ul(
                Li("💧 Log water intake with the hydration tracker"),
                Li("⏱️ Use the Pomodoro timer for focused work sessions"),
                Li("🔔 Get stand-up and water reminders based on your settings"),
                Li("✅ Add and manage daily tasks without interrupting your timer"),
                Li("🕒 Auto-reset your water and tasks every day at your chosen time"),
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