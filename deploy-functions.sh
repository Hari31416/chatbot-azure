#!/bin/bash
set -euo pipefail

# Load environment variables from .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

FUNCTION_APP_NAME="${AZURE_FUNCTION_APP_NAME:-}"

if [ -z "$FUNCTION_APP_NAME" ]; then
  echo "🔍 Fetching Azure Function App name from deployment outputs..."
  FUNCTION_APP_NAME=$(az deployment sub show --name main --query "properties.outputs.azure_function_app_name.value" -o tsv 2>/dev/null || true)
fi

if [ -z "$FUNCTION_APP_NAME" ] || [ "$FUNCTION_APP_NAME" == "null" ]; then
  echo "❌ Error: Could not find Azure Function App Name. Please run 'make deploy-infra' first."
  exit 1
fi

echo "🚀 Deploying Python Function App to $FUNCTION_APP_NAME..."
cd backend

# Deploy utilizing the Azure Functions Core Tools
func azure functionapp publish "$FUNCTION_APP_NAME" --python

echo "🎉 Function App deployment complete!"
