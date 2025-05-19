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
import random
import pandas as pd
import time
import google.generativeai as genai
from streamlit_option_menu import option_menu
from PIL import Image

# ---------- API Setup ---------- #
GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY"
genai.configure(api_key=GOOGLE_API_KEY)

# ---------- Files ---------- #
SCORE_FILE = 'scoreboard.pkl'
KNOWLEDGE_FILE = 'knowledge.pkl'
KNOWLEDGE_CSV = 'knowledge.csv'
USERS_FILE = 'users.pkl'
CHAT_HISTORY_DIR = 'chat_histories'
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)

# ---------- Mood Settings ---------- #
MOODS = {
    "happy": {"prefix": "😄 PyBot (Happy): "},
    "angry": {"prefix": "😡 PyBot (Angry): "},
    "sad": {"prefix": "😢 PyBot (Sad): "},
    "neutral": {"prefix": "🤖 PyBot: "}
}

# ---------- Predefined Responses ---------- #
responses = {
    "hi": "Hello! How can I help you?",
    "hello": "Hi there! What can I do for you?",
    "how are you": "I'm just a bot, but I'm functioning perfectly!",
    "thank you": "You're welcome!",
    "thanks": "No problem!",
    "bye": "Goodbye! Have a nice day!"
}

python_keywords = {}
python_topics = {}

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

def get_chat_file(username):
    return os.path.join(CHAT_HISTORY_DIR, f"{username}.csv")

def save_chat(username, user_input, reply):
    chat_file = get_chat_file(username)
    new_row = pd.DataFrame([[user_input, reply]], columns=["Input", "Reply"])
    if os.path.exists(chat_file):
        df = pd.read_csv(chat_file)
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row
    df.to_csv(chat_file, index=False)

def get_user_history(username):
    chat_file = get_chat_file(username)
    if os.path.exists(chat_file):
        df = pd.read_csv(chat_file)
        return df[['Input', 'Reply']].values.tolist()
    return []

def get_user_chat_sessions():
    return [f.replace('.csv', '') for f in os.listdir(CHAT_HISTORY_DIR) if f.endswith('.csv')]

# ---------- Voice --------- #
def text_to_speech(text):
    try:
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
    except Exception as e:
        st.warning(f"Voice generation failed: {e}")

# ---------- Search / Logic ---------- #
def calculate(expression):
    try:
        if re.match(r"^[\d\s\+\-\*/\.\(\)]+$", expression):
            return f"The answer is {eval(expression)}"
        return None
    except Exception:
        return None

def google_search(query):
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(query)
        result = response.text.strip()
        return result if result else result

def search_knowledge(user_input, sources):
    for source in sources:
        match = get_close_matches(user_input.lower(), source.keys(), n=1, cutoff=0.7)
        if match:
            return source[match[0]]
    return None

def get_response(user_input):
    user_input_lower = user_input.lower()
    reply = (
        search_knowledge(user_input_lower, [responses, st.session_state.knowledge, python_keywords, python_topics])
        or calculate(user_input_lower)
        or google_search(user_input_lower)
    )
    return reply or "I'm not sure about that. I tried my best to find a relevant answer."

# ---------- Session Setup ---------- #
if "page_configured" not in st.session_state:
    st.set_page_config(page_title="PyBot", layout="wide")
    st.session_state.page_configured = True

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "scores" not in st.session_state:
    st.session_state.scores = load_data(SCORE_FILE)
if "knowledge" not in st.session_state:
    st.session_state.knowledge = load_data(KNOWLEDGE_FILE)
    st.session_state.knowledge.update(load_from_csv())
if "users" not in st.session_state:
    st.session_state.users = load_data(USERS_FILE) or {"admin": "1234", "student": "python"}
if "mood" not in st.session_state:
    st.session_state.mood = "neutral"

# ---------- Login/Signup UI ---------- #
if not st.session_state.logged_in:
    st.title("🔐 PyBot Login")
    mode = st.radio("Choose action", ["Log in", "Sign up"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    def suggest_username(name, user_dict):
        if name not in user_dict:
            return name
        i = 1
        while f"{name}{i}" in user_dict:
            i += 1
        return f"{name}{i}"

    if mode == "Log in" and st.button("Log in"):
        if username in st.session_state.users and st.session_state.users[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success("Login successful! Redirecting...")
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

# ---------- Sidebar Layout ---------- #
with st.sidebar:
    st.markdown("## 🗂️ Sessions")
    sessions = get_user_chat_sessions()
    for session in sessions:
        if session == st.session_state.username:
            st.markdown(f"- **{session}**")
    selected = option_menu("Main Menu", ["Chat", "Past Conversations", "Games", "Settings"],
                           icons=["chat-dots", "clock-history", "controller", "gear"],
                           menu_icon="robot", default_index=0)

# ---------- Chat Page ---------- #
if selected == "Chat":
    st.title("🤖 Welcome to PyBot")
    st.markdown(f"### {MOODS[st.session_state.mood]['prefix']} How can I assist you today?")

    user_input = st.chat_input("Say something...")
    if user_input:
        reply = get_response(user_input)
        save_chat(st.session_state.username, user_input, reply)
        st.chat_message("user").markdown(user_input)
        st.chat_message("assistant").markdown(f"{MOODS[st.session_state.mood]['prefix']} {reply}")
        text_to_speech(reply)

# ---------- Past Conversations Page ---------- #
elif selected == "Past Conversations":
    st.title("📂 Your Chat History")
    history = get_user_history(st.session_state.username)
    if history:
        for msg in history[::-1]:
            st.markdown(f"**You:** {msg[0]}")
            st.markdown(f"**{MOODS[st.session_state.mood]['prefix']}** {msg[1]}")
    else:
        st.info("No chat history found.")

# ---------- Games Page ---------- #
elif selected == "Games":
    st.title("🎮 PyBot Games")
    game = st.radio("Choose a game:", ["Guess the Number", "Hangman"])
    if game == "Guess the Number":
        st.markdown("### 🔢 I'm thinking of a number between 1 and 100. Can you guess it?")
        if "target" not in st.session_state:
            st.session_state.target = random.randint(1, 100)
        guess = st.number_input("Your guess:", min_value=1, max_value=100, step=1)
        if st.button("Submit Guess"):
            if guess == st.session_state.target:
                st.success("🎉 Correct! You guessed it.")
                st.session_state.target = random.randint(1, 100)
            elif guess < st.session_state.target:
                st.info("Try a higher number.")
            else:
                st.info("Try a lower number.")
    elif game == "Hangman":
        st.markdown("### ⛓️ Hangman is coming soon!")

# ---------- Settings Page ---------- #
elif selected == "Settings":
    st.title("⚙️ Settings")
    if st.button("🔒 Logout"):
        st.session_state.logged_in = False
        st.rerun()
    theme = st.selectbox("Choose a theme:", ["Light", "Dark", "System Default"])
    st.info("Theme change is not yet implemented.")
