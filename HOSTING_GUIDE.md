# FollowUp Boss MCP Server Hosting Guide

## Hosting Options

### 1. Local Development (Simplest)
Run directly on your machine:
```bash
export FOLLOWUP_BOSS_API_KEY="your_api_key"
python3 fubmcp.py
```
- ✅ Easy setup
- ✅ Good for testing
- ❌ Only accessible locally
- ❌ Stops when computer sleeps

### 2. Local Background Service (Recommended for Personal Use)
Run as a system service:

**macOS (launchd)**:
```xml
<!-- ~/Library/LaunchAgents/com.fubmcp.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fubmcp</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/fubmcp.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>FOLLOWUP_BOSS_API_KEY</key>
        <string>your_api_key</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

**Linux (systemd)**:
```ini
# /etc/systemd/system/fubmcp.service
[Unit]
Description=FollowUp Boss MCP Server
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/fubmcp
Environment="FOLLOWUP_BOSS_API_KEY=your_api_key"
ExecStart=/usr/bin/python3 /path/to/fubmcp.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 3. Docker Container (Recommended for Teams)
Create a Dockerfile:
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY fubmcp.py .
CMD ["python", "fubmcp.py"]
```

Run with:
```bash
docker build -t fubmcp .
docker run -d --name fubmcp \
  -e FOLLOWUP_BOSS_API_KEY="your_api_key" \
  --restart unless-stopped \
  fubmcp
```

### 4. Cloud Hosting (For Remote Access)

**Option A: VPS with SSH Tunnel**
1. Deploy to a VPS (DigitalOcean, Linode, etc.)
2. Use SSH tunnel for secure access:
```bash
ssh -L 5000:localhost:5000 user@your-vps.com
```

**Option B: Private Cloud (AWS/GCP/Azure)**
- Deploy as a container service
- Use VPN or private networking
- Never expose MCP directly to internet

### 5. Team Deployment (Project Scope)
Create `.mcp.json` in project root:
```json
{
  "servers": {
    "fubmcp": {
      "command": "python3",
      "args": ["fubmcp.py"],
      "env": {
        "FOLLOWUP_BOSS_API_KEY": "${FOLLOWUP_BOSS_API_KEY}"
      }
    }
  }
}
```

## Security Best Practices

### 1. API Key Management
- **Never** hardcode API keys
- Use environment variables
- Consider using secret managers:
  - macOS: Keychain
  - Linux: `pass` or `secret-tool`
  - Cloud: AWS Secrets Manager, etc.

### 2. Network Security
- **Never** expose MCP server directly to internet
- Use VPN or SSH tunnels for remote access
- Implement firewall rules
- Use HTTPS/TLS for any remote connections

### 3. Access Control
- Run with minimal privileges
- Use dedicated service accounts
- Implement logging and monitoring
- Regular security audits

## Recommended Setup by Use Case

### Personal Use
1. Local background service
2. API key in keychain/secret manager
3. Regular backups of configuration

### Small Team
1. Docker container on shared server
2. VPN access to server
3. Shared API key management
4. `.mcp.json` in project repo

### Enterprise
1. Container orchestration (Kubernetes)
2. Secret management service
3. Zero-trust networking
4. Comprehensive logging/monitoring

## Configuration Management

### Environment Variables
```bash
# .env file (DO NOT commit to git)
FOLLOWUP_BOSS_API_KEY=your_api_key
MCP_LOG_LEVEL=INFO
MCP_MAX_CONNECTIONS=10
```

### Claude Code Integration
```bash
# Add server to Claude Code
claude mcp add fubmcp /path/to/fubmcp.py

# For remote server (NOT recommended)
claude mcp add --transport sse fubmcp https://internal.server/mcp
```

## Monitoring & Maintenance

### Health Checks
Add a health endpoint to your server:
```python
@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    # Add health check tool
    tools.append(Tool(
        name="health_check",
        description="Check server health",
        inputSchema={"type": "object"}
    ))
```

### Logging
- Log all API interactions
- Monitor error rates
- Set up alerts for failures

### Updates
- Regular dependency updates
- API compatibility monitoring
- Backup before updates

## Quick Start Commands

```bash
# Local development
export FOLLOWUP_BOSS_API_KEY="your_key"
python3 fubmcp.py

# Docker deployment
docker-compose up -d

# Add to Claude Code
claude mcp add fubmcp ./fubmcp.py
```

## Important Notes

1. **MCP is designed for local/private use** - Not for public internet
2. **Protect your API keys** - They have full account access
3. **Monitor usage** - Watch for rate limits
4. **Test thoroughly** - Before production deployment
5. **Keep it simple** - Start local, scale as needed