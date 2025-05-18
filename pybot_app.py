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
        url = f"https://en.wikipedia.org/w/index.php?search={query}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.select('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 50:
                return text
        return "I couldn't find a reliable source, but I tried to search Wikipedia for you."
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
        search_knowledge(user_input_lower, [st.session_state.knowledge])
        or calculate(user_input_lower)
        or google_search(user_input_lower)
        or "I'm not sure about that. Can you rephrase?"
    )
    return reply


# ---------- Session Setup ---------- #
cookie = st.query_params.get("user")
if cookie:
    st.session_state.logged_in = True
    st.session_state.username = cookie[0]

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

    if mode == "Log in" and st.button("Log in"):
        if username in st.session_state.users and st.session_state.users[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.experimental_set_query_params(user=username)
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

# Continue with main app UI setup below as-is...import time

# After login and setup...

st.title("🤖 Welcome to PyBot, " + st.session_state.username)

# Mood selection
mood = st.radio("Select PyBot's mood:", list(MOODS.keys()), index=list(MOODS.keys()).index(st.session_state.mood))
st.session_state.mood = mood

# Display chat history under mood
history = get_user_history(st.session_state.username)
st.markdown(f"### 💬 Previous Conversations ({len(history)})")
for inp, rep in history[-10:]:  # Show last 10 chats
    st.markdown(f"**You:** {inp}")
    st.markdown(f"{MOODS[mood]['prefix']} {rep}")

# Games toggle button
if "show_games" not in st.session_state:
    st.session_state.show_games = False

if st.button("🎮 Games"):
    st.session_state.show_games = not st.session_state.show_games

if st.session_state.show_games:
    st.subheader("🎮 Select a Game to Play")

    game_choice = st.selectbox("", ["Select a game", "Lucky 7", "Rock Paper Scissors", "Guess the Number", "Speed Typing Race", "Car Racing"])

    def play_again():
        return st.button("Play Again")

    if game_choice == "Lucky 7":
        option = st.radio("Pick your guess:", ["Above 7", "=7", "Below 7"])
        if st.button("Play Lucky 7"):
            number = random.randint(1, 12)
            if (option == "Above 7" and number > 7) or \
               (option == "=7" and number == 7) or \
               (option == "Below 7" and number < 7):
                st.success(f"You won! The number was {number}.")
            else:
                st.error(f"You lost! The number was {number}.")
        if play_again():
            st.experimental_rerun()

    elif game_choice == "Rock Paper Scissors":
        user_move = st.radio("Choose your move:", ["Rock", "Paper", "Scissors"])
        if st.button("Play RPS"):
            comp_move = random.choice(["Rock", "Paper", "Scissors"])
            st.write(f"Computer chose: {comp_move}")
            if user_move == comp_move:
                st.info("It's a tie!")
            elif (user_move == "Rock" and comp_move == "Scissors") or \
                 (user_move == "Paper" and comp_move == "Rock") or \
                 (user_move == "Scissors" and comp_move == "Paper"):
                st.success("You win!")
            else:
                st.error("You lose!")
        if play_again():
            st.experimental_rerun()

    elif game_choice == "Guess the Number":
        guess = st.number_input("Guess a number between 1 and 20:", min_value=1, max_value=20, step=1)
        if st.button("Guess"):
            secret = random.randint(1, 20)
            if guess == secret:
                st.success("Correct! You guessed the number!")
            else:
                st.error(f"Wrong! The number was {secret}.")
        if play_again():
            st.experimental_rerun()

    elif game_choice == "Speed Typing Race":
        phrase = "The quick brown fox jumps over the lazy dog"
        st.write("Type this phrase exactly as shown and hit Submit:")
        st.markdown(f"**{phrase}**")

        if "typing_start" not in st.session_state or st.session_state.game_reset:
            st.session_state.typing_start = time.time()
            st.session_state.game_reset = False

        user_typing = st.text_input("Start typing here:")

        if st.button("Submit Typing"):
            if user_typing.strip() == phrase:
                elapsed = time.time() - st.session_state.typing_start
                st.success(f"Perfect! Your time: {elapsed:.2f} seconds.")
            else:
                st.error("Typed phrase does not match exactly. Try again!")
        if play_again():
            st.session_state.game_reset = True
            st.experimental_rerun()

    elif game_choice == "Car Racing":
        st.write("When you see GO, press the button as fast as you can!")

        if "car_ready" not in st.session_state:
            st.session_state.car_ready = False
        if "car_start_time" not in st.session_state:
            st.session_state.car_start_time = None

        if not st.session_state.car_ready:
            if st.button("Get Ready"):
                delay = random.uniform(2, 5)
                st.write("Wait for it...")
                time.sleep(delay)
                st.write("GO!")
                st.session_state.car_start_time = time.time()
                st.session_state.car_ready = True
        else:
            if st.button("Press!"):
                reaction = time.time() - st.session_state.car_start_time
                st.success(f"Your reaction time: {reaction:.3f} seconds!")
                st.session_state.car_ready = False
                st.session_state.car_start_time = None
        if play_again():
            st.experimental_rerun()

else:
    # Main chatbot input/output UI when games hidden
    user_input = st.text_input(f"{MOODS[mood]['prefix']} Enter your message:")
    if st.button("Send") and user_input.strip():
        reply = get_response(user_input.strip())
        st.markdown(f"**You:** {user_input}")
        st.markdown(f"{MOODS[mood]['prefix']} {reply}")
        save_chat(st.session_state.username, user_input, reply)
