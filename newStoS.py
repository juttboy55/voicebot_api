
import asyncio
import wave
import pyaudio
import uvicorn
import openai
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from gtts import gTTS
import io

# Replace with your OpenAI API key
openai.api_key = 'sk-proj-jccHQRGxu7TXjMvAthN7T3BlbkFJBYiZ0mes5k6sHEA0MQoe'

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audio recording parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 3  # Reduce recording time to speed up response
WAVE_OUTPUT_FILENAME = "output.wav"

async def record_audio():
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    frames = []

    try:
        for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

    # Save the recorded data as a WAV file
    with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    return WAVE_OUTPUT_FILENAME

async def transcribe_audio(audio_file_path):
    with open(audio_file_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe(
            model="whisper-1",
            file=audio_file,
            response_format='json',
            language='en'
        )
    return transcript['text']

async def generate_response(prompt, dialogue_history):
    dialogue_history.append({"role": "user", "content": prompt})

    response = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a supportive aide."},
            *dialogue_history
        ]
    )

    ai_response = response['choices'][0]['message']['content'].strip()
    dialogue_history.append({"role": "system", "content": ai_response})

    return ai_response

async def text_to_speech(text):
    tts = gTTS(text=text, lang='en')
    audio_bytes = io.BytesIO()
    tts.write_to_fp(audio_bytes)
    audio_bytes.seek(0)
    return audio_bytes.read()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    dialogue_history = []

    try:
        while True:
            data = await websocket.receive_text()
            if data == "start":
                audio_file_path = await record_audio()
                transcription = await transcribe_audio(audio_file_path)
                ai_response = await generate_response(transcription, dialogue_history)
                tts_audio = await text_to_speech(ai_response)
                await websocket.send_text(f'{{"type": "user", "content": "{transcription}"}}')
                await websocket.send_text(f'{{"type": "ai", "content": "{ai_response}"}}')
                await websocket.send_bytes(tts_audio)
            elif data == "stop":
                break
    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
