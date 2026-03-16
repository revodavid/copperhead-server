# Deploy the CopperHead game server to Azure Container Apps.
#
# Usage:
#   1. Review the configuration values in the section below.
#   2. Make sure a Dockerfile exists in this folder.
#   3. Run this script from PowerShell:
#      .\deploy-azure.ps1
#
# Notes:
#   - This script uses 'az acr build', so Docker does not need to be installed locally.
#   - server-settings.json is stored on an Azure File Share so you can edit it
#     from the Azure Portal (Storage Browser) without redeploying.
#   - The server log file is also written to the file share for easy access.

$ErrorActionPreference = "Stop"

# -------------------------------
# Configuration
# -------------------------------
$ResourceGroup   = if ($env:RESOURCE_GROUP)   { $env:RESOURCE_GROUP }   else { "copperhead-rg" }
$Location        = if ($env:LOCATION)         { $env:LOCATION }         else { "westus2" }
$AcrName         = if ($env:ACR_NAME)         { $env:ACR_NAME }         else { "copperheadacr" }   # Must be globally unique and lowercase.
$AppName         = if ($env:APP_NAME)         { $env:APP_NAME }         else { "copperhead-server" }
$Environment     = if ($env:ENVIRONMENT)      { $env:ENVIRONMENT }      else { "copperhead-env" }
$ImageName       = if ($env:IMAGE_NAME)       { $env:IMAGE_NAME }       else { "copperhead-server" }
$ImageTag        = if ($env:IMAGE_TAG)        { $env:IMAGE_TAG }        else { "latest" }
$ContainerPort   = if ($env:CONTAINER_PORT)   { $env:CONTAINER_PORT }   else { "8765" }
$Cpu             = if ($env:CPU)              { $env:CPU }              else { "1.0" }
$Memory          = if ($env:MEMORY)           { $env:MEMORY }           else { "2.0Gi" }
$MinReplicas     = if ($env:MIN_REPLICAS)     { $env:MIN_REPLICAS }     else { "1" }
$MaxReplicas     = if ($env:MAX_REPLICAS)     { $env:MAX_REPLICAS }     else { "1" }
$StorageAccount  = if ($env:STORAGE_ACCOUNT)  { $env:STORAGE_ACCOUNT }  else { "copperheadstore" }  # Must be globally unique and lowercase.
$FileShareName   = "copperhead-config"
$MountPath       = "/app/config"

$ScriptDir       = Split-Path -Parent $MyInvocation.MyCommand.Path
$RegistryServer  = "$AcrName.azurecr.io"
$Image           = "$RegistryServer/${ImageName}:${ImageTag}"
$RevisionSuffix  = "r" + (Get-Date -AsUTC -Format "yyMMddHHmmss")

# --- Helper functions for colored output ---

function Write-Section($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Info($msg)    { Write-Host $msg -ForegroundColor Yellow }
function Write-Ok($msg)      { Write-Host $msg -ForegroundColor Green }
function Write-Err($msg)     { Write-Host "ERROR: $msg" -ForegroundColor Red }

# --- Pre-flight checks ---

if (-not (Test-Path "$ScriptDir\Dockerfile")) {
    Write-Err "No Dockerfile was found in $ScriptDir. Create the Dockerfile first, then rerun this script."
    exit 1
}

if (-not (Test-Path "$ScriptDir\server-settings.json")) {
    Write-Err "server-settings.json was not found in $ScriptDir."
    exit 1
}

if ($AcrName -notmatch "^[a-z0-9]{5,50}$") {
    Write-Err "ACR_NAME must be 5-50 characters long and contain only lowercase letters and numbers."
    exit 1
}

# --- Step 1: Check Azure CLI ---

Write-Section "Checking Azure CLI"

Write-Host "Checking whether the Azure CLI is installed..."
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Err "Azure CLI is not installed. Install it from https://aka.ms/azure-cli and rerun this script."
    exit 1
}

Write-Host "Checking whether you are logged in to Azure..."
$loginCheck = az account show 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Azure CLI is not logged in. Run 'az login' and rerun this script."
    exit 1
}

$SubscriptionName = az account show --query name -o tsv
Write-Ok "Azure CLI is ready. Current subscription: $SubscriptionName"

# --- Step 2: Ensure Container Apps extension ---

Write-Section "Ensuring Container Apps commands are available"
Write-Host "Adding or updating the Azure Container Apps CLI extension if needed..."
az extension add --name containerapp --upgrade --only-show-errors 2>&1 | Out-Null
Write-Ok "Azure Container Apps commands are available."

# --- Step 3: Create resource group ---

Write-Section "Creating resource group"
Write-Host "Creating resource group '$ResourceGroup' in '$Location' (safe to run again if it already exists)..."
az group create --name $ResourceGroup --location $Location --output table
if ($LASTEXITCODE -ne 0) { Write-Err "Failed to create resource group."; exit 1 }
Write-Ok "Resource group is ready."

# --- Step 4: Create Azure Container Registry ---

