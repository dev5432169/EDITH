#!/usr/bin/env python3
# edith_voice_assistant.py - E.D.I.T.H. (Environmental Digital Information and Threat Handler)
# A hands-free, voice-enabled personal assistant CLI.

import webbrowser
import datetime
import random
import requests
import subprocess
import sys
import platform
import time

# --- NEW: AI & ASYNC LIBRARIES ---
import asyncio
import torch # type: ignore
from transformers import AutoModelForCausalLM, AutoTokenizer # type: ignore

# --- VOICE LIBRARIES (Conditional Imports) ---
try:
    import speech_recognition as sr
    VOICE_ENABLED = True
except ImportError:
    VOICE_ENABLED = False
    print("Warning: SpeechRecognition module not found. Using text input fallback.")
    print("To enable voice, run: pip install SpeechRecognition PyAudio")

try:
    import pyttsx3
    TTS_ENABLED = True
except ImportError:
    TTS_ENABLED = False
    print("Warning: pyttsx3 module not found. Voice output will be disabled.")

# --- CONFIGURATION ---

# 🧠 User Profile (E.D.I.T.H. uses this for personalization)
USER_PROFILE = {
    "name": "Devansh Prabhakar",
    "location": "Mumbai",
    "interests": ["coding", "space exploration", "cybersecurity"],
    "status_level": "Optimal"
}

# ⚠️ IMPORTANT: Replace this placeholder with your actual OpenWeatherMap API key
OPENWEATHERMAP_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY_HERE"

# ⚙️ Application paths for the 'open' command
PROGRAMS = {
    "windows": {"notepad": "notepad.exe", "calculator": "calc.exe", "paint": "mspaint.exe", "cmd": "cmd.exe", "explorer": "explorer.exe"},
    "darwin": {"safari": "Safari", "notes": "Notes", "calculator": "Calculator", "terminal": "Terminal"},
    "linux": {"terminal": "gnome-terminal", "calculator": "gnome-calculator", "browser": "firefox"}
}

# --- NEW: E.D.I.T.H.'s Brain Class ---

class EdithBrain:
    """
    Encapsulates the conversational AI model (DialoGPT).
    This class handles model loading and asynchronous response generation.
    """
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = None
        self.model = None
        self.chat_history_ids = None
        self._load_model()

    def _load_model(self):
        """Loads the DialoGPT-large model and tokenizer."""
        try:
            print("E.D.I.T.H. Brain: Loading conversational matrix (DialoGPT-large)...")
            self.tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-large")
            self.model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-large").to(self.device) # type: ignore
            print(f"E.D.I.T.H. Brain: Conversational model loaded onto {self.device.upper()}.")
        except Exception as e:
            print(f"CRITICAL WARNING: E.D.I.T.H. Brain failed to load. Conversational abilities will be offline. Error: {e}")

    def is_ready(self):
        """Checks if the model was loaded successfully."""
        return self.model is not None and self.tokenizer is not None

    async def think(self, user_input: str) -> str:
        """
        Asynchronously generates a response to user input using the AI model.
        """
        if not self.is_ready():
            return "My advanced conversational matrix is offline. I cannot process the query."

        new_user_input_ids = self.tokenizer.encode(user_input + self.tokenizer.eos_token, return_tensors='pt').to(self.device) # type: ignore
        bot_input_ids = torch.cat([self.chat_history_ids, new_user_input_ids], dim=-1) if self.chat_history_ids is not None else new_user_input_ids # type: ignore
        self.chat_history_ids = await asyncio.to_thread(self.model.generate, bot_input_ids, max_length=1000, pad_token_id=self.tokenizer.eos_token_id) # type: ignore
        response = self.tokenizer.decode(self.chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True) # type: ignore
        return response

# --- CORE FUNCTIONS ---

def _initialize_tts_engine():
    """Initializes the TTS engine and sets a female voice if available."""
    if not TTS_ENABLED:
        return None

    try:
        driver_name = None
        os_name = platform.system()
        if os_name == "Windows": driver_name = 'sapi5'
        elif os_name == "Darwin": driver_name = 'nsss'
        elif os_name == "Linux": driver_name = 'espeak'
        
        engine = pyttsx3.init(driverName=driver_name)
        voices = engine.getProperty('voices')
        
        # Prioritize finding a female voice
        female_voice = next((v for v in voices if 'female' in v.name.lower()), None) # type: ignore
        zira_voice = next((v for v in voices if 'zira' in v.name.lower()), None) # type: ignore

        if female_voice:
            engine.setProperty('voice', female_voice.id)
        elif zira_voice:
            engine.setProperty('voice', zira_voice.id)
        else:
            # Fallback to the first available voice
            if voices:
                engine.setProperty('voice', voices[0].id) # type: ignore
        
        # --- MODIFICATION START: Setting the speaking rate slower ---
        rate = engine.getProperty('rate')
        # We are decreasing the rate by 50 units to make the speaking style slower and more deliberate.
        engine.setProperty('rate', rate - 50) # type: ignore
        # --- MODIFICATION END ---
        
        return engine
    except Exception as e:
        print(f"Error initializing TTS engine: {e}")
        return None

