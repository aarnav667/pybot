import streamlit as st
import pickle
import csv
import os
import re
import requests
from difflib import get_close_matches, SequenceMatcher
from bs4 import BeautifulSoup
from gtts import gTTS
import tempfile
import base64
import speech_recognition as sr

# ---------- Files ---------- #
SCORE_FILE = 'scoreboard.pkl'
KNOWLEDGE_FILE = 'knowledge.pkl'
KNOWLEDGE_CSV = 'knowledge.csv'
USERS_FILE = 'users.pkl'

# ---------- Mood Settings ---------- #
MOODS = {
    "happy": {"prefix": "😄 PyBot (Happy): "},
    "angry": {"prefix": "😡 PyBot (Angry): "},
    "sad": {"prefix": "😢 PyBot (Sad): "},
    "neutral": {"prefix": "🤖 PyBot: "}
}
if "mood" not in st.session_state:
    st.session_state.mood = "neutral"

# ---------- Load & Save ---------- #
def load_data(file_name):
    return pickle.load(open(file_name, 'rb')) if os.path.exists(file_name) else {}

def save_data(data, file_name):
    pickle.dump(data, open(file_name, 'wb'))

def save_to_csv(knowledge):
    with open(KNOWLEDGE_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Question', 'Answer'])
        for q, a in knowledge.items():
            writer.writerow([q, a])

def load_from_csv():
    knowledge = {}
    if os.path.exists(KNOWLEDGE_CSV):
        with open(KNOWLEDGE_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                knowledge[row['Question'].lower()] = row['Answer']
    return knowledge

def suggest_username(name, user_dict):
    if name not in user_dict:
        return name
    i = 1
    while f"{name}{i}" in user_dict:
        i += 1
    return f"{name}{i}"

# ---------- Voice --------- #
def text_to_speech(text):
    tts = gTTS(text)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        tts.save(fp.name)
        audio_file = open(fp.name, 'rb')
        audio_bytes = audio_file.read()
        b64 = base64.b64encode(audio_bytes).decode()
        md = f"""
        <audio autoplay>
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """
        st.markdown(md, unsafe_allow_html=True)

# ---------- Search / Logic ---------- #
def calculate(expression):
    try:
        if re.match(r"^[\d\s\+\-\*/\.\(\)]+$", expression):
            return f"The answer is {eval(expression)}"
        return "Invalid math expression."
    except Exception as e:
        return f"Error: {str(e)}"

def google_search(query):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://www.google.com/search?q={query}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        snippet = soup.find('div', class_='BNeawe s3v9rd AP7Wnd')
        return snippet.text if snippet else "No direct answer found, but I searched Google."
    except Exception as e:
        return f"Search error: {str(e)}"

def search_knowledge(user_input, sources):
    for source in sources:
        match = get_close_matches(user_input.lower(), source.keys(), n=1, cutoff=0.7)
        if match:
            return source[match[0]]
    return None

def get_response(user_input):
    if user_input.lower().startswith("set mood"):
        mood = user_input.split()[-1]
        if mood in MOODS:
            st.session_state.mood = mood
            return f"Mood set to {mood}."
        return "Unknown mood."

    if any(op in user_input for op in ['+', '-', '*', '/']):
        return calculate(user_input)

    if user_input.lower() == "show scores":
        return '\n'.join([f"{k}: {v}" for k, v in st.session_state.scores.items()]) or "No scores yet."

    response = search_knowledge(user_input, [st.session_state.knowledge, responses, python_topics, python_keywords])
    if response:
        return response

    response = google_search(user_input)
    st.session_state.knowledge[user_input] = response
    save_data(st.session_state.knowledge, KNOWLEDGE_FILE)
    save_to_csv(st.session_state.knowledge)
    return response

# ---------- Default Data ---------- #
responses = {
    "hi": "Hello! I can chat, solve math, play games, and teach Python.",
    "bye": "Goodbye! Keep learning.",
    "games": "Try Lucky 7, Rock Paper Scissors, Guess the Number!",
    "help": "Ask me Python, Math or try a command like 'Lucky 7'."
}

python_keywords = {
    "if": "Used for decision-making. Example:\nif x > 0:\n    print('Positive')",
    "list": "An ordered, changeable collection. Example: mylist = [1, 2, 3]"
}

python_topics = {
    "what is python?": "Python is a high-level, interpreted programming language."
}

# ---------- Session Setup ---------- #
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "scores" not in st.session_state:
    st.session_state.scores = load_data(SCORE_FILE)
if "knowledge" not in st.session_state:
    st.session_state.knowledge = load_data(KNOWLEDGE_FILE)
    st.session_state.knowledge.update(load_from_csv())
if "users" not in st.session_state:
    st.session_state.users = load_data(USERS_FILE) or {"admin": "1234", "student": "python"}

# ---------- Login/Signup UI ---------- #
if not st.session_state.logged_in:
    st.title("🔐 PyBot Login")
    mode = st.radio("Choose action", ["Log in", "Sign up"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if mode == "Log in" and st.button("Log in"):
        if username in st.session_state.users and st.session_state.users[username] == password:
            st.session_state.logged_in = True
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid username or password.")

    elif mode == "Sign up" and st.button("Sign up"):
        if username in st.session_state.users:
            suggestion = suggest_username(username, st.session_state.users)
            st.warning(f"Username already exists. Try: {suggestion}")
        else:
            st.session_state.users[username] = password
            save_data(st.session_state.users, USERS_FILE)
            st.success("Sign up successful! You can now log in.")
            st.rerun()

    st.stop()

# ---------- Main App UI ---------- #
st.title("🤖 PyBot - Python Learning Assistant")

with st.sidebar:
    st.header("Settings")
    mood = st.selectbox("Choose Mood", list(MOODS.keys()), index=list(MOODS.keys()).index(st.session_state.mood))
    st.session_state.mood = mood
    st.write("Current Mood:", MOODS[st.session_state.mood]["prefix"])

user_input = st.text_input("Ask me anything:")

if st.button("🎙️ Voice Input"):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening...")
        audio = r.listen(source)
        try:
            user_input = r.recognize_google(audio)
            st.success(f"You said: {user_input}")
        except sr.UnknownValueError:
            st.error("Could not understand audio")
        except sr.RequestError as e:
            st.error(f"Could not request results; {e}")

if user_input:
    reply = get_response(user_input)
    st.markdown(f"{MOODS[st.session_state.mood]['prefix']} **{reply}**")
    text_to_speech(reply)
