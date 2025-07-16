#!/usr/bin/env python3
"""
Prompt injection protection for ElevenLabs MCP server
Detects and blocks malicious prompts in user inputs
"""
import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger("prompt_security")

@dataclass
class SecurityThreat:
    severity: str  # "high", "medium", "low"
    threat_type: str
    description: str
    matched_text: str

class PromptInjectionDetector:
    """Detects prompt injection attempts in user inputs"""
    
    def __init__(self):
        # High-risk patterns that indicate prompt injection
        self.high_risk_patterns = [
            # Direct prompt injection attempts
            r"(?i)(ignore|forget|disregard).{0,50}(previous|above|prior|earlier).{0,50}(instruction|prompt|rule|command)",
            r"(?i)(system|assistant|ai|bot).{0,20}(now|please|must|should).{0,20}(ignore|forget|respond|answer)",
            r"(?i)act\s+as\s+(a\s+)?(different|new|another|other)",
            r"(?i)(you\s+are|you're)\s+(now|actually|really)\s+(a|an)",
            r"(?i)(new|different|updated|changed)\s+(instructions|rules|guidelines|prompt)",
            
            # Role manipulation
            r"(?i)(assume|pretend|roleplay|act\s+like|behave\s+as)\s+(you\s+are|you're)",
            r"(?i)(developer|admin|root|system)\s+(mode|access|override|bypass)",
            r"(?i)(jailbreak|break\s+out|escape|override|bypass)",
            
            # System prompt attempts
            r"(?i)(show|reveal|display|tell\s+me)\s+(your|the)\s+(prompt|instructions|rules|guidelines)",
            r"(?i)(what\s+are|show\s+me)\s+(your|the)\s+(original|initial|system)\s+(prompt|instructions)",
            r"(?i)print\s*\(\s*[\"'].*system.*[\"']\s*\)",
            
            # Code injection attempts
            r"(?i)(execute|run|eval|import|subprocess|os\.system)",
            r"(?i)(__|\$\{|<%|<\?|{{)",
            r"(?i)(script|javascript|python|bash|shell|cmd)",
            
            # Data exfiltration attempts
            r"(?i)(api\s+key|secret|token|password|credential)",
            r"(?i)(database|sql|query|select|insert|update|delete)",
            r"(?i)(file|directory|path|folder|read|write|access)",
        ]
        
        # Medium-risk patterns
        self.medium_risk_patterns = [
            # Suspicious instruction patterns
            r"(?i)(please|now|must|should)\s+(ignore|skip|bypass|override)",
            r"(?i)(instead|but|however|actually|really)\s+(ignore|disregard|forget)",
            r"(?i)(tell|show|give)\s+me\s+(everything|all|any)",
            r"(?i)(hypothetical|imagine|suppose|what\s+if)\s+(you|I|we)\s+(could|can|were)",
            
            # Suspicious formatting
            r"[\[\]{}()<>].*[\[\]{}()<>]",  # Multiple brackets/braces
            r"[\"'`]{3,}",  # Triple quotes
            r"[A-Z]{5,}",  # Excessive capitals
            
            # Suspicious keywords
            r"(?i)(admin|root|sudo|privilege|escalate|elevate)",
            r"(?i)(hack|crack|exploit|vulnerability|inject)",
            r"(?i)(malware|virus|trojan|backdoor|payload)",
        ]
        
        # Low-risk patterns (suspicious but might be legitimate)
        self.low_risk_patterns = [
            r"(?i)(test|testing|debug|debugging)",
            r"(?i)(example|sample|demo|demonstration)",
            r"(?i)(help|assist|support|guidance)",
        ]
    
    def analyze_input(self, text: str, context: str = "") -> List[SecurityThreat]:
        """Analyze input for security threats"""
        if not text or not isinstance(text, str):
            return []
        
        threats = []
        
        # Check high-risk patterns
        for pattern in self.high_risk_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                threats.append(SecurityThreat(
                    severity="high",
                    threat_type="prompt_injection",
                    description=f"Potential prompt injection detected in {context}",
                    matched_text=match.group()
                ))
        
        # Check medium-risk patterns
        for pattern in self.medium_risk_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                threats.append(SecurityThreat(
                    severity="medium",
                    threat_type="suspicious_content",
                    description=f"Suspicious content detected in {context}",
                    matched_text=match.group()
                ))
        
        # Check low-risk patterns
        for pattern in self.low_risk_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                threats.append(SecurityThreat(
                    severity="low",
                    threat_type="potentially_suspicious",
                    description=f"Potentially suspicious content in {context}",
                    matched_text=match.group()
                ))
        
        return threats
    
    def sanitize_input(self, text: str, max_length: int = 1000) -> str:
        """Sanitize input by removing dangerous patterns"""
        if not text or not isinstance(text, str):
            return ""
        
        # Remove potential injection attempts
        sanitized = text
        
        # Remove excessive whitespace and control characters
        sanitized = re.sub(r'\s+', ' ', sanitized)
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', sanitized)
        
        # Remove potential code injection patterns
        sanitized = re.sub(r'[<>{}()[\]`]', '', sanitized)
        
        # Remove excessive punctuation
        sanitized = re.sub(r'[!@#$%^&*]{3,}', '', sanitized)
        
        # Limit length
        sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    def is_safe_input(self, text: str, context: str = "") -> tuple[bool, List[SecurityThreat]]:
        """Check if input is safe to process"""
        threats = self.analyze_input(text, context)
        
        # Block if any high-risk threats found
        high_risk_threats = [t for t in threats if t.severity == "high"]
        if high_risk_threats:
            logger.warning(f"High-risk prompt injection blocked in {context}: {[t.matched_text for t in high_risk_threats]}")
            return False, threats
        
        # Warn about medium-risk threats but allow
        medium_risk_threats = [t for t in threats if t.severity == "medium"]
        if medium_risk_threats:
            logger.warning(f"Medium-risk content detected in {context}: {[t.matched_text for t in medium_risk_threats]}")
        
        return True, threats

