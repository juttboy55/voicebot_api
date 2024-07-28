import openai
import pyttsx3
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

# Replace with your OpenAI API key
openai.api_key = ''

app = FastAPI()

# Initialize the conversation history
conversation_history = [{"role": "system", "content": "You are a helpful assistant."}]

def ask_openai(prompt):
    global conversation_history
    
    # Add the user's prompt to the conversation history
    conversation_history.append({"role": "user", "content": prompt})

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=conversation_history
    )
    
    ai_response = response['choices'][0]['message']['content'].strip()
    
    # Add the AI's response to the conversation history
    conversation_history.append({"role": "assistant", "content": ai_response})
    
    return ai_response

def speak_text(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)    # Speed of speech
    engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)

    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[0].id)  # Use the first voice

    engine.say(text)
    engine.runAndWait()

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            response = ask_openai(data)
            speak_text(response)
            await websocket.send_text(response)
    except WebSocketDisconnect:
        await websocket.close()

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Text-to-Speech API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
