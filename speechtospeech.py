import asyncio
import wave
import pyaudio
import uvicorn
import openai
import pyttsx3
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# OpenAI API key
openai.api_key = 'sk-proj-jccHQRGxu7TXjMvAthN7T3BlbkFJBYiZ0mes5k6sHEA0MQoe'

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "output.wav"

prompts = {
    "1": "You are a fast food expert specializing in KFC.",
    "2": "You are a knowledgeable police officer here to assist with inquiries.",
    "3": "You are a healthcare professional ready to provide medical advice."
}

async def record_audio():
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []

    try:
        for _ in range(int(RATE / CHUNK * RECORD_SECONDS)):
            frames.append(stream.read(CHUNK))
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

    with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    return WAVE_OUTPUT_FILENAME

def transcribe_audio(audio_file_path):
    with open(audio_file_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe(
            model="whisper-1",
            file=audio_file,
            response_format='json',
            language='en'
        )
    return transcript['text']

async def generate_response(prompt, dialogue_history, custom_prompt):
    dialogue_history.append({"role": "user", "content": prompt})
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": custom_prompt}, *dialogue_history]
    )
    ai_response = response['choices'][0]['message']['content'].strip()
    dialogue_history.append({"role": "system", "content": ai_response})
    return ai_response

async def speak_text(text):
    loop = asyncio.get_event_loop()
    engine = pyttsx3.init()

    def _speak():
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[0].id)
        engine.say(text)
        engine.runAndWait()

    await loop.run_in_executor(None, _speak)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    dialogue_history = []
    selected_prompt = None

    try:
        while True:
            data = await websocket.receive_text()

            if data in prompts:
                selected_prompt = prompts[data]
                await websocket.send_text(f'{{"type": "info", "content": "Prompt set to {selected_prompt}"}}')

            elif data == "start":
                if not selected_prompt:
                    await websocket.send_text('{"type": "error", "content": "Please select a prompt first"}')
                    continue

                audio_file_path = await record_audio()
                transcription = transcribe_audio(audio_file_path)
                ai_response = await generate_response(transcription, dialogue_history, selected_prompt)
                await speak_text(ai_response)
                await websocket.send_text(f'{{"type": "user", "content": "{transcription}"}}')
                await websocket.send_text(f'{{"type": "ai", "content": "{ai_response}"}}')

            elif data == "stop":
                await websocket.send_text('{"type": "info", "content": "Session stopped"}')
                break

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
        await websocket.send_text(f'{{"type": "error", "content": "An error occurred: {e}"}}')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
