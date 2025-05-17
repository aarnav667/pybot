# pybot_streamlit_advanced.py
import streamlit as st
import pickle
import csv
import os
import re
import requests
import speech_recognition as sr
from gtts import gTTS
from difflib import get_close_matches
from bs4 import BeautifulSoup
from streamlit_extras.switch_page_button import switch_page

# ---------------- File Paths ---------------- #
DATA_DIR = "user_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def get_user_file(user, name):
    return os.path.join(DATA_DIR, f"{user}_{name}.pkl")

def get_user_chat_file(user):
    return os.path.join(DATA_DIR, f"{user}_chat.txt")

# ---------------- Streamlit Session State ---------------- #
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "current_mood" not in st.session_state:
    st.session_state.current_mood = "neutral"

MOODS = {
    "happy": {"prefix": "😄 PyBot (Happy): ", "rate": 180},
    "angry": {"prefix": "😡 PyBot (Angry): ", "rate": 200},
    "sad": {"prefix": "😢 PyBot (Sad): ", "rate": 120},
    "neutral": {"prefix": "🤖 PyBot: ", "rate": 160}
}

# ---------------- Load & Save Data ---------------- #
def load_data(file_name):
    if os.path.exists(file_name):
        with open(file_name, 'rb') as f:
            return pickle.load(f)
    return {}

def save_data(data, file_name):
    with open(file_name, 'wb') as f:
        pickle.dump(data, f)

def append_chat(username, user_input, response):
    with open(get_user_chat_file(username), 'a', encoding='utf-8') as f:
        f.write(f"User: {user_input}\n{MOODS[st.session_state.current_mood]['prefix']}{response}\n\n")

def read_chat_history(username):
    path = get_user_chat_file(username)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return "No chat history found."

# ---------------- Authentication ---------------- #
if not st.session_state.logged_in:
    st.title("🔐 Login to PyBot")
    username = st.text_input("Enter your username")
    if st.button("Login") and username:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.experimental_rerun()
    st.stop()

username = st.session_state.username
SCORE_FILE = get_user_file(username, "scores")
KNOWLEDGE_FILE = get_user_file(username, "knowledge")

# ---------------- Load Data ---------------- #
scores = load_data(SCORE_FILE)
learned_knowledge = load_data(KNOWLEDGE_FILE)

# ---------------- Knowledge Base ---------------- #
responses = {
    "hi": "Hello! I can chat, solve math problems, play games, and teach Python.",
    "bye": "Goodbye! Keep practicing Python!",
    "games": "Available games: Lucky 7, Rock Paper Scissors, Guess the Number"
}
python_keywords = {
    "if": "Used for decision-making. Example:\nif x > 0:\n    print('Positive number')"
}
python_topics = {
    "what is python?": "Python is a high-level, interpreted programming language."
}

# ---------------- Utility Functions ---------------- #
def set_mood(mood_name):
    if mood_name.lower() in MOODS:
        st.session_state.current_mood = mood_name.lower()
        return f"Mood set to {mood_name}"
    return "Unknown mood. Choose from: happy, sad, angry, neutral."

def calculate(expression):
    try:
        if re.match(r"^[\d\s\+\-\*/\.\(\)]+$", expression):
            return f"The answer is {eval(expression)}"
        else:
            return "Invalid math expression."
    except Exception as e:
        return f"Error: {str(e)}"

def google_search(query):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        search_url = f"https://www.google.com/search?q={query}"
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        snippets = soup.select('div.BNeawe.s3v9rd.AP7Wnd')
        for s in snippets:
            if s.text.strip():
                return s.text.strip()
        return "No direct answer found. Try checking Google directly."
    except Exception as e:
        return f"Failed to search. Error: {str(e)}"

def search_knowledge(user_input):
    all_sources = [learned_knowledge, responses, python_topics, python_keywords]
    for source in all_sources:
        match = get_close_matches(user_input.lower(), source.keys(), n=1, cutoff=0.7)
        if match:
            return source[match[0]]
    return None

def get_response(user_input):
    if user_input.lower().startswith("set mood"):
        return set_mood(user_input.replace("set mood", "").strip())
    elif any(op in user_input for op in ['+', '-', '*', '/']):
        return calculate(user_input)
    elif user_input.lower() == "show scores":
        return '\n'.join([f"{k}: {v}" for k, v in scores.items()]) or "No scores yet."

    match = search_knowledge(user_input)
    if match:
        return match

    response = google_search(user_input)
    learned_knowledge[user_input] = response  # Learn from mistake
    save_data(learned_knowledge, KNOWLEDGE_FILE)
    return response

# ---------------- Streamlit UI ---------------- #
st.title("🤖 PyBot - Your Python Learning Assistant")

with st.sidebar:
    st.header(f"Welcome, {username}")
    selected_mood = st.selectbox("Choose Mood", list(MOODS.keys()), index=list(MOODS.keys()).index(st.session_state.current_mood))
    mood_message = set_mood(selected_mood)
    st.write("Current Mood:", MOODS[st.session_state.current_mood]['prefix'])
    if st.button("View Chat History"):
        st.info(read_chat_history(username))

user_input = st.text_input("Ask me anything:")
if st.button("Speak"):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening...")
        audio = recognizer.listen(source)
        try:
            user_input = recognizer.recognize_google(audio)
            st.success(f"You said: {user_input}")
        except sr.UnknownValueError:
            st.error("Sorry, I could not understand your speech.")
        except sr.RequestError:
            st.error("Speech recognition service failed.")

if user_input:
    response = get_response(user_input)
    st.markdown(f"{MOODS[st.session_state.current_mood]['prefix']} **{response}**")
    append_chat(username, user_input, response)
