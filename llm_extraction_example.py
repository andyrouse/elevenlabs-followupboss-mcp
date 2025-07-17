#!/usr/bin/env python3
"""
Example of how to add LLM-based data extraction to the webhook
This would replace the regex patterns with smarter AI extraction
"""
import openai
import json
from typing import Dict, Any, List

async def extract_caller_info_with_llm(transcript: List[Dict], api_key: str) -> Dict[str, str]:
    """Use OpenAI to extract caller information from transcript"""
    
    # Format transcript for LLM
    conversation = ""
    for entry in transcript[:5]:  # First 5 messages
        role = entry.get("role", "unknown")
        message = entry.get("message", "")
        conversation += f"{role.upper()}: {message}\n"
    
    # Structured prompt for extraction
    prompt = f"""
Analyze this phone conversation transcript and extract the following information:

CONVERSATION:
{conversation}

Extract these fields and return ONLY a JSON object:
{{
    "caller_name": "First and last name if mentioned, or null",
    "caller_phone": "Phone number if mentioned, or null", 
    "source": "One of: Texting, Cold Email, Standard mailer, Google, ElevenLabs AI Call",
    "property_county": "County mentioned, or null",
    "property_state": "State mentioned, or null",
    "acreage": "Amount of acreage mentioned, or null"
}}

Rules:
- Only extract explicitly mentioned information
- For source: if they mention "text", use "Texting"; if "email", use "Cold Email"; if "ad/mailer", use "Standard mailer"; if "website/google", use "Google"; otherwise use "ElevenLabs AI Call"
- Return valid JSON only, no other text
"""

    try:
        client = openai.AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Cheap and fast
            messages=[{"role": "user", "content": prompt}],
            temperature=0,  # Deterministic
            max_tokens=200
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        # Fallback to current regex extraction
        print(f"LLM extraction failed: {e}")
        return {}

# Cost estimate: ~$0.001 per call (very cheap)