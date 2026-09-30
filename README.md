# Silicon Intelligence

**Air-gapped voice AI assistant for Snapdragon X Elite.** Voice in, local LLM, voice out. No cloud calls.

Built for the Qualcomm Snapdragon AI Lab Challenge.

## Pipeline

```
Mic / text  ->  Whisper (Base) STT  ->  SmolLM2-135M-Instruct  ->  SAPI5 TTS  ->  audio playback
```

| Stage | Component |
|---|---|
| UI | Streamlit, Google-style prompt bar with mic toggle |
| STT | OpenAI Whisper (Base), local |
| LLM | HuggingFaceTB/SmolLM2-135M-Instruct |
| TTS | pyttsx3 (Windows SAPI5), offline |
| Profiling | `snapdragon_export.py` with `qai-hub` |

## Files

- `ai.py`: Streamlit app
- `snapdragon_export.py`: Qualcomm AI Hub profiling script
- `requirements.txt`: dependencies
- launcher `.bat`: one-click start

## Run

```bash
pip install -r requirements.txt
streamlit run ai.py
```

Models download once on first run; after that the app works with networking disabled.

## Qualcomm AI Hub

```bash
qai-hub configure --api_token <YOUR_TOKEN>
python snapdragon_export.py
```

## Roadmap

1. On-device RAG for private documents
2. INT4 quantization via Qualcomm AI Engine Direct