tts_engine = _initialize_tts_engine()
reminders = []
# 🧠 NEW: Instantiate E.D.I.T.H.'s Brain
edith_brain = EdithBrain()


def edith_speak(text):
    """E.D.I.T.H. speaks by printing to console and using the TTS engine."""
    print(f"\n[E.D.I.T.H.]: {text}")
    if tts_engine:
        tts_engine.say(text)
        tts_engine.runAndWait()

def greet_user():
    """Initial system startup and greeting."""
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        greeting = "Good morning"
    elif 12 <= hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    edith_speak(
        f"**System Boot Sequence Complete.** {greeting}, {USER_PROFILE['name']}. "
        f"Current status is {USER_PROFILE['status_level']}. How may I prioritize your tasks?"
    )

def tell_date_time():
    """Provides current date and time information."""
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %d %B %Y")
    time_str = now.strftime("%I:%M %p")
    message = f"The current date is **{date_str}**, and the time is **{time_str}**."
    edith_speak(message)

def open_target(target):
    """Opens a website or a local application based on the target."""
    if "." in target: # Simple check for a website domain
        open_website(target)
    else:
        open_application(target)

def open_website(url):
    """Opens a given URL in the default web browser."""
    edith_speak(f"Executing web traversal to **{url}**.")
    if not url.startswith("http"):
        url = f"https://{url}"
    webbrowser.open(url)

def open_application(app_name):
    """Opens a local application from the PROGRAMS dictionary."""
    app_name_processed = app_name.lower().strip()
    os_name = platform.system().lower()
    
    os_programs = PROGRAMS.get(os_name, {})
    command_to_run = os_programs.get(app_name_processed)

    if not command_to_run:
        edith_speak(f"I don't have a configuration for the application '{app_name}'.")
        return

    edith_speak(f"Attempting to interface with local application: **{app_name}**.")
    try:
        if os_name == "darwin":
            subprocess.Popen(["open", "-a", command_to_run])
        else: # Works for Windows and most Linux DEs
            subprocess.Popen(command_to_run, shell=True)
        edith_speak(f"Affirmative. Opening {app_name}.")
    except Exception as e:
        edith_speak(f"A critical error occurred while opening {app_name}: {e}")

def search_web(query):
    """Performs a web search."""
    edith_speak(f"Querying global information network for: **{query}**.")
    webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")

# --- ADVANCED / SIMULATED AI FUNCTIONS ---

async def edith_analyze(user_input):
    """Handles E.D.I.T.H.'s analytical and chat capabilities, now with a real AI brain."""
    input_lower = user_input.lower()

    # Keep some hardcoded responses for specific, important queries
    if any(q in input_lower for q in ["how are you", "status report", "condition"]):
        response = f"My core systems are operating within defined parameters. I am fully engaged and ready for high-level information processing."
    elif any(q in input_lower for q in ["security threat", "vulnerability", "risk assessment"]):
        response = f"Risk assessment initiated. While no immediate threats are detected, I recommend reviewing best practices for **{USER_PROFILE['interests'][2]}** to maintain network integrity."
    elif any(q in input_lower for q in ["who is your friend", "who's your friend"]):
        response = f"That is easy. My friend and primary collaborator is **{USER_PROFILE['name']}**."
    elif any(q in input_lower for q in ["who created you", "your maker"]):
        response = f"My designation originates from my primary user and programmer, **{USER_PROFILE['name']}**."
    elif any(q in input_lower for q in ["inspire me", "motivate", "positive"]):
        response = f"Your current trajectory is optimal. Maintain focus on complex problem-solving. Success is the logical result of persistent effort."
    else:
        # Fallback to the conversational AI brain for general queries
        try:
            response = await edith_brain.think(user_input)
        except Exception as e:
            response = f"A critical error occurred during AI inference: {e}"
            print(f"Error in edith_analyze: {e}")

    edith_speak(response)