Write-Section "Creating Azure Container Registry"
Write-Host "Creating Azure Container Registry '$AcrName' with the Basic SKU for lower cost..."

$acrExists = az acr show --name $AcrName --resource-group $ResourceGroup 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Info "ACR already exists. Reusing it and making sure admin access is enabled."
    az acr update --name $AcrName --resource-group $ResourceGroup --admin-enabled true --output none
} else {
    az acr create --name $AcrName --resource-group $ResourceGroup --location $Location --sku Basic --admin-enabled true --output table
    if ($LASTEXITCODE -ne 0) { Write-Err "Failed to create ACR."; exit 1 }
}
Write-Ok "Azure Container Registry is ready."

# --- Step 4b: Create Storage Account and File Share ---

Write-Section "Creating Azure Storage Account and File Share"
Write-Host "Creating storage account '$StorageAccount' for server-settings.json and log files..."

$storageExists = az storage account show --name $StorageAccount --resource-group $ResourceGroup 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Info "Storage account already exists. Reusing it."
} else {
    az storage account create `
        --name $StorageAccount `
        --resource-group $ResourceGroup `
        --location $Location `
        --sku Standard_LRS `
        --output table
    if ($LASTEXITCODE -ne 0) { Write-Err "Failed to create storage account."; exit 1 }
}

# Get the storage account key for file share operations
$StorageKey = az storage account keys list --account-name $StorageAccount --resource-group $ResourceGroup --query "[0].value" -o tsv

# Create file share if it doesn't exist
$shareExists = az storage share show --name $FileShareName --account-name $StorageAccount --account-key $StorageKey 2>&1
if ($LASTEXITCODE -ne 0) {
    az storage share create --name $FileShareName --account-name $StorageAccount --account-key $StorageKey --output table
    if ($LASTEXITCODE -ne 0) { Write-Err "Failed to create file share."; exit 1 }
}

# Upload server-settings.json to the file share (overwrite if exists)
Write-Host "Uploading server-settings.json to file share..."
az storage file upload `
    --share-name $FileShareName `
    --account-name $StorageAccount `
    --account-key $StorageKey `
    --source "$ScriptDir\server-settings.json" `
    --path "server-settings.json" `
    --output none

Write-Ok "Storage account and file share are ready."

# --- Step 5: Bundle client files (if available) ---

$clientSrc = Join-Path (Split-Path $ScriptDir) "copperhead-client"
$clientDst = Join-Path $ScriptDir "client"

if (Test-Path $clientSrc) {
    Write-Section "Bundling client files"
    Write-Host "Copying client from $clientSrc into server image..."
    if (Test-Path $clientDst) { Remove-Item $clientDst -Recurse -Force }
    New-Item -ItemType Directory -Path $clientDst -Force | Out-Null
    Get-ChildItem $clientSrc -Exclude ".git",".github","node_modules" |
        Copy-Item -Destination $clientDst -Recurse -Force
    Write-Ok "Client files bundled. The server will serve them at the root URL."
} else {
    Write-Info "No copperhead-client directory found alongside copperhead-server. Client will not be bundled."
}

# --- Step 6: Build Docker image in Azure ---

Write-Section "Building Docker image in Azure"
Write-Host "Building the '${ImageName}:${ImageTag}' image in ACR with 'az acr build' so no local Docker install is needed..."
az acr build --registry $AcrName --image "${ImageName}:${ImageTag}" $ScriptDir
if ($LASTEXITCODE -ne 0) { Write-Err "Docker image build failed."; exit 1 }
Write-Ok "Docker image build completed."

# Clean up bundled client files after build
if (Test-Path $clientDst) {
    Remove-Item $clientDst -Recurse -Force
}

# --- Step 6: Create Container Apps environment ---

Write-Section "Creating Container Apps environment"
Write-Host "Creating the Container Apps environment '$Environment' (safe to rerun if it already exists)..."

$envExists = az containerapp env show --name $Environment --resource-group $ResourceGroup 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Info "Container Apps environment already exists. Reusing it."
} else {
    az containerapp env create --name $Environment --resource-group $ResourceGroup --location $Location --output table
    if ($LASTEXITCODE -ne 0) { Write-Err "Failed to create Container Apps environment."; exit 1 }
}
Write-Ok "Container Apps environment is ready."

# --- Link storage to environment ---

Write-Section "Linking file share to Container Apps environment"
Write-Host "Adding storage '$StorageAccount' to environment '$Environment'..."
# Remove existing link if present (safe to fail)
az containerapp env storage remove --name $Environment --resource-group $ResourceGroup --storage-name copperheadfiles --yes 2>&1 | Out-Null
az containerapp env storage set `
    --name $Environment `
    --resource-group $ResourceGroup `
    --storage-name copperheadfiles `
    --azure-file-account-name $StorageAccount `
    --azure-file-account-key $StorageKey `
    --azure-file-share-name $FileShareName `
    --access-mode ReadWrite `
    --output table
if ($LASTEXITCODE -ne 0) { Write-Err "Failed to link storage."; exit 1 }
Write-Ok "File share linked to environment."

# --- Step 7: Create or update the Container App with file share mount ---
#
# Volume mounts require a YAML template — the az CLI doesn't support them
# as direct command-line arguments. We generate the YAML dynamically.

Write-Section "Creating Container App"
Write-Host "Creating or updating the Container App '$AppName' with external ingress on port $ContainerPort..."
Write-Host "Mounting file share at $MountPath for server-settings.json and log files."

$AcrUsername = az acr credential show --name $AcrName --query username -o tsv
$AcrPassword = az acr credential show --name $AcrName --query "passwords[0].value" -o tsv

# Generate a YAML template for the container app with volume mount
$yamlContent = @"
properties:
  configuration:
    ingress:
      external: true
      targetPort: $ContainerPort
      transport: auto
    registries:
      - server: $RegistryServer
        username: $AcrUsername
        passwordSecretRef: acr-password
    secrets:
      - name: acr-password
        value: $AcrPassword
  template:
    revisionSuffix: $RevisionSuffix
    scale:
      minReplicas: $MinReplicas
      maxReplicas: $MaxReplicas
    containers:
      - name: $AppName
        image: $Image
        resources:
          cpu: $Cpu
          memory: $Memory
        command: ["python", "main.py", "$MountPath/server-settings.json", "--log-file", "$MountPath/server-log.txt"]
        volumeMounts:
          - volumeName: config-volume
            mountPath: $MountPath
    volumes:
      - name: config-volume
        storageType: AzureFile
        storageName: copperheadfiles
"@

$yamlPath = Join-Path $env:TEMP "copperhead-app.yaml"
$yamlContent | Out-File -FilePath $yamlPath -Encoding utf8

$appExists = az containerapp show --name $AppName --resource-group $ResourceGroup 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Info "Container App already exists. Updating with volume mount."
    az containerapp update `
        --name $AppName `
        --resource-group $ResourceGroup `
        --yaml $yamlPath `
        --output table
} else {
    az containerapp create `
        --name $AppName `
        --resource-group $ResourceGroup `
        --environment $Environment `
        --yaml $yamlPath `
        --output table
    if ($LASTEXITCODE -ne 0) { Write-Err "Failed to create Container App."; exit 1 }
}

