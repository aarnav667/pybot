import streamlit as st
import pickle
import csv
import os
import re
import requests
from difflib import get_close_matches
from bs4 import BeautifulSoup
from gtts import gTTS
import tempfile
import base64
import speech_recognition as sr
import random
import pandas as pd

# ---------- Files ---------- #
SCORE_FILE = 'scoreboard.pkl'
KNOWLEDGE_FILE = 'knowledge.pkl'
KNOWLEDGE_CSV = 'knowledge.csv'
USERS_FILE = 'users.pkl'
CHAT_HISTORY_FILE = 'chat_history.csv'

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

def save_chat(username, user_input, reply):
    new_row = pd.DataFrame([[username, user_input, reply]], columns=["User", "Input", "Reply"])
    if os.path.exists(CHAT_HISTORY_FILE):
        df = pd.read_csv(CHAT_HISTORY_FILE)
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row
    df.to_csv(CHAT_HISTORY_FILE, index=False)

def get_user_history(username):
    if os.path.exists(CHAT_HISTORY_FILE):
        df = pd.read_csv(CHAT_HISTORY_FILE)
        return df[df['User'] == username][['Input', 'Reply']].values.tolist()
    return []

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
        return snippet.text if snippet else "I couldn't find a direct answer, but I searched Google for you."
    except Exception as e:
        return f"Search error: {str(e)}"

def search_knowledge(user_input, sources):
    for source in sources:
        match = get_close_matches(user_input.lower(), source.keys(), n=1, cutoff=0.7)
        if match:
            return source[match[0]]
    return None

def get_response(user_input):
    user_input_lower = user_input.lower()
    reply = (
        search_knowledge(user_input_lower, [st.session_state.knowledge, responses, python_keywords, python_topics])
        or calculate(user_input_lower)
        or google_search(user_input_lower)
        or "I'm not sure about that. Can you rephrase?"
    )
    return reply

# ---------- Games ---------- #
def play_lucky_7():
    number = random.randint(1, 10)
    if number == 7:
        return "You got Lucky 7! 🎉"
    return f"You got {number}. Try again!"

def play_rps():
    choices = ["rock", "paper", "scissors"]
    bot = random.choice(choices)
    return f"I chose {bot}. What's your pick?"

def play_guess():
    return f"I'm thinking of a number between 1 and 5. Try refreshing and guessing again! It was {random.randint(1, 5)}."

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
            st.session_state.username = username
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

    st.subheader("🎮 Games")
    game_option = st.radio("Choose a game", ["None", "Lucky 7", "Rock Paper Scissors", "Guess the Number"])

    st.subheader("🕑 Previous Chats")
    history = get_user_history(st.session_state.username)
    for h_input, h_reply in reversed(history[-10:]):
        st.markdown(f"**You:** {h_input}")
        st.markdown(f"**PyBot:** {h_reply}")

if "voice_input" not in st.session_state:
    st.session_state.voice_input = ""

st.subheader("💬 Chat with PyBot")
text_prompt = "Ask me anything (or use voice input):"
user_input = st.text_input(text_prompt, value=st.session_state.voice_input)
st.session_state.voice_input = ""

if st.button("🎙️ Voice Input"):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening...")
        audio = r.listen(source)
        try:
            text = r.recognize_google(audio)
            st.success(f"You said: {text}")
            st.session_state.voice_input = text
            st.rerun()
        except sr.UnknownValueError:
            st.error("Could not understand audio")
        except sr.RequestError as e:
            st.error(f"Could not request results; {e}")

if user_input:
    user_input_lower = user_input.lower()
    if "lucky 7" in user_input_lower or game_option == "Lucky 7":
        reply = play_lucky_7()
    elif "rock" in user_input_lower or "paper" in user_input_lower or "scissors" in user_input_lower or game_option == "Rock Paper Scissors":
        reply = play_rps()
    elif "guess" in user_input_lower or game_option == "Guess the Number":
        reply = play_guess()
    else:
        reply = get_response(user_input)

    st.markdown(f"{MOODS[st.session_state.mood]['prefix']} **{reply}**")
    text_to_speech(reply)
    save_chat(st.session_state.username, user_input, reply)
