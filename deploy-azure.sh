#!/usr/bin/env bash
#
# Deploy the CopperHead game server to Azure Container Apps.
#
# Usage:
#   1. Review the configuration values in the section below.
#   2. Make sure a Dockerfile exists in this folder.
#   3. Run this script from Git Bash, WSL, or another Bash shell:
#      bash deploy-azure.sh
#
# Notes:
#   - This script uses 'az acr build', so Docker does not need to be installed locally.
#   - server-settings.json is baked into the image. If you change it, rerun this script
#     to rebuild the image and redeploy the app.

set -euo pipefail

# -------------------------------
# Configuration
# -------------------------------
RESOURCE_GROUP="${RESOURCE_GROUP:-copperhead-rg}"
LOCATION="${LOCATION:-westus2}"
ACR_NAME="${ACR_NAME:-copperheadacr}"              # Must be globally unique and lowercase.
APP_NAME="${APP_NAME:-copperhead-server}"
ENVIRONMENT="${ENVIRONMENT:-copperhead-env}"
IMAGE_NAME="${IMAGE_NAME:-copperhead-server}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
CONTAINER_PORT="${CONTAINER_PORT:-8765}"
CPU="${CPU:-0.5}"
MEMORY="${MEMORY:-1.0Gi}"
MIN_REPLICAS="${MIN_REPLICAS:-1}"
MAX_REPLICAS="${MAX_REPLICAS:-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGISTRY_SERVER="${ACR_NAME}.azurecr.io"
IMAGE="${REGISTRY_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}"
REVISION_SUFFIX="${REVISION_SUFFIX:-r$(date -u +%y%m%d%H%M%S)}"

# Simple colored output to make the script easier to follow.
BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
RESET='\033[0m'

print_section() {
    echo -e "\n${BLUE}==> $1${RESET}"
}

print_info() {
    echo -e "${YELLOW}$1${RESET}"
}

print_success() {
    echo -e "${GREEN}$1${RESET}"
}

print_error() {
    echo -e "${RED}ERROR: $1${RESET}" >&2
}

# Helpful early checks prevent confusing Azure CLI errors later.
if [[ ! -f "${SCRIPT_DIR}/Dockerfile" ]]; then
    print_error "No Dockerfile was found in ${SCRIPT_DIR}. Create the Dockerfile first, then rerun this script."
    exit 1
fi

if [[ ! -f "${SCRIPT_DIR}/server-settings.json" ]]; then
    print_error "server-settings.json was not found in ${SCRIPT_DIR}."
    exit 1
fi

if [[ ! "${ACR_NAME}" =~ ^[a-z0-9]{5,50}$ ]]; then
    print_error "ACR_NAME must be 5-50 characters long and contain only lowercase letters and numbers."
    exit 1
fi

print_section "Checking Azure CLI"

echo "Checking whether the Azure CLI is installed..."
if ! command -v az >/dev/null 2>&1; then
    print_error "Azure CLI is not installed. Install it from https://aka.ms/azure-cli and rerun this script."
    exit 1
fi

echo "Checking whether you are logged in to Azure..."
if ! az account show >/dev/null 2>&1; then
    print_error "Azure CLI is not logged in. Run 'az login' and rerun this script."
    exit 1
fi

SUBSCRIPTION_NAME="$(az account show --query name -o tsv)"
print_success "Azure CLI is ready. Current subscription: ${SUBSCRIPTION_NAME}"

print_section "Ensuring Container Apps commands are available"
echo "Adding or updating the Azure Container Apps CLI extension if needed..."
az extension add --name containerapp --upgrade --only-show-errors >/dev/null
print_success "Azure Container Apps commands are available."

print_section "Creating resource group"
echo "Creating resource group '${RESOURCE_GROUP}' in '${LOCATION}' (safe to run again if it already exists)..."
az group create \
    --name "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --output table
print_success "Resource group is ready."

print_section "Creating Azure Container Registry"
echo "Creating Azure Container Registry '${ACR_NAME}' with the Basic SKU for lower cost..."
if az acr show --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" >/dev/null 2>&1; then
    print_info "ACR already exists. Reusing it and making sure admin access is enabled."
    az acr update \
        --name "${ACR_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --admin-enabled true \
        --output none
else
    az acr create \
        --name "${ACR_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}" \
        --sku Basic \
        --admin-enabled true \
        --output table
