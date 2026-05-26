#!/bin/bash
set -euo pipefail

REGISTRY="${AZURE_CONTAINER_REGISTRY:-crchatbotdev}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "Building and pushing to ACR..."
az acr build --registry "$REGISTRY" --image "chatbot-backend:$IMAGE_TAG" ./backend

echo "Updating Container App..."
az containerapp update \
  --name chatbot-backend \
  --resource-group "rg-chatbot-${AZURE_ENV_NAME:-dev}" \
  --image "$REGISTRY.azurecr.io/chatbot-backend:$IMAGE_TAG"

echo "Deployment complete!"
