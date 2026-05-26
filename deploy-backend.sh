#!/bin/bash
set -euo pipefail

REGISTRY="${AZURE_CONTAINER_REGISTRY:-crchatbotdev}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "🔐 Logging in to Azure Container Registry ($REGISTRY)..."
az acr login --name "$REGISTRY"

echo "🐳 Building container image locally via Docker for linux/amd64 platform..."
# --platform linux/amd64 is required since we are on macOS but Azure Container Apps runs on Intel/AMD hosts
docker build --platform linux/amd64 -t "$REGISTRY.azurecr.io/chatbot-backend:$IMAGE_TAG" ./backend

echo "🚀 Pushing image to ACR..."
docker push "$REGISTRY.azurecr.io/chatbot-backend:$IMAGE_TAG"

echo "🔄 Updating Container App..."
az containerapp update \
  --name chatbot-backend \
  --resource-group "rg-chatbot-${AZURE_ENV_NAME:-dev}" \
  --image "$REGISTRY.azurecr.io/chatbot-backend:$IMAGE_TAG"

echo "🎉 Deployment complete!"

