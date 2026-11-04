#!/usr/bin/env bash
# Gemini Flash example (safe version)
# Never hardcode your API key. Set it as an environment variable:
#   export GEMINI_API_KEY="your-key-here"
#
# IMPORTANT: The key shared in chat is compromised. Rotate it immediately
# in Google AI Studio / Cloud Console before using this.

set -euo pipefail

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "Error: GEMINI_API_KEY environment variable is not set."
  echo "Export it first, then re-run this script."
  exit 1
fi

curl -sS "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent" \
  -H "Content-Type: application/json" \
  -H "X-goog-api-key: ${GEMINI_API_KEY}" \
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "Explain how AI works in a few words"
          }
        ]
      }
    ]
  }' | jq .
