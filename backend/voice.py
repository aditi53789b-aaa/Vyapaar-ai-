from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any
from app.services.voice_service import parse_voice_transaction

router = APIRouter(prefix="/voice", tags=["Multilingual Voice Assistant"])

class VoiceInputRequest(BaseModel):
    transcript: str

@router.post("/parse")
def parse_voice(data: VoiceInputRequest) -> Dict[str, Any]:
    return parse_voice_transaction(data.transcript)
