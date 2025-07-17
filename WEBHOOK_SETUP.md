# ElevenLabs Webhook Setup for FollowUp Boss Integration

## Overview
This guide explains how to set up post-call webhooks to automatically log ElevenLabs AI calls to FollowUp Boss CRM.

## Why Webhooks Instead of MCP?
- **MCP tools** are for real-time actions DURING conversations
- **Webhooks** are for post-call processing and are more reliable
- Webhooks are triggered automatically by ElevenLabs after every call

## Setup Steps

### 1. Deploy the Webhook Server

On your Railway instance, the webhook server should be running:

```bash
python webhook_server.py
```

### 2. Configure Environment Variables

Set these in your Railway dashboard:
- `FOLLOWUP_BOSS_API_KEY` - Your FollowUp Boss API key
- `ELEVENLABS_WEBHOOK_SECRET` - (Optional) Secret for webhook signature verification

### 3. Configure ElevenLabs

1. Log into your ElevenLabs dashboard
2. Go to your Conversational AI agent settings
3. Navigate to "Workflows" or "Post-call webhooks"
4. Enable "Post-call transcription webhook"
5. Set the webhook URL to:
   ```
   https://web-production-dfe01.up.railway.app/webhook/elevenlabs
   ```
6. If using webhook secret, add it in ElevenLabs settings
7. Save your changes

### 4. What Data is Logged

The webhook automatically extracts and logs:
- Caller name (parsed from conversation)
- Phone number (parsed from conversation)
- Full conversation transcript
- Call duration
- Call cost
- Agent ID
- Conversation ID
- AI-generated summary

### 5. Testing

1. Make a test call to your ElevenLabs agent
2. End the call
3. Within seconds, check:
   - Railway logs for webhook receipt
   - FollowUp Boss for the new contact/event

### 6. Troubleshooting

If calls aren't appearing in FollowUp Boss:

1. **Check Railway logs** for webhook requests
2. **Verify API key** is correct
3. **Test webhook manually** using curl:
   ```bash
   curl -X POST https://web-production-dfe01.up.railway.app/webhook/elevenlabs \
     -H "Content-Type: application/json" \
     -d '{
       "agent_id": "test",
       "conversation_id": "test-123",
       "transcript": {"messages": []},
       "metadata": {"duration": 60}
     }'
   ```
4. **Check ElevenLabs webhook settings** are saved and enabled

## Security Notes

- The webhook endpoint validates the FollowUp Boss API key
- Optional HMAC signature verification for webhook authenticity
- All data is sanitized before sending to FollowUp Boss