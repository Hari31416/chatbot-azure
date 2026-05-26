targetScope = 'subscription'

@description('Environment name (dev, staging, prod)')
param environmentName string

@description('Primary Azure region for all resources')
param location string

@description('Unique resource token for naming')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

// ──────────────────────────────────────────────
// Resource Group
// ──────────────────────────────────────────────
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'rg-chatbot-${environmentName}'
  location: location
  tags: {
    'azd-env-name': environmentName
    project: 'chatbot-azure'
  }
}

// ──────────────────────────────────────────────
// Storage Module (Phase 2)
// ──────────────────────────────────────────────
module storage './modules/storage.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    location: location
    environmentName: environmentName
    resourceToken: resourceToken
  }
}

// ──────────────────────────────────────────────
// Cosmos DB Module (Phase 3)
// ──────────────────────────────────────────────
module cosmos './modules/cosmos.bicep' = {
  name: 'cosmos'
  scope: rg
  params: {
    location: location
    environmentName: environmentName
  }
}

output AZURE_STORAGE_ACCOUNT_NAME string = storage.outputs.storageAccountName
output COSMOS_ENDPOINT string = cosmos.outputs.cosmosEndpoint
output COSMOS_DATABASE_NAME string = cosmos.outputs.cosmosDatabaseName
