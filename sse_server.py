#!/usr/bin/env python3
"""
SSE-compatible MCP server for ElevenLabs integration
Exposes FollowUp Boss functionality via Server-Sent Events
"""
import asyncio
import json
import os
import logging
from typing import Any, Dict, List
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fubmcp import FollowUpBossClient, app as mcp_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sse_server")

# Create FastAPI app for SSE endpoint
sse_app = FastAPI(title="FollowUp Boss MCP SSE Server", version="1.0.0")

# Add CORS middleware
sse_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MCPSSEHandler:
    def __init__(self):
        self.api_key = os.getenv("FOLLOWUP_BOSS_API_KEY")
        if not self.api_key:
            raise ValueError("FOLLOWUP_BOSS_API_KEY environment variable not set")
    
    async def handle_mcp_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP protocol messages"""
        try:
            if message.get("method") == "tools/list":
                # Return available tools
                tools = await mcp_app._tool_handlers[0]()
                return {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "result": {"tools": [tool.model_dump() for tool in tools]}
                }
            
            elif message.get("method") == "tools/call":
                # Handle tool calls
                params = message.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                # Use the MCP server's tool handler
                result = await mcp_app._tool_handlers[1](tool_name, arguments)
                
                return {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "result": {
                        "content": [content.model_dump() for content in result]
                    }
                }
            
            elif message.get("method") == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "followup-boss-mcp",
                            "version": "1.0.0"
                        }
                    }
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {message.get('method')}"
                    }
                }
                
        except Exception as e:
            logger.error(f"Error handling MCP message: {e}")
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }

handler = MCPSSEHandler()

@sse_app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP communication"""
    async def event_generator():
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'message': 'FollowUp Boss MCP Server connected'})}\n\n"
            
            # Keep connection alive and handle any incoming messages
            while True:
                await asyncio.sleep(1)
                # Send heartbeat
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': asyncio.get_event_loop().time()})}\n\n"
                
        except asyncio.CancelledError:
            logger.info("SSE connection cancelled")
        except Exception as e:
            logger.error(f"SSE error: {e}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@sse_app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Handle MCP JSON-RPC messages"""
    try:
        message = await request.json()
        logger.info(f"Received MCP message: {message}")
        
        response = await handler.handle_mcp_message(message)
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

@sse_app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "server": "followup-boss-mcp-sse"}

if __name__ == "__main__":
    uvicorn.run(sse_app, host="0.0.0.0", port=8002)