#!/usr/bin/env python3
"""
Secure ElevenLabs-compatible MCP server for FollowUp Boss integration
Production-ready with authentication, rate limiting, and input validation
"""
import asyncio
import json
import os
import logging
import re
import hmac
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import httpx
from fubmcp import FollowUpBossClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("secure_elevenlabs_mcp")

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Secure ElevenLabs FollowUp Boss MCP", 
    version="1.0.0",
    docs_url=None,  # Disable docs in production
    redoc_url=None
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://elevenlabs.io", "https://*.elevenlabs.io"],  # Restrict to ElevenLabs
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)

class SecureMCPServer:
    def __init__(self):
        self.api_key = os.getenv("FOLLOWUP_BOSS_API_KEY")
        self.webhook_secret = os.getenv("ELEVENLABS_WEBHOOK_SECRET")
        self.auth_token = os.getenv("MCP_AUTH_TOKEN")
        
        if not self.api_key:
            raise ValueError("FOLLOWUP_BOSS_API_KEY environment variable required")
        if not self.auth_token:
            raise ValueError("MCP_AUTH_TOKEN environment variable required")
            
        logger.info("Secure MCP Server initialized")
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify ElevenLabs webhook signature"""
        if not self.webhook_secret:
            logger.warning("No webhook secret configured - skipping signature verification")
            return True
            
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    
    def sanitize_input(self, text: str, max_length: int = 1000) -> str:
        """Sanitize user input"""
        if not isinstance(text, str):
            return ""
        
        # Remove potentially dangerous characters and limit length
        sanitized = re.sub(r'[<>"\'\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        return sanitized[:max_length].strip()
    
    def validate_phone(self, phone: str) -> bool:
        """Validate phone number format"""
        if not phone:
            return False
        # Basic phone validation - digits, spaces, hyphens, parentheses, plus
        return bool(re.match(r'^[\+\-\s\(\)\d]{10,}$', phone.strip()))
    
    async def handle_jsonrpc(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC 2.0 requests with validation"""
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
                        "capabilities": {"tools": {}},
                        "serverInfo": {
                            "name": "secure-followup-boss-mcp",
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
                                "description": "Securely log a completed call to FollowUp Boss CRM",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "caller_name": {"type": "string", "maxLength": 100},
                                        "caller_phone": {"type": "string", "pattern": r"^[\+\-\s\(\)\d]{10,}$"},
                                        "transcript": {"type": "string", "maxLength": 5000},
                                        "call_duration": {"type": "integer", "minimum": 0, "maximum": 7200},
                                        "call_outcome": {"type": "string", "maxLength": 50},
                                        "call_summary": {"type": "string", "maxLength": 500}
                                    },
                                    "required": ["caller_name", "caller_phone"],
                                    "additionalProperties": False
                                }
                            }
                        ]
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "log_call":
                    result = await self._log_call_secure(arguments)
                else:
                    raise ValueError(f"Unknown tool: {tool_name}")
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": result}]
                    }
                }
            
            else:
                logger.warning(f"Unknown method attempted: {method}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": "Method not found"
                    }
                }
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": "Internal server error"
                }
            }
    
    async def _log_call_secure(self, args: Dict[str, Any]) -> str:
        """Securely log a call with input validation"""
        # Validate and sanitize inputs
        caller_name = self.sanitize_input(args.get("caller_name", ""), 100)
        caller_phone = self.sanitize_input(args.get("caller_phone", ""), 20)
        transcript = self.sanitize_input(args.get("transcript", ""), 5000)
        call_summary = self.sanitize_input(args.get("call_summary", ""), 500)
        call_outcome = self.sanitize_input(args.get("call_outcome", ""), 50)
        
        # Validation
        if not caller_name or len(caller_name) < 2:
            return "❌ Invalid caller name"
        
        if not self.validate_phone(caller_phone):
            return "❌ Invalid phone number format"
        
        call_duration = args.get("call_duration", 0)
        if not isinstance(call_duration, int) or call_duration < 0 or call_duration > 7200:
            call_duration = 0
        
        client = FollowUpBossClient(self.api_key)
        try:
            event_data = {
                "type": "call",
                "person": {
                    "name": caller_name,
                    "phone": caller_phone,
                    "source": "ElevenLabs AI Call"
                },
                "note": self._format_secure_call_note({
                    "call_duration": call_duration,
                    "call_outcome": call_outcome,
                    "call_summary": call_summary,
                    "transcript": transcript
                }),
                "source": "ElevenLabs"
            }
            
            result = await client.create_event(event_data)
            event_id = result.get("event", {}).get("id", "unknown")
            
            logger.info(f"Call logged successfully for {caller_name} (Event ID: {event_id})")
            return f"✅ Call logged successfully (Event ID: {event_id})"
            
        except Exception as e:
            logger.error(f"Error logging call for {caller_name}: {str(e)}")
            return "❌ Failed to log call - please try again"
        finally:
            await client.close()
    
    def _format_secure_call_note(self, args: Dict[str, Any]) -> str:
        """Format call information securely"""
        note_parts = [f"📞 AI Call Summary - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"]
        
        if args.get("call_duration"):
            duration_min = args["call_duration"] // 60
            duration_sec = args["call_duration"] % 60
            note_parts.append(f"Duration: {duration_min}m {duration_sec}s")
        
        if args.get("call_outcome"):
            note_parts.append(f"Outcome: {args['call_outcome']}")
        
        if args.get("call_summary"):
            note_parts.append(f"Summary: {args['call_summary']}")
        
        if args.get("transcript"):
            note_parts.append(f"Transcript:\n{args['transcript']}")
        
        return "\n\n".join(note_parts)

server = SecureMCPServer()

async def verify_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify authentication token"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if credentials.credentials != server.auth_token:
        logger.warning(f"Invalid auth attempt from IP")
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    return credentials

@app.get("/sse")
@limiter.limit("5/minute")
async def sse_endpoint(request: Request, credentials: HTTPAuthorizationCredentials = Depends(verify_auth)):
    """Secure SSE endpoint"""
    async def event_stream():
        try:
            yield f"data: {json.dumps({'type': 'connected', 'server': 'secure-followup-boss-mcp', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            
            while True:
                await asyncio.sleep(30)
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.post("/mcp")
@limiter.limit("20/minute")
async def mcp_endpoint(
    request: Request, 
    credentials: HTTPAuthorizationCredentials = Depends(verify_auth)
):
    """Secure MCP endpoint"""
    try:
        body = await request.json()
        
        # Log request (without sensitive data)
        logger.info(f"MCP request from {get_remote_address(request)}: {body.get('method', 'unknown')}")
        
        response = await server.handle_jsonrpc(body)
        return response
        
    except json.JSONDecodeError:
        logger.warning("Invalid JSON received")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"MCP endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
@limiter.limit("10/minute")
async def health(request: Request):
    """Public health check"""
    return {
        "status": "healthy",
        "service": "secure-elevenlabs-followupboss-mcp",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)