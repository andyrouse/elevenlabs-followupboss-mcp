#!/bin/bash

# Start ElevenLabs Webhook Server for FollowUp Boss Integration

echo "Starting ElevenLabs Webhook Server..."

# Export the FollowUp Boss API key
export FOLLOWUP_BOSS_API_KEY="sk_live_4d923a31_DMJcrnAWdBS3xBhRLKHNdztT"

# Export the ElevenLabs webhook secret for HMAC verification
export ELEVENLABS_WEBHOOK_SECRET="wsec_9b91cbd8e397a600a199d0c785eea8a5e12174050165d08e6341ab66995b93bf"

# Start the webhook server
python3 webhook_server.py