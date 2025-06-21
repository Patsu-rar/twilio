from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, FileResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
import requests, os, uuid, logging
import json

load_dotenv()

TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
LANGFLOW_URL  = os.getenv("LANGFLOW_URL")
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
PUBLIC_URL = os.getenv("PUBLIC_URL")

app = FastAPI(title="Dream Roast API")
logging.basicConfig(level=logging.INFO)

headers = {
    "Content-Type": "application/json"
}

def get_roast(dream: str, session_id: str) -> str:
    payload = {
        "input_value": dream,
        "input_type": "chat",
        "output_type": "chat",
    }
    try:
        r = requests.post(LANGFLOW_URL, data=json.dumps(payload), headers=headers)
        r.raise_for_status()
        data = r.json()
        
        return  data['outputs'][0]['outputs'][0]['results']['message']['data']['text']
    except Exception as e:
        logging.error(f"Langflow error: {e}")
        return "Roast malfunction! Even comedians bomb sometimes."

def tts_elevenlabs(text: str) -> str | None:
    if not ELEVEN_KEY or not PUBLIC_URL:
        return None
    url  = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}"
    head = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.3, "similarity_boost": 0.75}
    }
    try:
        r = requests.post(url, headers=head, json=body, timeout=40)
        r.raise_for_status()
        audio_id = str(uuid.uuid4())
        file_path = f"/tmp/{audio_id}.mp3"
        with open(file_path, "wb") as f:
            f.write(r.content)
        return f"{PUBLIC_URL}/audio/{audio_id}.mp3"
    except Exception as e:
        logging.error(f"ElevenLabs TTS error: {e}")
        return None

@app.get("/audio/{audio_id}.mp3")
async def serve_audio(audio_id: str):
    file_path = f"/tmp/{audio_id}.mp3"
    return FileResponse(file_path, media_type="audio/mpeg")

@app.post("/sms", response_class=PlainTextResponse)
async def sms_reply(request: Request):
    form = await request.form()
    dream = form.get("Body", "").strip()
    session_id = form.get("From", str(uuid.uuid4()))
    roast = get_roast(dream, session_id)
    print(roast)    
    return roast

@app.post("/voice", response_class=PlainTextResponse)
async def voice_reply(request: Request):
    form = await request.form()
    speech_result = form.get("SpeechResult")
    caller = form.get("From", str(uuid.uuid4()))

    twiml = VoiceResponse()

    if not speech_result:
        gather = Gather(input="speech", timeout=8, action="/voice", method="POST")
        gather.say("Hey dreamer! Tell me your weird dream after the beep.")
        gather.play("https://api.twilio.com/cowbell.mp3")
        twiml.append(gather)
        twiml.redirect("/voice")
        return str(twiml)

    roast = get_roast(speech_result, caller)
    twiml.say(f"Analyzing dream … {roast}")
    twiml.hangup()
    return str(twiml)