fi
print_success "Azure Container Registry is ready."

print_section "Building Docker image in Azure"
echo "Building the '${IMAGE_NAME}:${IMAGE_TAG}' image in ACR with 'az acr build' so no local Docker install is needed..."
az acr build \
    --registry "${ACR_NAME}" \
    --image "${IMAGE_NAME}:${IMAGE_TAG}" \
    "${SCRIPT_DIR}"
print_success "Docker image build completed."

print_section "Creating Container Apps environment"
echo "Creating the Container Apps environment '${ENVIRONMENT}' (safe to rerun if it already exists)..."
if az containerapp env show --name "${ENVIRONMENT}" --resource-group "${RESOURCE_GROUP}" >/dev/null 2>&1; then
    print_info "Container Apps environment already exists. Reusing it."
else
    az containerapp env create \
        --name "${ENVIRONMENT}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}" \
        --output table
fi
print_success "Container Apps environment is ready."

print_section "Creating Container App"
echo "Creating or updating the Container App '${APP_NAME}' with external ingress on port ${CONTAINER_PORT}..."
echo "Using min replicas = ${MIN_REPLICAS} and max replicas = ${MAX_REPLICAS} so the game server stays warm and does not scale out unexpectedly."
echo "Using revision suffix '${REVISION_SUFFIX}' so each deployment creates a fresh Container Apps revision, even when reusing the same image tag."

ACR_USERNAME="$(az acr credential show --name "${ACR_NAME}" --query username -o tsv)"
ACR_PASSWORD="$(az acr credential show --name "${ACR_NAME}" --query 'passwords[0].value' -o tsv)"

if az containerapp show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" >/dev/null 2>&1; then
    print_info "Container App already exists. Updating it to the newly built image and the desired scale settings."
    az containerapp update \
        --name "${APP_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --image "${IMAGE}" \
        --revision-suffix "${REVISION_SUFFIX}" \
        --cpu "${CPU}" \
        --memory "${MEMORY}" \
        --min-replicas "${MIN_REPLICAS}" \
        --max-replicas "${MAX_REPLICAS}" \
        --output table

    az containerapp ingress update \
        --name "${APP_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --type external \
        --target-port "${CONTAINER_PORT}" \
        --transport auto \
        --output table
else
    az containerapp create \
        --name "${APP_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --environment "${ENVIRONMENT}" \
        --image "${IMAGE}" \
        --revision-suffix "${REVISION_SUFFIX}" \
        --ingress external \
        --target-port "${CONTAINER_PORT}" \
        --transport auto \
        --min-replicas "${MIN_REPLICAS}" \
        --max-replicas "${MAX_REPLICAS}" \
        --cpu "${CPU}" \
        --memory "${MEMORY}" \
        --registry-server "${REGISTRY_SERVER}" \
        --registry-username "${ACR_USERNAME}" \
        --registry-password "${ACR_PASSWORD}" \
        --output table
fi
print_success "Container App deployment completed."

print_section "Fetching deployed URL"
FQDN="$(az containerapp show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --query properties.configuration.ingress.fqdn -o tsv)"
HTTPS_URL="https://${FQDN}"
WEBSOCKET_URL="wss://${FQDN}"

echo "HTTP URL:      ${HTTPS_URL}"
echo "WebSocket URL: ${WEBSOCKET_URL}"
print_success "Deployment finished successfully."

print_section "Useful management commands"
cat <<EOF
View logs:
  az containerapp logs show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --follow --format text

Restart the latest active revision:
  REVISION_NAME=\$(az containerapp revision list --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --query "[?properties.active].name | [0]" -o tsv)
  az containerapp revision restart --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --revision "\$REVISION_NAME"

Update server-settings.json and redeploy:
  # Edit server-settings.json in this folder, then run:
  bash deploy-azure.sh

  # If you only want the raw Azure commands, these are the important ones:
  REVISION_SUFFIX="r\$(date -u +%y%m%d%H%M%S)"
  az acr build --registry "${ACR_NAME}" --image "${IMAGE_NAME}:${IMAGE_TAG}" "${SCRIPT_DIR}"
  az containerapp update --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --image "${IMAGE}" --revision-suffix "\$REVISION_SUFFIX"

Delete all deployed resources:
  az group delete --name "${RESOURCE_GROUP}" --yes --no-wait
EOF
