#!/usr/bin/env python3
"""
ElevenLabs-compatible MCP bridge server
Creates an SSE endpoint that ElevenLabs can connect to
"""
import asyncio
import json
import os
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fubmcp import FollowUpBossClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elevenlabs_bridge")

app = FastAPI(title="ElevenLabs FollowUp Boss Bridge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ElevenLabsBridge:
    def __init__(self):
        self.api_key = os.getenv("FOLLOWUP_BOSS_API_KEY")
        if not self.api_key:
            raise ValueError("FOLLOWUP_BOSS_API_KEY environment variable not set")
        self.clients = set()
    
    async def create_contact_from_call(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a contact in FollowUp Boss from call data"""
        client = FollowUpBossClient(self.api_key)
        try:
            # Extract information from call data
            caller_name = call_data.get("caller_name", "Unknown Caller")
            caller_phone = call_data.get("caller_phone")
            transcript = call_data.get("transcript", "")
            call_outcome = call_data.get("outcome", "completed")
            
            # Create event data
            event_data = {
                "type": "call",
                "person": {
                    "name": caller_name,
                    "phone": caller_phone,
                    "source": "ElevenLabs AI Call"
                },
                "note": f"AI Call Transcript:\n{transcript}" if transcript else "AI call completed",
                "source": "ElevenLabs"
            }
            
            result = await client.create_event(event_data)
            logger.info(f"Created FollowUp Boss event: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            raise
        finally:
            await client.close()

bridge = ElevenLabsBridge()

@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for ElevenLabs integration"""
    async def event_generator():
        client_id = id(request)
        bridge.clients.add(client_id)
        
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'message': 'FollowUp Boss bridge ready'})}\n\n"
            
            # Keep connection alive
            while True:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': asyncio.get_event_loop().time()})}\n\n"
                
        except asyncio.CancelledError:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"SSE error for client {client_id}: {e}")
        finally:
            bridge.clients.discard(client_id)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.post("/webhook/call-completed")
async def handle_call_completed(call_data: dict):
    """Handle completed call webhook from ElevenLabs"""
    try:
        logger.info(f"Received call completion data: {call_data}")
        
        # Create contact in FollowUp Boss
        result = await bridge.create_contact_from_call(call_data)
        
        return {
            "status": "success",
            "message": "Contact created in FollowUp Boss",
            "event_id": result.get("event", {}).get("id")
        }
        
    except Exception as e:
        logger.error(f"Error handling call completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/generic")
async def handle_generic_webhook(webhook_data: dict):
    """Handle generic webhook from ElevenLabs"""
    try:
        logger.info(f"Received generic webhook: {webhook_data}")
        
        # Process based on webhook type
        if webhook_data.get("event_type") == "call_completed":
            return await handle_call_completed(webhook_data.get("data", {}))
        
        return {"status": "received", "message": "Webhook processed"}
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools")
async def list_tools():
    """List available tools for ElevenLabs"""
    return {
        "tools": [
            {
                "name": "create_contact_from_call",
                "description": "Create a contact in FollowUp Boss from call data",
                "parameters": {
                    "caller_name": "string",
                    "caller_phone": "string", 
                    "transcript": "string",
                    "outcome": "string"
                }
            }
        ]
    }

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "service": "elevenlabs-followupboss-bridge",
        "connected_clients": len(bridge.clients)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)