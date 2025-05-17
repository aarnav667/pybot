import streamlit as st
import pickle
import csv
import os
import re
import requests
from difflib import get_close_matches
from bs4 import BeautifulSoup

# ---------------- Initial Setup ---------------- #
SCORE_FILE = 'scoreboard.pkl'
KNOWLEDGE_FILE = 'knowledge.pkl'
KNOWLEDGE_CSV = 'knowledge.csv'

# ---------------- Mood Settings ---------------- #
MOODS = {
    "happy": {"prefix": "😄 PyBot (Happy): ", "rate": 180},
    "angry": {"prefix": "😡 PyBot (Angry): ", "rate": 200},
    "sad": {"prefix": "😢 PyBot (Sad): ", "rate": 120},
    "neutral": {"prefix": "🤖 PyBot: ", "rate": 160}
}
current_mood = "neutral"

# ---------------- Load & Save Data ---------------- #
def load_data(file_name):
    if os.path.exists(file_name):
        with open(file_name, 'rb') as f:
            return pickle.load(f)
    return {}

def save_data(data, file_name):
    with open(file_name, 'wb') as f:
        pickle.dump(data, f)

def save_to_csv(knowledge):
    with open(KNOWLEDGE_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Question', 'Answer'])
        for question, answer in knowledge.items():
            writer.writerow([question, answer])

def load_from_csv():
    knowledge = {}
    if os.path.exists(KNOWLEDGE_CSV):
        with open(KNOWLEDGE_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                knowledge[row['Question'].lower()] = row['Answer']
    return knowledge

# Load data
scores = load_data(SCORE_FILE)
learned_knowledge = load_data(KNOWLEDGE_FILE)
learned_knowledge.update(load_from_csv())

# ---------------- Knowledge Base ---------------- #
responses = {
    "hi": "Hello! I can chat, solve math problems, play games, and teach Python.",
    "hello": "Hi there! You can ask me Python-related questions.",
    "how are you?": "I'm just a bot, but I'm here to help you with Python and math!",
    "who are you?": "I'm PyBot, your Python learning assistant.",
    "bye": "Goodbye! Keep practicing Python!",
    "help": "Try commands like 'Lucky 7', 'Rock Paper Scissors', 'Guess the Number', or ask me a math question.",
    "games": "Available games: Lucky 7, Rock Paper Scissors, Guess the Number"
}

python_keywords = {
    "if": "Used for decision-making. Example:\nif x > 0:\n    print('Positive number')",
    "list": "A collection which is ordered and changeable. Example:\nmylist = [1, 2, 3]"
}

python_topics = {
    "what is python?": "Python is a high-level, interpreted programming language."
}

# ---------------- Core Functions ---------------- #
def set_mood(mood_name):
    global current_mood
    if mood_name.lower() in MOODS:
        current_mood = mood_name.lower()
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
        snippet = soup.find('div', class_='BNeawe s3v9rd AP7Wnd')
        if snippet:
            return snippet.text
        else:
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
    learned_knowledge[user_input] = response
    save_data(learned_knowledge, KNOWLEDGE_FILE)
    save_to_csv(learned_knowledge)
    return response

# ---------------- Streamlit UI ---------------- #
st.title("🤖 PyBot - Your Python Learning Assistant")

with st.sidebar:
    st.header("Settings")
    selected_mood = st.selectbox("Choose Mood", list(MOODS.keys()), index=list(MOODS.keys()).index(current_mood))
    set_mood(selected_mood)
    st.write("Current Mood:", MOODS[current_mood]['prefix'])

user_input = st.text_input("Ask me anything:")
if user_input:
    response = get_response(user_input)
    st.markdown(f"{MOODS[current_mood]['prefix']} **{response}**")
