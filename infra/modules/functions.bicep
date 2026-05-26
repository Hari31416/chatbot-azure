param location string
param environmentName string
param storageAccountConnectionString string

resource hostingPlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: 'asp-chatbot-worker-${environmentName}'
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true // Required for Linux
  }
}

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: 'func-chatbot-worker-${environmentName}'
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: hostingPlan.id
    siteConfig: {
      linuxFxVersion: 'Python|3.12'
      appSettings: [
        { name: 'AzureWebJobsStorage', value: storageAccountConnectionString }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING', value: storageAccountConnectionString }
        { name: 'WEBSITE_CONTENTSHARE', value: 'func-chatbot-worker-${environmentName}-share' }
      ]
    }
    reserved: true // Required for Linux
  }
}

output functionAppPrincipalId string = functionApp.identity.principalId
output functionAppName string = functionApp.name