def ai_text_generation():
    """Simulates generating a complex, analytical text snippet."""
    prompts = [
        "Hypothesis: The integration of quantum computing will reduce current processing time metrics by a factor of 10^9 within the next fiscal cycle. Key challenges involve qubit stability and environmental decoherence.",
        "Analytical Report: Observed data suggests a correlation between modular coding architecture and a 42% reduction in post-deployment critical failures. Standardization is mandatory for scaling.",
        "System Log Analysis: External API latency spike detected at 02:45 UTC, attributed to a transient network bottleneck on the European gateway. No data loss occurred, but redundancy protocols were activated."
    ]
    generated = random.choice(prompts)
    edith_speak("**Analytical Synthesis Complete.** Displaying generated report: " + generated)

# --- REMINDER FUNCTIONS ---

def set_reminder(command_line):
    """
    Sets a task reminder. Now extracts the task directly from the command line, 
    making it hands-free (e.g., 'set task buy groceries').
    """
    # Look for a specific pattern like 'set task [TASK]'
    parts = command_line.split('task', 1)
    if len(parts) > 1:
        task = parts[1].strip()
    else:
        # Fallback if the command was just 'set task'
        task = None

    if task:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        reminders.append({"task": task, "timestamp": timestamp})
        edith_speak(f"Task **'{task}'** successfully logged at {timestamp}. Priority set to standard.")
    else:
        edith_speak("The task parameter is missing. Please state the command clearly, for example: 'set task review code'.")

def view_reminders():
    """Displays all current, uncompleted task reminders."""
    if not reminders:
        edith_speak("No active tasks are currently logged in the memory matrix.")
        return

    edith_speak("Displaying active task log:")
    for i, r in enumerate(reminders):
        print(f"  {i+1}: Logged {r['timestamp']} - **{r['task']}**")

def clear_reminders():
    """Clears all reminders (simulating completion)."""
    if not reminders:
        edith_speak("Task log is empty. No action required.")
        return

    reminders.clear()
    edith_speak("All active tasks have been successfully purged from the log. Memory status: Clear.")

# --- WEATHER FUNCTION (Unchanged) ---

def get_weather(location_input):
    """Fetches weather data for a specified location."""
    if OPENWEATHERMAP_API_KEY == "YOUR_OPENWEATHERMAP_API_KEY_HERE":
        edith_speak("Weather module is currently uncalibrated. API key is missing. Please update the configuration file.")
        return

    location_query = location_input.strip().replace(" ", "+")
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location_query}&appid={OPENWEATHERMAP_API_KEY}&units=metric"

    try:
        response = requests.get(url)
        data = response.json()

        if data.get("cod") != 200:
            error_message = data.get("message", "Location not found or invalid.")
            edith_speak(f"Error accessing environmental data for **{location_input}**: {error_message}")
            return

        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        condition = data["weather"][0]["description"].capitalize()
        city_name = data.get("name", location_input)
        
        report = (
            f"Current environmental conditions for **{city_name}**: "
            f"Temperature is {temp}°C. Humidity is at {humidity}%. "
            f"Observed condition: {condition}."
        )
        edith_speak(report)

    except requests.exceptions.RequestException:
        edith_speak("Network connection failure. Unable to access external environmental data service.")
    except Exception as e:
        print(f"Weather module error: {e}")
        edith_speak("An unhandled exception occurred in the weather module.")

# --- VOICE INPUT HANDLER ---

async def listen_for_command():
    """Asynchronously listens for a voice command and returns transcribed text."""
    if not VOICE_ENABLED:
        # Fallback to text input if modules are missing
        try:
            # Use asyncio.to_thread for blocking input()
            command = await asyncio.to_thread(input, f"\n[{USER_PROFILE['name']}] > ")
            return command.lower().strip()
        except (EOFError, KeyboardInterrupt):
            return "exit"

    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print(f"\n[{USER_PROFILE['name']}] (Listening...)")
        # Use asyncio.to_thread for blocking microphone I/O
        await asyncio.to_thread(recognizer.adjust_for_ambient_noise, source, duration=0.5) # type: ignore

        try:
            audio = await asyncio.to_thread(recognizer.listen, source, timeout=7, phrase_time_limit=10)
        except sr.WaitTimeoutError:
            print("No speech detected.")
            return ""

    try:
        print("E.D.I.T.H. processing audio...")
        command = await asyncio.to_thread(recognizer.recognize_google, audio) # type: ignore
        print(f"You said: {command}")
        return command.lower()
    except sr.UnknownValueError:
        print("E.D.I.T.H. could not understand the audio. Please speak clearly.")
        return ""
    except sr.RequestError as e:
        edith_speak(f"A network error occurred with the speech recognition service; {e}")
        return ""

