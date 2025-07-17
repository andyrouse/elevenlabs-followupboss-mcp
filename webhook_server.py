#!/usr/bin/env python3
"""
Webhook server for ElevenLabs integration
Handles incoming webhooks and creates FollowUp Boss events
"""
import os
from fastapi import FastAPI, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import logging
import hmac
import hashlib
import time
from fubmcp import FollowUpBossClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook_server")

app = FastAPI(title="ElevenLabs Webhook Handler", version="1.0.0")

class TranscriptEntry(BaseModel):
    role: str
    message: str
    time_in_call_secs: Optional[int] = None
    tool_calls: Optional[Any] = None
    tool_results: Optional[Any] = None
    feedback: Optional[Any] = None
    conversation_turn_metrics: Optional[Dict[str, Any]] = None

class ElevenLabsWebhook(BaseModel):
    """Expected structure from ElevenLabs post-call transcription webhook"""
    type: str
    event_timestamp: int
    data: Dict[str, Any]  # Contains agent_id, conversation_id, transcript, metadata, etc.

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify ElevenLabs webhook signature"""
    if not signature or not secret:
        return False
    
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, f"sha256={expected_signature}")

def extract_info_from_transcript(transcript: list) -> Dict[str, str]:
    """Extract caller information from conversation transcript"""
    extracted = {
        "name": None,
        "phone": None,
        "email": None,
        "property_address": None,
        "interested": True
    }
    
    import re
    
    for entry in transcript:
        if entry.get("role") == "user":
            message = entry.get("message", "").lower()
            
            # Extract name patterns
            if not extracted["name"]:
                name_patterns = [
                    r"my name is ([a-z\s]+)",
                    r"i'm ([a-z\s]+)",
                    r"this is ([a-z\s]+)",
                    r"i am ([a-z\s]+)"
                ]
                for pattern in name_patterns:
                    match = re.search(pattern, message, re.IGNORECASE)
                    if match:
                        extracted["name"] = match.group(1).strip().title()
                        break
            
            # Extract phone
            if not extracted["phone"]:
                phone_match = re.search(r"\b(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b", message)
                if phone_match:
                    extracted["phone"] = phone_match.group()
            
            # Extract email
            if not extracted["email"]:
                email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", message)
                if email_match:
                    extracted["email"] = email_match.group()
            
            # Check interest level
            negative_phrases = ["not interested", "don't call", "remove me", "take me off"]
            if any(phrase in message for phrase in negative_phrases):
                extracted["interested"] = False
    
    return extracted

@app.post("/webhook/elevenlabs")
async def handle_elevenlabs_webhook(
    request: Request,
    x_elevenlabs_signature: Optional[str] = Header(None)
):
    """Handle incoming webhook from ElevenLabs"""
    # Get raw payload for signature verification
    payload = await request.body()
    webhook_data = await request.json()
    
    logger.info(f"Received ElevenLabs webhook: {webhook_data}")
    
    # Verify webhook signature if secret is configured
    webhook_secret = os.getenv("ELEVENLABS_WEBHOOK_SECRET")
    if webhook_secret and not verify_webhook_signature(payload, x_elevenlabs_signature, webhook_secret):
        logger.error("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    api_key = os.getenv("FOLLOWUP_BOSS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="FollowUp Boss API key not configured")
    
    client = FollowUpBossClient(api_key)
    try:
        # Extract data from ElevenLabs webhook payload
        data = webhook_data.get("data", {})
        transcript = data.get("transcript", [])
        metadata = data.get("metadata", {})
        analysis = data.get("analysis", {})
        dynamic_vars = data.get("conversation_initiation_client_data", {}).get("dynamic_variables", {})
        
        # Extract caller info from dynamic variables first
        caller_name = dynamic_vars.get("user_name", None)
        caller_phone = dynamic_vars.get("user_phone", None)
        
        # Extract additional info from transcript
        extracted_info = extract_info_from_transcript(transcript)
        
        # Use extracted info if not in dynamic vars
        if not caller_name:
            caller_name = extracted_info["name"] or "Unknown Caller"
        if not caller_phone:
            caller_phone = extracted_info["phone"] or "Unknown"
        
        # Format name properly and split into first/last
        first_name = "Unknown"
        last_name = "Caller"
        
        if caller_name and caller_name != "Unknown Caller":
            caller_name = caller_name.title()
            name_parts = caller_name.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])
            elif len(name_parts) == 1:
                first_name = name_parts[0]
                last_name = ""
        
        # Extract property details from transcript
        site_county = dynamic_vars.get("site_county", "")
        site_state = dynamic_vars.get("site_state", "")
        reference_number = dynamic_vars.get("reference_number", "")
        acreage = dynamic_vars.get("acreage", "")
        source = dynamic_vars.get("source", "ElevenLabs AI Call")
        
        # Build conversation transcript
        conversation_text = ""
        for entry in transcript:
            role = entry.get("role", "unknown")
            message = entry.get("message", "")
            time_in_call = entry.get("time_in_call_secs", "")
            conversation_text += f"[{time_in_call}s] {role.upper()}: {message}\n\n"
        
        # Get metadata
        call_duration = metadata.get("call_duration_secs", 0)
        call_cost = metadata.get("cost", 0) / 100  # Convert cents to dollars
        agent_id = data.get("agent_id", "Unknown")
        conversation_id = data.get("conversation_id", "Unknown")
        summary = analysis.get("transcript_summary", "No summary available")
        call_outcome = analysis.get("call_successful", "unknown")
        
        # Determine stage based on conversation
        stage = "Qualify"  # Default
        if "not interested" in conversation_text.lower():
            stage = "Seller not interested"
        elif "do not call" in conversation_text.lower() or "dnc" in conversation_text.lower():
            stage = "DNC"
        
        # Create event data for FollowUp Boss
        event_data = {
            "type": "call",
            "person": {
                "firstName": first_name,
                "lastName": last_name,
                "phone": caller_phone,
                "source": source,
                "stage": stage,
                "customSiteCounty": site_county,
                "customSiteState": site_state,
                "customReferenceNumber": reference_number,
                "customAcreage": acreage
            },
            "note": f"📞 AI Call Summary\n\n=== CALL DETAILS ===\nAgent ID: {agent_id}\nConversation ID: {conversation_id}\nDuration: {call_duration} seconds\nCost: ${call_cost:.2f}\nOutcome: {call_outcome}\n\n=== AI SUMMARY ===\n{summary}\n\n=== PROPERTY DETAILS ===\n- County: {site_county if site_county else 'Not provided'}\n- State: {site_state if site_state else 'Not provided'}\n- Reference: {reference_number if reference_number else 'Not provided'}\n- Acreage: {acreage if acreage else 'Not provided'}\n\n=== FULL TRANSCRIPT ===\n{conversation_text}",
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