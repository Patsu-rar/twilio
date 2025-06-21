from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv
import requests, os, uuid, logging
import json

load_dotenv()

TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
LANGFLOW_URL  = os.getenv("LANGFLOW_URL")

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
        twiml.append(gather)
        twiml.redirect("/voice")
        return str(twiml)

    roast = get_roast(speech_result, caller)
    twiml.say(f" {roast}")
    twiml.hangup()
    return str(twiml)
