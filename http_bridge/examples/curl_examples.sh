#!/bin/bash
# SpireComm HTTP Bridge - Example curl commands

# Health check
echo "=== Health Check ==="
curl http://localhost:8080/health | jq .

# Get current game state
echo -e "\n=== Get State ==="
curl http://localhost:8080/state | jq .

# Send action: end turn
echo -e "\n=== Send Action: End Turn ==="
curl -X POST http://localhost:8080/action \
  -H "Content-Type: application/json" \
  -d '{"command": "end"}' | jq .

# Send action: play card 1 (no target)
echo -e "\n=== Send Action: Play Card 1 ==="
curl -X POST http://localhost:8080/action \
  -H "Content-Type: application/json" \
  -d '{"command": "play 1"}' | jq .

# Send action: play card 2 targeting monster 0
echo -e "\n=== Send Action: Play Card 2 -> Monster 0 ==="
curl -X POST http://localhost:8080/action \
  -H "Content-Type: application/json" \
  -d '{"command": "play 2 0"}' | jq .

# Send action: choose option 0
echo -e "\n=== Send Action: Choose Option 0 ==="
curl -X POST http://localhost:8080/action \
  -H "Content-Type: application/json" \
  -d '{"command": "choose 0"}' | jq .

# Send action: proceed
echo -e "\n=== Send Action: Proceed ==="
curl -X POST http://localhost:8080/action \
  -H "Content-Type: application/json" \
  -d '{"command": "proceed"}' | jq .

# Send action: use potion 0
echo -e "\n=== Send Action: Use Potion 0 ==="
curl -X POST http://localhost:8080/action \
  -H "Content-Type: application/json" \
  -d '{"command": "potion use 0"}' | jq .

# Manual ready handshake (alternative to auto-handshake)
echo -e "\n=== Manual Ready Handshake ==="
curl http://localhost:8080/ready | jq .
