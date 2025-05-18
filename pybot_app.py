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
import time

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
        return None
    except Exception:
        return None

def google_search(query):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://www.google.com/search?q={query}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        snippets = soup.select("div.BNeawe.s3v9rd.AP7Wnd")
        for snippet in snippets:
            text = snippet.get_text().strip()
            if len(text) > 50:
                return text
        return "I found some information, but couldn't extract a clear answer."
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
        search_knowledge(user_input_lower, [responses, st.session_state.knowledge, python_keywords, python_topics])
        or calculate(user_input_lower)
        or google_search(user_input_lower)
        or "I'm not sure about that. Could you try rephrasing?"
    )
    return reply

# ---------- Session Setup ---------- #
cookie = st.query_params.get("user")
if cookie:
    st.session_state.logged_in = True
    st.session_state.username = cookie

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
    st.set_page_config(page_title="PyBot Login", layout="centered")
    st.title("🔐 PyBot Login")
    mode = st.radio("Choose action", ["Log in", "Sign up"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if mode == "Log in" and st.button("Log in"):
        if username in st.session_state.users and st.session_state.users[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.query_params.update({"user": username})
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
st.set_page_config(page_title="PyBot", layout="wide")
st.sidebar.title("🛠️ Settings")
st.sidebar.selectbox("Choose Mood", list(MOODS.keys()), key="mood")

st.title("🤖 Welcome to PyBot")
st.markdown(f"### {MOODS[st.session_state.mood]['prefix']} How can I assist you today?")

user_input = st.text_input("You:")
if st.button("Send") and user_input:
    reply = get_response(user_input)
    save_chat(st.session_state.username, user_input, reply)
    st.markdown(f"**You:** {user_input}")
    st.markdown(f"**{MOODS[st.session_state.mood]['prefix']}** {reply}")
    text_to_speech(reply)

with st.expander("📜 Chat History"):
    history = get_user_history(st.session_state.username)
    for msg in history[-10:][::-1]:
        st.markdown(f"**You:** {msg[0]}")
        st.markdown(f"**{MOODS[st.session_state.mood]['prefix']}** {msg[1]}")
