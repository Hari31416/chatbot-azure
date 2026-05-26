# Azure Deployment & Authentication Setup Guide

This guide provides a comprehensive, step-by-step walk-through to provision the Azure infrastructure, configure Microsoft Entra ID (Active Directory) authentication, create test users, store gateway API secrets, and deploy the decoupled FastAPI backend and React frontend.

---

## 📋 Prerequisites

Before starting the deployment, make sure you have installed and configured the following tools locally:

1. **Azure CLI**: Run `az login` to authenticate with your active Azure Subscription.
2. **Docker**: Running locally to allow packaging the FastAPI backend containers.
3. **Python & uv**: For backend local testing and packaging.
4. **Node.js & pnpm**: For building and bundling the frontend React assets.

---

## 🛠️ Step 1: Authenticate with Azure

Open your terminal and authenticate the Azure CLI using one of the following methods, depending on your development environment:

### Method A: Interactive Web Browser (Default for local machines)
Run the following command. It will automatically open your default browser to prompt for your credentials:
```bash
az login
```

### Method B: Device Code Login (For headless hosts, cloud-shells, WSL, or SSH sessions)
If you are working on a remote machine where a GUI browser cannot open automatically, use the device code flow:
```bash
az login --use-device-code
```
*This will output a one-time code (e.g., `WD32E54F3`) and request you to open `https://microsoft.com/devicelogin` on any internet-connected browser (like your phone or desktop) to complete authentication.*

### Method C: Service Principal Secret (For CI/CD runners like GitHub Actions)
If you are automating deployments programmatically, authenticate using a Service Principal:
```bash
az login --service-principal \
  -u "<app-id-or-sp-name>" \
  -p "<service-principal-client-secret>" \
  --tenant "<your-tenant-id>"
```

---

### Step 1.2: Select and Set Active Subscription
Once authenticated, list your active billing scopes and set the target subscription ID:
```bash
# List all subscriptions in a readable table format
az account list --output table

# Set the active subscription context
az account set --subscription "<your-subscription-id>"
```

---

## 🏗️ Step 2: Deploy Core Infrastructure (Bicep)

The main Bicep script handles resource group provisioning, network isolation, role assignments, database containers, and computing environments.

Deploy the infrastructure using the unified `Makefile`:

```bash
# Deploys main.bicep to your subscription
# You can customize these defaults in the Makefile or override them at invocation:
# e.g., make deploy-infra AZURE_ENV_NAME=prod AZURE_LOCATION=westeurope
make deploy-infra
```

### What this provisions:
* **Resource Group**: `rg-chatbot-dev`
* **Log Analytics Workspace & Application Insights**: Custom telemetry ingestion environment
* **Azure Storage Account**: Private file uploads containers (`uploads`), queues (`ingestion-queue`), and storage tables
* **Azure Cosmos DB NoSQL Account**: Storage database and vector indexing containers (`conversations`, `vectors`)
* **Azure Container Registry (ACR)**: Secure host for backend Docker builds
* **Azure Container Apps Environment & Container App**: High-performance FastAPI compute engine (scales down to 0 instances when idle)
* **Azure Static Web Apps (SWA)**: Global CDN host for React client assets
* **Azure Key Vault**: Highly secure KMS store for LiteLLM gateway credentials

### Extract Deployment Keys and Endpoints:
After Bicep completes, extract key outputs to use in the subsequent steps:
```bash
# Get the backend API URL
az deployment sub show \
  --name "rg-chatbot-dev-deployment" \
  --query "properties.outputs.BACKEN_URL.value"

# Get the Static Web App deployment token
az deployment sub show \
  --name "rg-chatbot-dev-deployment" \
  --query "properties.outputs.AZURE_SWA_DEPLOYMENT_TOKEN.value"
```

---

## 🔐 Step 3: Configure Microsoft Entra ID Authentication

Microsoft Entra ID (formerly Azure Active Directory) serves as the secure Identity Provider for this chatbot platform.

