# app.py
# Streamlit Voice-Enabled FAQ Chatbot (secure, cleaned version)

import os
import datetime
import pandas as pd
import streamlit as st
import speech_recognition as sr
from gtts import gTTS

# --- OpenAI client (use env var; do NOT hardcode keys) ---
# Supports either: openai>=1.x (OpenAI class) or the classic openai lib.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable.")

# Prefer the official 'openai' SDK (>=1.x). Fallback if older API is installed.
try:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    def chat_completion(messages, model="gpt-4o-mini", max_tokens=200, temperature=0.2):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
except Exception:
    import openai  # classic
    openai.api_key = OPENAI_API_KEY
    def chat_completion(messages, model="gpt-3.5-turbo", max_tokens=200, temperature=0.2):
        resp = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message["content"].strip()

# --- Data helpers ---
DEFAULT_FAQ = {
    "question": [
        "What are your working hours?",
        "Do you work on weekends?",
        "How can I reset my password?",
        "Can I change my registered email address?",
        "Do you offer international shipping?",
        "How long does delivery take within India?",
        "How long does international delivery take?",
        "How can I contact support?",
        "Where is your company located?",
        "Do you provide refunds?",
        "How do I track my order?",
        "What payment methods are accepted?",
        "Is cash on delivery available?",
        "Is my personal data secure?",
        "Do you provide warranty on products?",
        "Can I cancel my order?",
        "Do you have a mobile app?",
        "Do you provide bulk discounts?",
        "What should I do if I receive a damaged product?",
        "Do you offer internships?",
        "How do I apply for a job?",
        "Do you offer customer loyalty rewards?",
        "How do I redeem reward points?",
        "What if I forgot my username?",
        "How can I delete my account?"
    ],
    "answer": [
        "Our office is open from 9 AM to 6 PM, Monday to Friday.",
        "No, we are closed on Saturdays and Sundays.",
        "Click on 'Forgot Password' at login and follow the steps to reset your password.",
        "Yes, go to Account Settings and update your email under Profile Information.",
        "Yes, we ship worldwide with additional charges depending on the region.",
        "Delivery usually takes 3–5 business days.",
        "International delivery can take 7–15 business days depending on location.",
        "You can email us at support@example.com or call +1-234-567-890.",
        "We are headquartered in New Delhi, India, with offices in Bangalore and Mumbai.",
        "Yes, refunds can be requested within 14 days of purchase subject to our refund policy.",
        "Go to 'My Orders' and click 'Track Order' for real-time updates.",
        "We accept credit cards, debit cards, UPI, PayPal, and bank transfers.",
        "Yes, Cash on Delivery is available for select regions in India.",
        "Yes, we use industry-standard encryption and comply with relevant privacy regulations.",
        "Yes, most products come with a 1-year manufacturer’s warranty.",
        "Yes, you can cancel before the order is shipped. After shipping, cancellation is not possible.",
        "Yes, our app is available on both iOS and Android platforms.",
        "Yes, we provide discounts for bulk and corporate orders. Contact sales@example.com.",
        "Please raise a support ticket within 48 hours with photos, and we will arrange a replacement.",
        "Yes, we offer internships in software, data science, and marketing. Openings are posted on our Careers page.",
        "Visit our Careers page and apply through the online portal.",
        "Yes, we have a points-based loyalty program where every purchase earns you reward points.",
        "You can redeem points at checkout for discounts on future purchases.",
        "Use your registered email address as your username or request help from support.",
        "Go to Account Settings → Privacy → Delete Account. This is permanent and cannot be undone."
    ]
}

def ensure_csv(path="data/faq.csv"):
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(path):
        pd.DataFrame(DEFAULT_FAQ).to_csv(path, index=False, encoding="utf-8")

def load_faq(path="data/faq.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"question", "answer"}
    if not required.issubset(df.columns):
        raise ValueError("CSV must have 'question' and 'answer' columns.")
    return df

# --- App State & Utils ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_query" not in st.session_state:
    st.session_state.user_query = ""

def log_message(sender, message):
    st.session_state.chat_history.append({
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "sender": sender,
        "message": message
    })

def generate_response(user_query: str, faq_df: pd.DataFrame) -> str:
    faq_text = "\n".join([f"Q: {row['question']}\nA: {row['answer']}" for _, row in faq_df.iterrows()])
    prompt = f"""
You are a polite and helpful FAQ chatbot.
Use only the FAQs to answer.

FAQs:
{faq_text}

User asked: "{user_query}"

If the answer is in the FAQs, respond succinctly.
If not found, reply exactly: "Sorry, I don't have information about that."
"""
    messages = [
        {"role": "system", "content": "You are an FAQ chatbot."},
        {"role": "user", "content": prompt},
    ]
    try:
        return chat_completion(messages)
    except Exception as e:
        return f"⚠️ Error: {e}"

def record_audio() -> str:
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎙️ Listening... please speak your question")
        audio = recognizer.listen(source, phrase_time_limit=5)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return "⚠️ Sorry, could not understand audio."
    except sr.RequestError:
        return "⚠️ Speech recognition service unavailable."

def speak_text(text: str, filename="response.mp3") -> str:
    tts = gTTS(text)
    tts.save(filename)
    return filename

# --- UI ---
st.set_page_config(page_title="Voice FAQ Chatbot", page_icon="🎤", layout="centered")
st.title("🎤 Voice-Enabled FAQ Chatbot")
st.caption("Ask me FAQs using your voice or text!")

ensure_csv()
faq_df = load_faq()

col1, col2 = st.columns(2)
with col1:
    text_input = st.text_input("💬 Type your Question:", placeholder="e.g. How can I reset my password?")
    if text_input:
        st.session_state.user_query = text_input

with col2:
    if st.button("🎙️ Speak"):
        user_query = record_audio()
        st.write(f"🧑 You (Voice): {user_query}")
        if user_query.strip():
            log_message("🧑 You", user_query)
            answer = generate_response(user_query, faq_df)
            log_message("🤖 Bot", answer)
            audio_file = speak_text(answer)
            st.audio(audio_file, format="audio/mp3")

if st.button("Ask"):
    if st.session_state.user_query.strip():
        log_message("🧑 You", st.session_state.user_query)
        answer = generate_response(st.session_state.user_query, faq_df)
        log_message("🤖 Bot", answer)
        audio_file = speak_text(answer)
        st.audio(audio_file, format="audio/mp3")
        st.session_state.user_query = ""
    else:
        st.warning("Please enter or speak a question first.")

if st.session_state.chat_history:
    st.markdown("### 💬 Conversation")
    for chat in st.session_state.chat_history:
        st.markdown(f"**{chat['sender']} ({chat['time']}):** {chat['message']}")
