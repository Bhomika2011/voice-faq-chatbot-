import streamlit as st
import pandas as pd
import openai
import speech_recognition as sr
from gtts import gTTS
import os
import datetime

# Load API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# Load FAQ dataset
def load_faq(path="faq.csv"):
    df = pd.read_csv(path)
    if "question" not in df.columns or "answer" not in df.columns:
        st.error("CSV must have 'question' and 'answer' columns!")
        st.stop()
    return df

faq_df = load_faq("faq.csv")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def log_message(sender, message):
    st.session_state.chat_history.append({
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "sender": sender,
        "message": message
    })

def generate_response(user_query, faq_df):
    faq_text = "\n".join([f"Q: {row['question']} \nA: {row['answer']}" for _, row in faq_df.iterrows()])

    prompt = f"""
    You are a polite and helpful FAQ chatbot.
    FAQs:

    {faq_text}

    User asked: "{user_query}"

    Based on the FAQs, give the best possible helpful answer.
    If not found, say: "Sorry, I don't have information about that."
    """

    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=200,
            temperature=0.2
        )
        return response["choices"][0]["text"].strip()
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def record_audio():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎙️ Listening... please speak your question")
        audio = recognizer.listen(source, phrase_time_limit=5)
        try:
            query = recognizer.recognize_google(audio)
            return query
        except sr.UnknownValueError:
            return "⚠️ Sorry, could not understand audio."
        except sr.RequestError:
            return "⚠️ Speech recognition service unavailable."

def speak_text(text, filename="response.mp3"):
    tts = gTTS(text)
    tts.save(filename)
    return filename

# Streamlit UI
st.set_page_config(page_title="Voice FAQ Chatbot", page_icon="🎤", layout="centered")
st.title("🎤 Voice-Enabled FAQ Chatbot")
st.caption("Ask me FAQs using your voice or text!")

# Input options
col1, col2 = st.columns(2)

with col1:
    user_query = st.text_input("💬 Type your Question:", placeholder="e.g. How can I reset my password?")

with col2:
    if st.button("🎙️ Speak"):
        user_query = record_audio()
        st.write(f"🧑 You (Voice): {user_query}")

# Ask button
if st.button("Ask"):
    if user_query.strip() != "":
        log_message("🧑 You", user_query)
        answer = generate_response(user_query, faq_df)
        log_message("🤖 Bot", answer)

        # Play TTS
        audio_file = speak_text(answer)
        st.audio(audio_file, format="audio/mp3")
    else:
        st.warning("Please enter or speak a question first.")

# Display chat history
if st.session_state.chat_history:
    st.markdown("### 💬 Conversation")
    for chat in st.session_state.chat_history:
        st.markdown(f"**{chat['sender']} ({chat['time']}):** {chat['message']}")

# Upload audio file option
uploaded_file = st.file_uploader("🎙️ Upload an audio file", type=["wav", "mp3", "m4a"])
if uploaded_file:
    recognizer = sr.Recognizer()
    with sr.AudioFile(uploaded_file) as source:
        audio = recognizer.record(source)
        query = recognizer.recognize_google(audio)
        st.write("🧑 You (Voice):", query)