### A. Create an App Registration
1. Sign in to the [Azure Portal](https://portal.azure.com/).
2. Navigate to **Microsoft Entra ID** $\rightarrow$ **App registrations** $\rightarrow$ **New registration**.
3. Set the following options:
   * **Name**: `chatbot-auth`
   * **Supported account types**: "Accounts in this organizational directory only (Single tenant)"
   * **Redirect URI**: 
     * Select **Single-page application (SPA)**.
     * Enter: `http://localhost:3000` (for local React development) and your deployed Static Web App URL (extracted in Step 2).
4. Click **Register**.

### B. Extract App Registration IDs
After registration, copy the following values from the registration dashboard's **Overview** panel:
* **Application (client) ID**: *This is your Client ID* (e.g., `VITE_AZURE_CLIENT_ID` / `AZURE_CLIENT_ID`).
* **Directory (tenant) ID**: *This is your Tenant ID* (e.g., `AZURE_TENANT_ID`).
* **Authority Endpoint**: Format as `https://login.microsoftonline.com/<tenant-id>` (e.g., `VITE_ENTRA_AUTHORITY` / `ENTRA_AUTHORITY`).

### C. Configure User Flows and API Permissions
Ensure users can authenticate. Under **API permissions**:
1. Click **Add a permission** $\rightarrow$ **Microsoft Graph** $\rightarrow$ **Delegated permissions**.
2. Make sure `User.Read` is selected (this allows retrieving the logged-in user's email).
3. Click **Add permissions**.

---

## 👥 Step 4: Create Authorized Test Users

Since this is a Single Tenant enterprise directory app, you must register users inside your directory tenant to allow them to log in.

1. In the **Microsoft Entra ID** portal, navigate to **Users** $\rightarrow$ **All users** $\rightarrow$ **New user** $\rightarrow$ **Create new user**.
2. Fill in the user profile parameters:
   * **User principal name (username)**: `testuser@yourdomain.onmicrosoft.com`
   * **Display name**: `Test User`
   * **Password**: Select "Auto-generate password" or write a secure temporary one.
3. Click **Create**.
4. *(Optional)* Login once with this user on [myapps.microsoft.com](https://myapps.microsoft.com) to accept the directory's default terms and reset the temporary password if prompted.

---

## 🔑 Step 5: Store Secrets in Key Vault

The FastAPI application uses system-assigned managed identity to fetch runtime secrets. You must populate the LiteLLM gateway credentials inside the Key Vault.

Run the following commands using the Azure CLI:

```bash
# 1. Store your primary model API key
az keyvault secret set \
  --vault-name "kv-chatbot-dev" \
  --name "litellm-api-key" \
  --value "<your-api-key>"

# 2. Store your vision model API key
az keyvault secret set \
  --vault-name "kv-chatbot-dev" \
  --name "litellm-vision-api-key" \
  --value "<your-api-key>"
```

---

## 🚀 Step 6: Deploy the Backend API (Container Apps)

Build and package the Python FastAPI application using Azure Container Registry (ACR) and update the Container App:

```bash
# 1. Run local test suite to verify code sanity
cd backend
uv run pytest

# 2. Execute ACR remote build and Container App update via Makefile
cd ..
make deploy-backend
```

---

## 💻 Step 7: Deploy the Frontend Client (Static Web Apps)

Configure your React environment variables to link with Microsoft Entra ID and the deployed backend API:

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Create your environment configuration file (`.env`):
   ```bash
   cp .env.example .env
   ```
3. Populate the Entra ID variables you extracted in Step 3:
   ```env
   VITE_API_BASE_URL=https://chatbot-backend.dev-api.azurecontainerapps.io
   VITE_AZURE_CLIENT_ID=xxxxxx-xxxx-xxxx-xxxx-xxxxxxxxx
   VITE_ENTRA_AUTHORITY=https://login.microsoftonline.com/your-tenant-id
   ```
4. Build the application and upload it to Azure Static Web Apps:
   ```bash
   cd ..
   # Make sure AZURE_SWA_DEPLOYMENT_TOKEN is exported or loaded in your shell:
   export AZURE_SWA_DEPLOYMENT_TOKEN="<your-extracted-token>"
   make deploy-frontend
   ```

---

## 🧪 Step 8: End-to-End Verification

Now that the entire stack is successfully deployed, verify the live environment:

1. Navigate to your deployed Frontend URL (e.g. `https://swa-chatbot-dev.azurestaticapps.net`).
2. You will be redirected to the Microsoft login page. Sign in with the **Test User** credentials you created in Step 4.
3. Once authenticated, you will be redirected back to the beautiful chat dashboard.
4. Try typing a message: "Explain the benefit of Azure Container Apps."
5. Test the **RAG Document Catalog**: Upload a sample PDF or text file. Watch the system transition the status from `processing` to `ready`, and then ask questions using context-enhanced knowledge!
