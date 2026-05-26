AZURE_ENV_NAME ?= dev
AZURE_LOCATION ?= eastus

export AZURE_ENV_NAME
export AZURE_LOCATION

.PHONY: deploy-infra deploy-backend deploy-frontend deploy-all

deploy-infra:
	@echo "🚀 Provisioning Azure Infrastructure via Bicep..."
	az deployment sub create \
	  --location $(AZURE_LOCATION) \
	  --template-file infra/main.bicep \
	  --parameters environmentName=$(AZURE_ENV_NAME) location=$(AZURE_LOCATION)

deploy-backend:
	@echo "🚀 Building backend container and deploying to Azure Container Apps..."
	./deploy-backend.sh

deploy-frontend:
	@echo "🚀 Compiling React frontend and deploying to Azure Static Web Apps..."
	./deploy-frontend.sh

deploy-all: deploy-infra deploy-backend deploy-frontend
	@echo "🎉 Full Azure stack deployment complete!"
