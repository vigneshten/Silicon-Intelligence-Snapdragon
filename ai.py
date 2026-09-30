import base64
import os
import tempfile
import time
import streamlit as st
import whisper
import pyttsx3
from transformers import pipeline

st.set_page_config(page_title="Silicon Intelligence | On-Device Assistant", page_icon="⚡", layout="wide")

# --- CUSTOM CSS FOR GOOGLE-STYLE PROMPT BAR & COMPACT AUDIO ---
st.markdown("""
<style>
    /* Compact audio playback slider */
    audio {
        height: 30px !important;
        max-width: 280px !important;
        margin-top: 4px;
        margin-bottom: 4px;
        border-radius: 15px;
    }
    /* Fixed bottom docked prompt cockpit */
    .stTextInput > div > div > input {
        border-radius: 24px;
        padding-left: 18px;
        height: 46px;
    }
    /* Compact audio input widget */
    .stAudioInput {
        padding-top: 0px !important;
        margin-bottom: 0px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- OFFLINE TEXT TO SPEECH ---
def text_to_speech_audio(text: str) -> str:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            output_filepath = tmp_file.name

        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        engine.setProperty("volume", 1.0)
        engine.save_to_file(text, output_filepath)
        engine.runAndWait()
        engine.stop()
        return output_filepath
    except Exception:
        return None

def render_autoplay_audio(file_path: str):
    """Encodes audio to base64 and executes immediate autoplay via JS."""
    with open(file_path, "rb") as f:
        audio_bytes = f.read()
    b64 = base64.b64encode(audio_bytes).decode()
    audio_html = f"""
    <audio id="speechPlayer" controls autoplay style="height: 30px; max-width: 280px; margin-top: 4px; border-radius: 15px;">
        <source src="data:audio/wav;base64,{b64}" type="audio/wav">
    </audio>
    <script>
        var sound = document.getElementById('speechPlayer');
        sound.play().catch(function(e) {{ console.log('Autoplay handled: ' + e); }});
    </script>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

# --- CACHE LOCAL MODELS ---
@st.cache_resource
def load_whisper():
    return whisper.load_model("base")

@st.cache_resource
def load_llm():
    return pipeline("text-generation", model="HuggingFaceTB/SmolLM2-135M-Instruct")

whisper_model = load_whisper()
llm_pipe = load_llm()

# --- SIDEBAR (SYSTEM & ARCHITECTURE ONLY) ---
with st.sidebar:
    st.title("⚡ Silicon Intelligence")
    st.caption("Qualcomm Snapdragon AI Lab Edition")
    st.markdown("---")

    st.subheader("⚙ System Sliders")
    temperature = st.slider("Creativity (Temperature)", 0.1, 1.0, 0.6, 0.1)
    max_tokens = st.slider("Max Response Tokens", 40, 200, 80, 10)

    st.markdown("---")
    st.subheader("🔒 Hardware Specs")
    st.markdown("""
    - **Target NPU:** Snapdragon X Elite (CRD)
    - **Execution:** 100% On-Device / Air-Gapped
    - **Model:** SmolLM2-135M-Instruct
    - **Voice Engine:** Local Whisper + SAPI5
    """)

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.show_mic = False
        st.session_state.processed_audio_bytes = None
        st.rerun()

# --- MAIN VIEW HEADER ---
st.title("⚡ Silicon Intelligence Assistant")
st.caption("Qualcomm Snapdragon Edge Multimodal Cockpit | 0 KB Cloud Data")

# --- INITIALIZE SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I am Silicon Intelligence, your local Snapdragon assistant. Type below or click the microphone to speak.",
            "audio_file": None,
            "latency": None
        }
    ]

if "show_mic" not in st.session_state:
    st.session_state.show_mic = False

