#!/usr/bin/env python3
"""
Webhook server for ElevenLabs integration
Handles incoming webhooks and creates FollowUp Boss events
"""
import os
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import logging
from fubmcp import FollowUpBossClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook_server")

app = FastAPI(title="ElevenLabs Webhook Handler", version="1.0.0")

class ElevenLabsWebhook(BaseModel):
    """Expected structure from ElevenLabs webhook"""
    # Adjust these fields based on actual ElevenLabs webhook payload
    call_id: Optional[str] = None
    caller_phone: Optional[str] = None
    caller_name: Optional[str] = None
    call_duration: Optional[int] = None
    transcript: Optional[str] = None
    call_outcome: Optional[str] = None
    timestamp: Optional[str] = None

@app.post("/webhook/elevenlabs")
async def handle_elevenlabs_webhook(webhook_data: ElevenLabsWebhook):
    """Handle incoming webhook from ElevenLabs"""
    logger.info(f"Received ElevenLabs webhook: {webhook_data}")
    
    api_key = os.getenv("FOLLOWUP_BOSS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="FollowUp Boss API key not configured")
    
    client = FollowUpBossClient(api_key)
    try:
        # Create event data for FollowUp Boss
        event_data = {
            "type": "call",
            "person": {
                "name": webhook_data.caller_name or "Unknown Caller",
                "phone": webhook_data.caller_phone,
                "source": "ElevenLabs Phone Call"
            },
            "note": f"Call transcript: {webhook_data.transcript}" if webhook_data.transcript else None,
            "source": "ElevenLabs"
        }
        
        # Create the event in FollowUp Boss
        result = await client.create_event(event_data)
        logger.info(f"Created FollowUp Boss event: {result}")
        
        return {"status": "success", "event_id": result.get("event", {}).get("id")}
        
    except ValueError as e:
        logger.error(f"FollowUp Boss API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await client.close()

@app.post("/webhook/generic")
async def handle_generic_webhook(request: Request):
    """Handle generic webhook payload"""
    try:
        payload = await request.json()
        logger.info(f"Received generic webhook: {payload}")
        
        # Process the payload and extract relevant data
        # This is a template - adjust based on your needs
        
        return {"status": "received", "payload": payload}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)