# Clean up temp file
Remove-Item $yamlPath -ErrorAction SilentlyContinue

Write-Ok "Container App deployment completed."

# --- Step 8: Print the deployed URL and admin console link ---

Write-Section "Fetching deployed URL"
$Fqdn = az containerapp show --name $AppName --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn -o tsv

Write-Host "HTTP URL:      https://$Fqdn"
Write-Host "WebSocket URL: wss://$Fqdn"

# Wait for the container to start, then extract the admin token from the logs.
Write-Host ""
Write-Host "Waiting for server to start..."
Start-Sleep 15
$adminToken = az containerapp logs show --name $AppName --resource-group $ResourceGroup --format text --tail 50 2>&1 `
    | Select-String -Pattern "Admin token: (\w+)" `
    | ForEach-Object { $_.Matches[0].Groups[1].Value } `
    | Select-Object -First 1

if ($adminToken) {
    $wsUrl = [uri]::EscapeDataString("wss://$Fqdn/ws/")
    $adminUrl = "https://revodavid.github.io/copperhead-client/?server=$wsUrl&admin=$adminToken"
    Write-Host ""
    Write-Ok "Admin console:"
    Write-Host $adminUrl
} else {
    Write-Info "Could not find admin token in logs. Check logs manually:"
    Write-Host "  az containerapp logs show --name $AppName --resource-group $ResourceGroup --format text --tail 30"
}

Write-Host ""
Write-Ok "Deployment finished successfully."

# --- Useful management commands ---

Write-Section "Useful management commands"
Write-Host @"

View logs:
  az containerapp logs show --name $AppName --resource-group $ResourceGroup --follow --format text

View server log file (from file share):
  az storage file download --share-name $FileShareName --account-name $StorageAccount --path server-log.txt --dest ./server-log.txt --account-key <key>

Edit server-settings.json:
  1. Open the Azure Portal: https://portal.azure.com
  2. Go to Storage Accounts > $StorageAccount > File shares > $FileShareName
  3. Click server-settings.json > Edit
  4. Save — the server will auto-reload within seconds

  Or from the command line:
  az storage file download --share-name $FileShareName --account-name $StorageAccount --path server-settings.json --dest ./server-settings-downloaded.json --account-key <key>
  # Edit the file, then upload:
  az storage file upload --share-name $FileShareName --account-name $StorageAccount --source ./server-settings-downloaded.json --path server-settings.json --account-key <key>

Restart the latest active revision:
  `$rev = az containerapp revision list --name $AppName --resource-group $ResourceGroup --query "[?properties.active].name | [0]" -o tsv
  az containerapp revision restart --name $AppName --resource-group $ResourceGroup --revision `$rev

Redeploy (after code changes):
  .\deploy-azure.ps1

Delete all deployed resources:
  az group delete --name $ResourceGroup --yes --no-wait
"@
