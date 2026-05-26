#!/bin/bash
set -euo pipefail

FUNC_NAME="${AZURE_FUNCTION_APP_NAME:-func-chatbot-worker-${AZURE_ENV_NAME:-dev}}"

if ! command -v func >/dev/null 2>&1; then
  echo "❌ Azure Functions Core Tools not found."
  echo "   Install:"
  echo "     brew tap azure/functions"
  echo "     brew install azure-functions-core-tools@4"
  exit 1
fi

echo "📦 Publishing ingestion worker to $FUNC_NAME..."
cd backend
func azure functionapp publish "$FUNC_NAME" --python

echo "🎉 Function App deployment complete!"
