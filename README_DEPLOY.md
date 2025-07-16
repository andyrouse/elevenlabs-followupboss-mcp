# ElevenLabs FollowUp Boss MCP Integration

Secure MCP (Model Context Protocol) server that integrates ElevenLabs AI calling with FollowUp Boss CRM.

## Features

- ✅ **Secure Authentication** - Token-based auth with rate limiting
- ✅ **Auto Contact Creation** - Creates contacts from AI call data  
- ✅ **Call Logging** - Logs full transcripts and call details
- ✅ **Input Validation** - Sanitizes all user inputs
- ✅ **Production Ready** - CORS, error handling, monitoring

## Quick Deploy to Railway

1. **Fork this repository** to your GitHub account

2. **Deploy to Railway:**
   - Go to [railway.app](https://railway.app) 
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your forked repository

3. **Set Environment Variables** in Railway dashboard:
   ```
   FOLLOWUP_BOSS_API_KEY=your_api_key_here
   MCP_AUTH_TOKEN=your_secure_random_token
   PORT=8000
   ```

4. **Configure ElevenLabs:**
   - Server Type: SSE
   - Server URL: `https://your-app.railway.app/sse`
   - Secret Token: Use your `MCP_AUTH_TOKEN`

## Local Development

```bash
# Install dependencies
pip install -r requirements-secure.txt

# Set environment variables
cp .env.example .env
# Edit .env with your keys

# Run server
python secure_elevenlabs_mcp.py
```

## Security Features

- Authentication tokens
- Rate limiting (20 requests/minute)
- Input sanitization 
- CORS restrictions
- No sensitive data logging
- Webhook signature verification

## Available Tools

### `log_call`
Logs completed AI calls to FollowUp Boss CRM
- Creates contact if doesn't exist
- Logs call transcript and details
- Validates phone numbers and names

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FOLLOWUP_BOSS_API_KEY` | Yes | Your FollowUp Boss API key |
| `MCP_AUTH_TOKEN` | Yes | Secure random token for auth |
| `ELEVENLABS_WEBHOOK_SECRET` | No | Optional webhook signature verification |
| `PORT` | No | Server port (default: 8000) |

## Support

For issues or questions, check the deployment logs in Railway dashboard.