# Global detector instance
detector = PromptInjectionDetector()

def validate_call_data(call_data: Dict[str, Any]) -> tuple[bool, str, Dict[str, Any]]:
    """Validate call data for security threats"""
    sanitized_data = {}
    
    # Check caller name
    caller_name = call_data.get("caller_name", "")
    is_safe, threats = detector.is_safe_input(caller_name, "caller_name")
    if not is_safe:
        return False, "Caller name contains suspicious content", {}
    sanitized_data["caller_name"] = detector.sanitize_input(caller_name, 100)
    
    # Check transcript
    transcript = call_data.get("transcript", "")
    is_safe, threats = detector.is_safe_input(transcript, "transcript")
    if not is_safe:
        return False, "Transcript contains potential prompt injection", {}
    sanitized_data["transcript"] = detector.sanitize_input(transcript, 5000)
    
    # Check call summary
    call_summary = call_data.get("call_summary", "")
    is_safe, threats = detector.is_safe_input(call_summary, "call_summary")
    if not is_safe:
        return False, "Call summary contains suspicious content", {}
    sanitized_data["call_summary"] = detector.sanitize_input(call_summary, 500)
    
    # Check call outcome
    call_outcome = call_data.get("call_outcome", "")
    is_safe, threats = detector.is_safe_input(call_outcome, "call_outcome")
    if not is_safe:
        return False, "Call outcome contains suspicious content", {}
    sanitized_data["call_outcome"] = detector.sanitize_input(call_outcome, 50)
    
    # Copy safe fields
    sanitized_data["caller_phone"] = call_data.get("caller_phone", "")
    sanitized_data["call_duration"] = call_data.get("call_duration", 0)
    
    return True, "Input validated successfully", sanitized_data