param location string
param environmentName string
param resourceToken string

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stchatbot${resourceToken}'
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  tags: { 'azd-env-name': environmentName }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource uploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'uploads'
  properties: { publicAccess: 'None' }
}

resource stagingContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'staging'
  properties: { publicAccess: 'None' }
}

resource ragTempContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'rag-temp'
  properties: { publicAccess: 'None' }
}

// Lifecycle management: auto-delete blobs after 7 days in staging and rag-temp
resource lifecyclePolicy 'Microsoft.Storage/storageAccounts/managementPolicies@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    policy: {
      rules: [
        {
          name: 'expire-staging-uploads'
          type: 'Lifecycle'
          definition: {
            actions: {
              baseBlob: { delete: { daysAfterModificationGreaterThan: 7 } }
            }
            filters: {
              blobTypes: ['blockBlob']
              prefixMatch: ['staging/', 'rag-temp/']
            }
          }
        }
      ]
    }
  }
}

output storageAccountName string = storageAccount.name
output storageAccountId string = storageAccount.id