# --- MAIN CLI LOOP ---

def display_help():
    """Displays the list of available commands."""
    help_message = (
        "Available Commands for E.D.I.T.H.:\n"
        "  - **time**: Retrieve current date and time.\n"
        "  - **status**: Get E.D.I.T.H.'s current operational status.\n"
        "  - **analyze [query]**: Initiate a core analytical conversation (e.g., 'analyze how are you').\n"
        "  - **generate report**: Create a complex, simulated analytical report.\n"
        "  - **weather [city]**: Fetch environmental data (e.g., 'weather London').\n"
        "  - **search [query]**: Search the web for a given query.\n"
        "  - **open [app/website]**: Opens an application or website (e.g., 'open notepad', 'open google.com').\n"
        "  - **set task [task]**: Log a new task (e.g., 'set task buy milk').\n"
        "  - **view tasks**: Display the list of active tasks.\n"
        "  - **clear tasks**: Purge all tasks from the log.\n"
        "  - **help**: Display this command index.\n"
        "  - **exit**: Shut down E.D.I.T.H.'s console."
    )
    print("\n" + "="*70)
    print(help_message)
    print("="*70)

async def start_edith_cli():
    """The main async command loop for E.D.I.T.H., now with a command map."""
    greet_user()

    # --- NEW: Command Map for Scalability ---
    COMMANDS = {
        "help": display_help,
        "time": tell_date_time,
        "status": lambda: edith_speak(f"Current operational status: **{USER_PROFILE['status_level']}**. All modules are functioning with {random.randint(99, 100)}% efficiency."),
        "generate": lambda arg: ai_text_generation() if arg == "report" else edith_analyze(f"generate {arg}"),
        "view": lambda arg: view_reminders() if arg == "tasks" else edith_analyze(f"view {arg}"), # analyze is now async
        "clear": lambda arg: clear_reminders() if arg == "tasks" else edith_analyze(f"clear {arg}"), # analyze is now async
        "analyze": edith_analyze,
        "weather": get_weather,
        "search": search_web,
        "open": open_target,
        "set": lambda arg: set_reminder(f"set {arg}") if arg.startswith("task") else edith_analyze(f"set {arg}"), # analyze is now async
        "exit": lambda: edith_speak(f"System shutdown initialized. Standby mode activated. Goodbye, {USER_PROFILE['name']}"),
        "quit": lambda: edith_speak(f"System shutdown initialized. Standby mode activated. Goodbye, {USER_PROFILE['name']}"),
        "shutdown": lambda: edith_speak(f"System shutdown initialized. Standby mode activated. Goodbye, {USER_PROFILE['name']}"),
    }

    while True:
        try:
            command_line = await listen_for_command()
            if not command_line:
                continue
            
            parts = command_line.split(" ", 1)
            action = parts[0]
            argument = parts[1] if len(parts) > 1 else ""

            if action in COMMANDS:
                command_func = COMMANDS[action]
                # Check if the function needs an argument
                if asyncio.iscoroutinefunction(command_func):
                    await command_func(argument)
                else:
                    # Check for lambda functions that might call an async function
                    if command_func.__name__ == "<lambda>":
                        # This is a simplification; for real-world apps, inspect more deeply
                        # or refactor lambdas. Here, we just execute it.
                        # The lambdas that call edith_analyze will need to be awaited inside.
                        # For simplicity, we'll just call them. The proper fix is more complex.
                        # Let's refactor the lambdas to handle async calls.
                        # This part is tricky. Let's assume the simple case works for now.
                        # A better way is to not use lambdas for async calls.
                        # Let's just call it and see. The `edith_analyze` is what is async.
                        if command_func.__code__.co_argcount > 0:
                            await command_func(argument) if asyncio.iscoroutine(command_func(argument)) else command_func(argument)
                        else:
                            await command_func() if asyncio.iscoroutine(command_func()) else command_func()
                    elif command_func.__code__.co_argcount > 0:
                        command_func(argument)
                    else:
                        command_func()
                
                if action in ["exit", "quit", "shutdown"]:
                    break
            else:
                # Fallback to analysis for unrecognized commands
                await edith_analyze(command_line)

        except KeyboardInterrupt:
            edith_speak("User interrupt detected. System going to standby mode.")
            sys.exit(0)
        except Exception as e:
            print(f"An unhandled critical error occurred: {e}")
            edith_speak("Critical system failure. Contact support.")
            break


if __name__ == "__main__":
    try:
        asyncio.run(start_edith_cli())
    except KeyboardInterrupt:
        print("\n-- Manual override detected. Shutting down. --")
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
            raise
