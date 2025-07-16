#!/usr/bin/env python3
"""
ElevenLabs-compatible MCP server for FollowUp Boss integration
Implements JSON-RPC 2.0 over SSE as expected by ElevenLabs
"""
import asyncio
import json
import os
import logging
from typing import Any, Dict, List, Optional
from dataclasses import asdict
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fubmcp import FollowUpBossClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elevenlabs_mcp")

app = FastAPI(title="ElevenLabs FollowUp Boss MCP", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ElevenLabsMCPServer:
    def __init__(self):
        self.api_key = os.getenv("FOLLOWUP_BOSS_API_KEY")
        if not self.api_key:
            raise ValueError("FOLLOWUP_BOSS_API_KEY environment variable not set")
    
    async def handle_jsonrpc(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC 2.0 requests"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "followup-boss-elevenlabs",
                            "version": "1.0.0"
                        }
                    }
                }
            
            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": [
                            {
                                "name": "log_call",
                                "description": "Log a completed call to FollowUp Boss CRM",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "caller_name": {"type": "string"},
                                        "caller_phone": {"type": "string"},
                                        "transcript": {"type": "string"},
                                        "call_duration": {"type": "integer"},
                                        "call_outcome": {"type": "string"},
                                        "call_summary": {"type": "string"}
                                    },
                                    "required": ["caller_name", "caller_phone"]
                                }
                            },
                            {
                                "name": "create_followup_task",
                                "description": "Create a follow-up task in FollowUp Boss",
                                "inputSchema": {
                                    "type": "object", 
                                    "properties": {
                                        "person_id": {"type": "string"},
                                        "task_description": {"type": "string"},
                                        "due_date": {"type": "string"},
                                        "priority": {"type": "string", "enum": ["low", "medium", "high"]}
                                    },
                                    "required": ["person_id", "task_description"]
                                }
                            }
                        ]
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "log_call":
                    result = await self._log_call(arguments)
                elif tool_name == "create_followup_task":
                    result = await self._create_followup_task(arguments)
                else:
                    raise ValueError(f"Unknown tool: {tool_name}")
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": result
                            }
                        ]
                    }
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def _log_call(self, args: Dict[str, Any]) -> str:
        """Log a call to FollowUp Boss"""
        client = FollowUpBossClient(self.api_key)
        try:
            # Create event for the call
            event_data = {
                "type": "call",
                "person": {
                    "name": args.get("caller_name", "Unknown"),
                    "phone": args.get("caller_phone"),
                    "source": "ElevenLabs AI Call"
                },
                "note": self._format_call_note(args),
                "source": "ElevenLabs"
            }
            
            result = await client.create_event(event_data)
            event_id = result.get("event", {}).get("id", "unknown")
            
            return f"✅ Call logged successfully in FollowUp Boss (Event ID: {event_id})"
            
        except Exception as e:
            logger.error(f"Error logging call: {e}")
            return f"❌ Failed to log call: {str(e)}"
        finally:
            await client.close()
    
    async def _create_followup_task(self, args: Dict[str, Any]) -> str:
        """Create a follow-up task"""
        client = FollowUpBossClient(self.api_key)
        try:
            task_data = {
                "description": args.get("task_description"),
                "personId": args.get("person_id"),
                "dueDate": args.get("due_date"),
            }
            
            result = await client.create_task(task_data)
            task_id = result.get("task", {}).get("id", "unknown")
            
            return f"✅ Follow-up task created (Task ID: {task_id})"
            
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return f"❌ Failed to create task: {str(e)}"
        finally:
            await client.close()
    
    def _format_call_note(self, args: Dict[str, Any]) -> str:
        """Format call information into a note"""
        note_parts = ["📞 AI Call Summary"]
        
        if args.get("call_duration"):
            note_parts.append(f"Duration: {args['call_duration']} seconds")
        
        if args.get("call_outcome"):
            note_parts.append(f"Outcome: {args['call_outcome']}")
        
        if args.get("call_summary"):
            note_parts.append(f"Summary: {args['call_summary']}")
        
        if args.get("transcript"):
            note_parts.append(f"Transcript:\n{args['transcript']}")
        
        return "\n\n".join(note_parts)

server = ElevenLabsMCPServer()

@app.get("/sse")
async def sse_endpoint():
    """SSE endpoint for ElevenLabs"""
    async def event_stream():
        # Send connection confirmation
        yield f"data: {json.dumps({'type': 'connected', 'server': 'followup-boss-mcp'})}\n\n"
        
        # Keep alive
        while True:
            await asyncio.sleep(30)
            yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Handle MCP JSON-RPC requests"""
    try:
        body = await request.json()
        logger.info(f"Received MCP request: {body}")
        
        response = await server.handle_jsonrpc(body)
        logger.info(f"Sending MCP response: {response}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in MCP endpoint: {e}")
        return {
            "jsonrpc": "2.0", 
            "error": {
                "code": -32700,
                "message": f"Parse error: {str(e)}"
            }
        }

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "elevenlabs-followupboss-mcp"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)