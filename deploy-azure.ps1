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
#   - server-settings.json is baked into the image. If you change it, rerun this script
#     to rebuild the image and redeploy the app.

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
$Cpu             = if ($env:CPU)              { $env:CPU }              else { "0.5" }
$Memory          = if ($env:MEMORY)           { $env:MEMORY }           else { "1.0Gi" }
$MinReplicas     = if ($env:MIN_REPLICAS)     { $env:MIN_REPLICAS }     else { "1" }
$MaxReplicas     = if ($env:MAX_REPLICAS)     { $env:MAX_REPLICAS }     else { "1" }

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

# --- Step 5: Build Docker image in Azure ---

Write-Section "Building Docker image in Azure"
Write-Host "Building the '${ImageName}:${ImageTag}' image in ACR with 'az acr build' so no local Docker install is needed..."
az acr build --registry $AcrName --image "${ImageName}:${ImageTag}" $ScriptDir
if ($LASTEXITCODE -ne 0) { Write-Err "Docker image build failed."; exit 1 }
Write-Ok "Docker image build completed."

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

# --- Step 7: Create or update the Container App ---

Write-Section "Creating Container App"
Write-Host "Creating or updating the Container App '$AppName' with external ingress on port $ContainerPort..."
Write-Host "Using min replicas = $MinReplicas and max replicas = $MaxReplicas so the game server stays warm."
Write-Host "Using revision suffix '$RevisionSuffix' so each deployment creates a fresh revision."

$AcrUsername = az acr credential show --name $AcrName --query username -o tsv
$AcrPassword = az acr credential show --name $AcrName --query "passwords[0].value" -o tsv

$appExists = az containerapp show --name $AppName --resource-group $ResourceGroup 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Info "Container App already exists. Updating it to the newly built image."
    az containerapp update `
        --name $AppName `
        --resource-group $ResourceGroup `
        --image $Image `
        --revision-suffix $RevisionSuffix `
        --cpu $Cpu `
        --memory $Memory `
        --min-replicas $MinReplicas `
        --max-replicas $MaxReplicas `
        --output table

    az containerapp ingress update `
        --name $AppName `
        --resource-group $ResourceGroup `
        --type external `
        --target-port $ContainerPort `
        --transport auto `
        --output table
} else {
    az containerapp create `
        --name $AppName `
        --resource-group $ResourceGroup `
        --environment $Environment `
        --image $Image `
        --revision-suffix $RevisionSuffix `
        --ingress external `
        --target-port $ContainerPort `
        --transport auto `
        --min-replicas $MinReplicas `
        --max-replicas $MaxReplicas `
        --cpu $Cpu `
        --memory $Memory `
        --registry-server $RegistryServer `
        --registry-username $AcrUsername `
        --registry-password $AcrPassword `
        --output table
    if ($LASTEXITCODE -ne 0) { Write-Err "Failed to create Container App."; exit 1 }
}
Write-Ok "Container App deployment completed."

# --- Step 8: Print the deployed URL ---

Write-Section "Fetching deployed URL"
$Fqdn = az containerapp show --name $AppName --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn -o tsv

Write-Host "HTTP URL:      https://$Fqdn"
Write-Host "WebSocket URL: wss://$Fqdn"
Write-Ok "Deployment finished successfully."

# --- Useful management commands ---

Write-Section "Useful management commands"
Write-Host @"

View logs:
  az containerapp logs show --name $AppName --resource-group $ResourceGroup --follow --format text

Restart the latest active revision:
  `$rev = az containerapp revision list --name $AppName --resource-group $ResourceGroup --query "[?properties.active].name | [0]" -o tsv
  az containerapp revision restart --name $AppName --resource-group $ResourceGroup --revision `$rev

Update server-settings.json and redeploy:
  # Edit server-settings.json in this folder, then run:
  .\deploy-azure.ps1

Delete all deployed resources:
  az group delete --name $ResourceGroup --yes --no-wait
"@