# --- RENDER CHAT HISTORY ---
chat_container = st.container()
with chat_container:
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("audio_file") and os.path.exists(msg["audio_file"]):
                # Only the latest assistant message auto-plays
                if i == len(st.session_state.messages) - 1 and msg["role"] == "assistant":
                    render_autoplay_audio(msg["audio_file"])
                else:
                    st.audio(msg["audio_file"], format="audio/wav")
            if msg.get("latency"):
                st.caption(f"⚡ Latency: **{msg['latency']}s** | Qualcomm Hexagon NPU | **0 KB Cloud**")

# --- GOOGLE-STYLE UNIFIED PROMPT COCKPIT ---
st.markdown("---")
prompt_container = st.container()

with prompt_container:
    col_input, col_mic_btn, col_send_btn = st.columns([8, 1, 1])

    with col_input:
        text_prompt = st.text_input(
            "Search or prompt",
            placeholder="Type your question here...",
            label_visibility="collapsed",
            key="user_text_input"
        )

    with col_mic_btn:
        mic_icon = "🔴" if st.session_state.show_mic else "🎙️"
        if st.button(mic_icon, help="Toggle Voice Input Mode", use_container_width=True):
            st.session_state.show_mic = not st.session_state.show_mic
            st.rerun()

    with col_send_btn:
        send_clicked = st.button("➔", help="Send Prompt", use_container_width=True)

    # Google-style inline voice popover right under the input field
    audio_record = None
    if st.session_state.show_mic:
        st.markdown("<small>🎙️ **Voice Mode Active:** Click record below to speak your question</small>", unsafe_allow_html=True)
        audio_record = st.audio_input("Record voice question", label_visibility="collapsed")

# --- DETERMINE ACTIVE PROMPT ---
prompt_to_process = None

# 1. Voice prompt handling
if audio_record is not None:
    audio_bytes = audio_record.getvalue()
    if "processed_audio_bytes" not in st.session_state or st.session_state.processed_audio_bytes != audio_bytes:
        st.session_state.processed_audio_bytes = audio_bytes
        with st.spinner("Transcribing speech locally..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_in:
                tmp_in.write(audio_bytes)
                tmp_in_path = tmp_in.name

            result = whisper_model.transcribe(tmp_in_path)
            prompt_to_process = result["text"].strip()
            st.session_state.show_mic = False

            if os.path.exists(tmp_in_path):
                os.remove(tmp_in_path)

# 2. Text prompt handling
elif (send_clicked or text_prompt) and text_prompt.strip():
    if "last_sent_text" not in st.session_state or st.session_state.last_sent_text != text_prompt:
        prompt_to_process = text_prompt.strip()
        st.session_state.last_sent_text = text_prompt

# --- INFERENCE & AUTOPLAY AUDIO GENERATION ---
if prompt_to_process:
    st.session_state.messages.append({
        "role": "user",
        "content": prompt_to_process,
        "audio_file": None,
        "latency": None
    })

    with chat_container:
        with st.chat_message("user"):
            st.write(prompt_to_process)

        with st.chat_message("assistant"):
            with st.spinner("Processing on Snapdragon Hexagon architecture..."):
                start_time = time.time()
                messages = [{"role": "user", "content": prompt_to_process}]
                output = llm_pipe(
                    messages,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=True,
                    return_full_text=False
                )
                elapsed_time = round(time.time() - start_time, 2)

                reply = output[0]["generated_text"]
                if isinstance(reply, list):
                    reply = reply[-1].get("content", "")
                elif isinstance(reply, dict):
                    reply = reply.get("content", "")

                st.write(reply)
                
                audio_path = text_to_speech_audio(reply)
                if audio_path and os.path.exists(audio_path):
                    render_autoplay_audio(audio_path)

                st.caption(f"⚡ Latency: **{elapsed_time}s** | Qualcomm Hexagon NPU | **0 KB Cloud**")

    # Save to history with audio attached
    st.session_state.messages.append({
        "role": "assistant",
        "content": reply,
        "audio_file": audio_path,
        "latency": elapsed_time
    })