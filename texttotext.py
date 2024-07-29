import openai
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Replace with your OpenAI API key
openai.api_key = ''

app = FastAPI()


def get_api_response(prompt: str) -> str | None:
    try:
        response = openai.ChatCompletion.create(
            model='gpt-4',
            messages=[
                {"role": "system", "content": "You will pretend to be a skater dude that ends every response with 'ye'."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=150,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0.6
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print('ERROR:', e)
        return None

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            bot_response = get_api_response(data)
            if bot_response:
                await websocket.send_text(f'Bot: {bot_response}')
            else:
                await websocket.send_text('Bot: Something went wrong...')
    except WebSocketDisconnect:
        print("Client disconnected")

# For health check
@app.get("/")
async def root():
    return {"message": "WebSocket server is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("your_filename:app", host="0.0.0.0", port=8000, reload=True)