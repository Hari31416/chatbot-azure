AZURE_ENV_NAME ?= dev
AZURE_LOCATION ?= centralindia

export AZURE_ENV_NAME
export AZURE_LOCATION

# Load environment variables from .env if it exists
ifneq ("$(wildcard .env)","")
  include .env
  export
endif

.PHONY: deploy-infra deploy-backend deploy-functions deploy-frontend deploy-all

deploy-infra:
	@echo "🚀 Provisioning Azure Infrastructure via Bicep..."
	az deployment sub create \
	  --location $(AZURE_LOCATION) \
	  --template-file infra/main.bicep \
	  --parameters environmentName=$(AZURE_ENV_NAME) location=$(AZURE_LOCATION) \
	               liteLlmApiKey="$(LITELLM_API_KEY)" liteLlmVisionApiKey="$(LITELLM_VISION_API_KEY)"

deploy-backend:
	@echo "🚀 Building backend container and deploying to Azure Container Apps..."
	./deploy-backend.sh

deploy-functions:
	@echo "🚀 Deploying background queue worker to Azure Functions..."
	./deploy-functions.sh

deploy-frontend:
	@echo "🚀 Compiling React frontend and deploying to Azure Static Web Apps..."
	./deploy-frontend.sh

deploy-all: deploy-infra deploy-backend deploy-functions deploy-frontend
	@echo "🎉 Full Azure stack deployment complete!"

show-outputs:
	@./get-outputs.sh

