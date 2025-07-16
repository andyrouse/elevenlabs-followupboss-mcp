#!/usr/bin/env python3
import asyncio
import os
import logging
from typing import Any, Optional, Dict, List
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
import mcp.types as types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fubmcp")

class FollowUpBossClient:
    def __init__(self, api_key: str):
        if not api_key or len(api_key.strip()) == 0:
            raise ValueError("API key is required")
        
        self.api_key = api_key.strip()
        self.base_url = "https://api.followupboss.com/v1"
        self.client = httpx.AsyncClient(
            auth=(self.api_key, ""),
            timeout=30.0,
            verify=True
        )
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            if method == "DELETE" and response.status_code == 204:
                return {"success": True}
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {method} {url}")
            if e.response.status_code == 401:
                raise ValueError("Invalid API key or insufficient permissions")
            elif e.response.status_code == 403:
                raise ValueError("Access forbidden - check user permissions")
            elif e.response.status_code == 429:
                raise ValueError("Rate limit exceeded - please try again later")
            else:
                raise ValueError(f"API request failed: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise ValueError("Failed to connect to FollowUp Boss API")
    
    async def list_people(self, limit: int = 25, offset: int = 0, **filters) -> Dict[str, Any]:
        params = {"limit": min(limit, 100), "offset": max(offset, 0)}
        
        for key, value in filters.items():
            if value is not None and str(value).strip():
                params[key] = str(value).strip()
        
        return await self._make_request("GET", "people", params=params)
    
    async def get_person(self, person_id: str) -> Dict[str, Any]:
        if not person_id or not person_id.strip():
            raise ValueError("Person ID is required")
        
        person_id = person_id.strip()
        return await self._make_request("GET", f"people/{person_id}")
    
    async def create_person(self, data: Dict[str, Any]) -> Dict[str, Any]:
        required_fields = {"name", "email"}
        if not any(field in data for field in required_fields):
            raise ValueError("Either name or email is required")
        
        clean_data = {}
        for key, value in data.items():
            if value is not None and str(value).strip():
                clean_data[key] = str(value).strip()
        
        return await self._make_request("POST", "people", json=clean_data)
    
    async def create_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data.get("person"):
            raise ValueError("Person data is required for events")
        
        clean_data = {}
        for key, value in data.items():
            if value is not None:
                if isinstance(value, dict):
                    clean_data[key] = {k: str(v).strip() if v else None for k, v in value.items() if v}
                else:
                    clean_data[key] = str(value).strip() if str(value).strip() else None
        
        return await self._make_request("POST", "events", json=clean_data)
    
    async def update_person(self, person_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not person_id or not person_id.strip():
            raise ValueError("Person ID is required")
        
        if not data:
            raise ValueError("Update data is required")
        
        person_id = person_id.strip()
        clean_data = {}
        for key, value in data.items():
            if value is not None and str(value).strip():
                clean_data[key] = str(value).strip()
        
        if not clean_data:
            raise ValueError("No valid update data provided")
        
        return await self._make_request("PUT", f"people/{person_id}", json=clean_data)
    
    async def delete_person(self, person_id: str) -> Dict[str, Any]:
        if not person_id or not person_id.strip():
            raise ValueError("Person ID is required")
        
        person_id = person_id.strip()
        return await self._make_request("DELETE", f"people/{person_id}")
    
    async def list_notes(self, limit: int = 25, offset: int = 0, person_id: Optional[str] = None) -> Dict[str, Any]:
        params = {"limit": min(limit, 100), "offset": max(offset, 0)}
        
        if person_id and person_id.strip():
            params["personId"] = person_id.strip()
        
        return await self._make_request("GET", "notes", params=params)
    
    async def get_note(self, note_id: str) -> Dict[str, Any]:
        if not note_id or not note_id.strip():
            raise ValueError("Note ID is required")
        
        note_id = note_id.strip()
        return await self._make_request("GET", f"notes/{note_id}")
    
    async def create_note(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data.get("personId"):
            raise ValueError("Person ID is required for notes")
        
        if not data.get("body"):
            raise ValueError("Note body is required")
        
        clean_data = {
            "personId": str(data["personId"]).strip(),
            "body": str(data["body"]).strip()
        }
        
        if data.get("isHtml"):
            clean_data["isHtml"] = bool(data["isHtml"])
        
        return await self._make_request("POST", "notes", json=clean_data)
    
    async def list_tasks(self, limit: int = 25, offset: int = 0, **filters) -> Dict[str, Any]:
        params = {"limit": min(limit, 100), "offset": max(offset, 0)}
        
        for key, value in filters.items():
            if value is not None and str(value).strip():
                params[key] = str(value).strip()
        
        return await self._make_request("GET", "tasks", params=params)
    
    async def create_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data.get("description"):
            raise ValueError("Task description is required")
        
        clean_data = {"description": str(data["description"]).strip()}
        
        if data.get("personId"):
            clean_data["personId"] = str(data["personId"]).strip()
        
        if data.get("dueDate"):
            clean_data["dueDate"] = str(data["dueDate"]).strip()
        
        if data.get("assignedTo"):
            clean_data["assignedTo"] = str(data["assignedTo"]).strip()
        
        return await self._make_request("POST", "tasks", json=clean_data)
    
    async def update_task(self, task_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not task_id or not task_id.strip():
            raise ValueError("Task ID is required")
        
        if not data:
            raise ValueError("Update data is required")
        
        task_id = task_id.strip()
        clean_data = {}
        
        for key in ["description", "dueDate", "assignedTo", "completed"]:
            if key in data:
                if key == "completed":
                    clean_data[key] = bool(data[key])
                else:
                    clean_data[key] = str(data[key]).strip() if data[key] else None
        
        if not clean_data:
            raise ValueError("No valid update data provided")
        
        return await self._make_request("PUT", f"tasks/{task_id}", json=clean_data)
    
    async def create_call(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data.get("personId"):
            raise ValueError("Person ID is required for calls")
        
        clean_data = {"personId": str(data["personId"]).strip()}
        
        if data.get("outcome"):
            clean_data["outcome"] = str(data["outcome"]).strip()
        
        if data.get("note"):
            clean_data["note"] = str(data["note"]).strip()
        
        if data.get("duration"):
            clean_data["duration"] = int(data["duration"])
        
        if data.get("callTime"):
            clean_data["callTime"] = str(data["callTime"]).strip()
        
        return await self._make_request("POST", "calls", json=clean_data)
    
    async def close(self):
        await self.client.aclose()

app = Server("fubmcp")

@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    return [
        Tool(
            name="list_people",
            description="List contacts from FollowUp Boss with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
                    "offset": {"type": "integer", "minimum": 0, "default": 0},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "name": {"type": "string"},
                    "source": {"type": "string"}
                },
                "additionalProperties": False
            }
        ),
        Tool(
            name="get_person",
            description="Get detailed information about a specific contact",
            inputSchema={
                "type": "object",
                "properties": {
                    "person_id": {"type": "string", "minLength": 1}
                },
                "required": ["person_id"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="create_person",
            description="Create a new contact in FollowUp Boss",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "email": {"type": "string", "format": "email"},
                    "phone": {"type": "string"},
                    "source": {"type": "string"},
                    "stage": {"type": "string"},
                    "assigned_to": {"type": "string"}
                },
                "anyOf": [
                    {"required": ["name"]},
                    {"required": ["email"]}
                ],
                "additionalProperties": False
            }
        ),
        Tool(
            name="create_event",
            description="Create an event/interaction for a contact (preferred method for adding new contacts)",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["call", "email", "text", "meeting", "other"]},
                    "person": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string", "format": "email"},
                            "phone": {"type": "string"},
                            "source": {"type": "string"},
                            "stage": {"type": "string"}
                        },
                        "anyOf": [
                            {"required": ["name"]},
                            {"required": ["email"]}
                        ]
                    },
                    "note": {"type": "string"},
                    "source": {"type": "string"}
                },
                "required": ["person"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="update_person",
            description="Update an existing contact's information",
            inputSchema={
                "type": "object",
                "properties": {
                    "person_id": {"type": "string", "minLength": 1},
                    "name": {"type": "string", "minLength": 1},
                    "email": {"type": "string", "format": "email"},
                    "phone": {"type": "string"},
                    "source": {"type": "string"},
                    "assigned_to": {"type": "string"}
                },
                "required": ["person_id"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="delete_person",
            description="Delete a contact from FollowUp Boss",
            inputSchema={
                "type": "object",
                "properties": {
                    "person_id": {"type": "string", "minLength": 1}
                },
                "required": ["person_id"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="list_notes",
            description="List notes with optional filtering by person",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
                    "offset": {"type": "integer", "minimum": 0, "default": 0},
                    "person_id": {"type": "string"}
                },
                "additionalProperties": False
            }
        ),
        Tool(
            name="get_note",
            description="Get details of a specific note",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "minLength": 1}
                },
                "required": ["note_id"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="create_note",
            description="Add a note to a contact",
            inputSchema={
                "type": "object",
                "properties": {
                    "person_id": {"type": "string", "minLength": 1},
                    "body": {"type": "string", "minLength": 1},
                    "is_html": {"type": "boolean", "default": False}
                },
                "required": ["person_id", "body"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="list_tasks",
            description="List tasks with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
                    "offset": {"type": "integer", "minimum": 0, "default": 0},
                    "person_id": {"type": "string"},
                    "assigned_to": {"type": "string"},
                    "completed": {"type": "boolean"}
                },
                "additionalProperties": False
            }
        ),
        Tool(
            name="create_task",
            description="Create a new task",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {"type": "string", "minLength": 1},
                    "person_id": {"type": "string"},
                    "due_date": {"type": "string"},
                    "assigned_to": {"type": "string"}
                },
                "required": ["description"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="update_task",
            description="Update an existing task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "due_date": {"type": "string"},
                    "assigned_to": {"type": "string"},
                    "completed": {"type": "boolean"}
                },
                "required": ["task_id"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="create_call",
            description="Log a phone call for a contact",
            inputSchema={
                "type": "object",
                "properties": {
                    "person_id": {"type": "string", "minLength": 1},
                    "outcome": {"type": "string"},
                    "note": {"type": "string"},
                    "duration": {"type": "integer", "minimum": 0},
                    "call_time": {"type": "string"}
                },
                "required": ["person_id"],
                "additionalProperties": False
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    api_key = os.getenv("FOLLOWUP_BOSS_API_KEY")
    if not api_key:
        return [types.TextContent(
            type="text",
            text="Error: FOLLOWUP_BOSS_API_KEY environment variable not set"
        )]
    
    client = FollowUpBossClient(api_key)
    
    try:
        if name == "list_people":
            result = await client.list_people(**arguments)
            people = result.get("people", [])
            
            if not people:
                return [types.TextContent(type="text", text="No contacts found")]
            
            response = f"Found {len(people)} contact(s):\n\n"
            for person in people:
                name = person.get("name", "No name")
                email = person.get("emails", [{}])[0].get("value", "No email") if person.get("emails") else "No email"
                phone = person.get("phones", [{}])[0].get("value", "No phone") if person.get("phones") else "No phone"
                response += f"• {name}\n  Email: {email}\n  Phone: {phone}\n  ID: {person.get('id', 'Unknown')}\n\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "get_person":
            result = await client.get_person(arguments["person_id"])
            person = result.get("person", {})
            
            name = person.get("name", "No name")
            emails = person.get("emails", [])
            phones = person.get("phones", [])
            source = person.get("source", "Unknown")
            
            response = f"Contact Details:\n"
            response += f"Name: {name}\n"
            response += f"ID: {person.get('id', 'Unknown')}\n"
            response += f"Source: {source}\n"
            
            if emails:
                response += f"Emails: {', '.join([e.get('value', '') for e in emails])}\n"
            if phones:
                response += f"Phones: {', '.join([p.get('value', '') for p in phones])}\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "create_person":
            result = await client.create_person(arguments)
            person = result.get("person", {})
            
            response = f"Successfully created contact:\n"
            response += f"Name: {person.get('name', 'Unknown')}\n"
            response += f"ID: {person.get('id', 'Unknown')}\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "create_event":
            result = await client.create_event(arguments)
            event = result.get("event", {})
            
            response = f"Successfully created event:\n"
            response += f"Type: {event.get('type', 'Unknown')}\n"
            response += f"ID: {event.get('id', 'Unknown')}\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "update_person":
            update_data = {k: v for k, v in arguments.items() if k != "person_id"}
            result = await client.update_person(arguments["person_id"], update_data)
            
            response = f"Successfully updated contact ID: {arguments['person_id']}\n"
            if "person" in result:
                person = result["person"]
                response += f"Name: {person.get('name', 'Unknown')}\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "delete_person":
            await client.delete_person(arguments["person_id"])
            
            response = f"Successfully deleted contact with ID: {arguments['person_id']}"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "list_notes":
            result = await client.list_notes(**arguments)
            notes = result.get("notes", [])
            
            if not notes:
                return [types.TextContent(type="text", text="No notes found")]
            
            response = f"Found {len(notes)} note(s):\n\n"
            for note in notes:
                body = note.get("body", "No content")[:100]
                if len(note.get("body", "")) > 100:
                    body += "..."
                person_name = note.get("person", {}).get("name", "Unknown")
                response += f"• Note ID: {note.get('id', 'Unknown')}\n"
                response += f"  Person: {person_name}\n"
                response += f"  Content: {body}\n\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "get_note":
            result = await client.get_note(arguments["note_id"])
            note = result.get("note", {})
            
            response = f"Note Details:\n"
            response += f"ID: {note.get('id', 'Unknown')}\n"
            response += f"Person: {note.get('person', {}).get('name', 'Unknown')}\n"
            response += f"Content:\n{note.get('body', 'No content')}\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "create_note":
            data = {
                "personId": arguments["person_id"],
                "body": arguments["body"],
                "isHtml": arguments.get("is_html", False)
            }
            result = await client.create_note(data)
            note = result.get("note", {})
            
            response = f"Successfully created note:\n"
            response += f"ID: {note.get('id', 'Unknown')}\n"
            response += f"Person ID: {arguments['person_id']}\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "list_tasks":
            result = await client.list_tasks(**arguments)
            tasks = result.get("tasks", [])
            
            if not tasks:
                return [types.TextContent(type="text", text="No tasks found")]
            
            response = f"Found {len(tasks)} task(s):\n\n"
            for task in tasks:
                desc = task.get("description", "No description")
                status = "✓" if task.get("completed") else "○"
                due_date = task.get("dueDate", "No due date")
                response += f"{status} {desc}\n"
                response += f"  ID: {task.get('id', 'Unknown')}\n"
                response += f"  Due: {due_date}\n\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "create_task":
            data = {
                "description": arguments["description"],
                "personId": arguments.get("person_id"),
                "dueDate": arguments.get("due_date"),
                "assignedTo": arguments.get("assigned_to")
            }
            result = await client.create_task(data)
            task = result.get("task", {})
            
            response = f"Successfully created task:\n"
            response += f"Description: {task.get('description', 'Unknown')}\n"
            response += f"ID: {task.get('id', 'Unknown')}\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "update_task":
            result = await client.update_task(arguments["task_id"], arguments)
            task = result.get("task", {})
            
            response = f"Successfully updated task:\n"
            response += f"Description: {task.get('description', 'Unknown')}\n"
            response += f"ID: {task.get('id', 'Unknown')}\n"
            response += f"Completed: {'Yes' if task.get('completed') else 'No'}\n"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "create_call":
            data = {
                "personId": arguments["person_id"],
                "outcome": arguments.get("outcome"),
                "note": arguments.get("note"),
                "duration": arguments.get("duration"),
                "callTime": arguments.get("call_time")
            }
            result = await client.create_call(data)
            call = result.get("call", {})
            
            response = f"Successfully logged call:\n"
            response += f"ID: {call.get('id', 'Unknown')}\n"
            response += f"Person ID: {arguments['person_id']}\n"
            if arguments.get("outcome"):
                response += f"Outcome: {arguments['outcome']}\n"
            
            return [types.TextContent(type="text", text=response)]
        
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except ValueError as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    except Exception as e:
        logger.error(f"Unexpected error in {name}: {e}")
        return [types.TextContent(type="text", text="An unexpected error occurred")]
    finally:
        await client.close()

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())