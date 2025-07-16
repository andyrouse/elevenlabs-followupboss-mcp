#!/usr/bin/env python3
"""
HTTP API server for FollowUp Boss integration
Allows external services like ElevenLabs to interact with FollowUp Boss
"""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
from fubmcp import FollowUpBossClient

app = FastAPI(title="FollowUp Boss API", version="1.0.0")

class PersonCreate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None

class EventCreate(BaseModel):
    type: Optional[str] = "other"
    person: PersonCreate
    note: Optional[str] = None
    source: Optional[str] = None

class NoteCreate(BaseModel):
    person_id: str
    body: str
    is_html: bool = False

@app.post("/people")
async def create_person(person: PersonCreate):
    """Create a new contact"""
    api_key = os.getenv("FOLLOWUP_BOSS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    
    client = FollowUpBossClient(api_key)
    try:
        result = await client.create_person(person.dict(exclude_none=True))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await client.close()

@app.post("/events")
async def create_event(event: EventCreate):
    """Create an event/interaction (preferred method for new contacts)"""
    api_key = os.getenv("FOLLOWUP_BOSS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    
    client = FollowUpBossClient(api_key)
    try:
        result = await client.create_event(event.dict(exclude_none=True))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await client.close()

@app.post("/notes")
async def create_note(note: NoteCreate):
    """Create a note for a contact"""
    api_key = os.getenv("FOLLOWUP_BOSS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    
    client = FollowUpBossClient(api_key)
    try:
        data = {
            "personId": note.person_id,
            "body": note.body,
            "isHtml": note.is_html
        }
        result = await client.create_note(data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await client.close()

@app.get("/people")
async def list_people(limit: int = 25, offset: int = 0):
    """List contacts"""
    api_key = os.getenv("FOLLOWUP_BOSS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    
    client = FollowUpBossClient(api_key)
    try:
        result = await client.list_people(limit=limit, offset=offset)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await client.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)