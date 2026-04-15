#!/usr/bin/env bash
#
# Deploy the CopperHead game server to Azure Container Apps.
#
# Usage:
#   1. Review the configuration values in the section below.
#   2. Make sure the repo root contains Dockerfile and server-settings.json.
#   3. Run this script from the repo root in Git Bash, WSL, or another Bash shell:
#      bash tools/deploy-azure.sh
#
# Notes:
#   - This script uses 'az acr build', so Docker does not need to be installed locally.
#   - server-settings.json is stored on an Azure File Share so you can edit it
#     from the Azure Portal (Storage Browser) without redeploying.
#   - The server log file is also written to the file share for easy access.

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
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-copperheadstore}"  # Must be globally unique and lowercase.
FILE_SHARE_NAME="copperhead-config"
MOUNT_PATH="/app/config"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
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
if [[ ! -f "${PROJECT_DIR}/Dockerfile" ]]; then
    print_error "No Dockerfile was found in ${PROJECT_DIR}. Create the Dockerfile first, then rerun this script."
    exit 1
fi

if [[ ! -f "${PROJECT_DIR}/server-settings.json" ]]; then
    print_error "server-settings.json was not found in ${PROJECT_DIR}."
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

print_section "Creating Azure Storage Account and File Share"
echo "Creating storage account '${STORAGE_ACCOUNT}' for server-settings.json and log files..."
if az storage account show --name "${STORAGE_ACCOUNT}" --resource-group "${RESOURCE_GROUP}" >/dev/null 2>&1; then
    print_info "Storage account already exists. Reusing it."
else
    az storage account create \
        --name "${STORAGE_ACCOUNT}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}" \
        --sku Standard_LRS \
        --output table
fi

STORAGE_KEY="$(az storage account keys list --account-name "${STORAGE_ACCOUNT}" --resource-group "${RESOURCE_GROUP}" --query "[0].value" -o tsv)"

if az storage share show --name "${FILE_SHARE_NAME}" --account-name "${STORAGE_ACCOUNT}" --account-key "${STORAGE_KEY}" >/dev/null 2>&1; then
    print_info "File share already exists. Reusing it."
else
    az storage share create \
        --name "${FILE_SHARE_NAME}" \
        --account-name "${STORAGE_ACCOUNT}" \
        --account-key "${STORAGE_KEY}" \
        --output table
fi

echo "Uploading server-settings.json to file share..."
az storage file upload \
    --share-name "${FILE_SHARE_NAME}" \
    --account-name "${STORAGE_ACCOUNT}" \
    --account-key "${STORAGE_KEY}" \
    --source "${PROJECT_DIR}/server-settings.json" \
    --path "server-settings.json" \
    --output none
print_success "Storage account and file share are ready."

# Bundle client files into the server image if the client repo is alongside the server repo
CLIENT_SRC="$(dirname "${PROJECT_DIR}")/copperhead-client"
CLIENT_DST="${PROJECT_DIR}/client"

if [ -d "${CLIENT_SRC}" ]; then
    print_section "Bundling client files"
    echo "Copying client from ${CLIENT_SRC} into server image..."
    rm -rf "${CLIENT_DST}"
    mkdir -p "${CLIENT_DST}"
    # Copy everything except .git and .github
    rsync -a --exclude='.git' --exclude='.github' --exclude='node_modules' "${CLIENT_SRC}/" "${CLIENT_DST}/" 2>/dev/null \
        || cp -r "${CLIENT_SRC}"/* "${CLIENT_DST}/" 2>/dev/null
    print_success "Client files bundled. The server will serve them at the root URL."
else
    print_info "No copperhead-client directory found alongside copperhead-server. Client will not be bundled."
fi

print_section "Building Docker image in Azure"
echo "Building the '${IMAGE_NAME}:${IMAGE_TAG}' image in ACR with 'az acr build' so no local Docker install is needed..."
az acr build \
    --registry "${ACR_NAME}" \
    --image "${IMAGE_NAME}:${IMAGE_TAG}" \
    "${PROJECT_DIR}"
print_success "Docker image build completed."

# Clean up bundled client files after build
if [ -d "${CLIENT_DST}" ]; then
    rm -rf "${CLIENT_DST}"
fi

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

print_section "Linking file share to Container Apps environment"
echo "Adding storage '${STORAGE_ACCOUNT}' to environment '${ENVIRONMENT}'..."
az containerapp env storage remove \
    --name "${ENVIRONMENT}" \
    --resource-group "${RESOURCE_GROUP}" \
    --storage-name copperheadfiles --yes >/dev/null 2>&1 || true
az containerapp env storage set \
    --name "${ENVIRONMENT}" \
    --resource-group "${RESOURCE_GROUP}" \
    --storage-name copperheadfiles \
    --azure-file-account-name "${STORAGE_ACCOUNT}" \
    --azure-file-account-key "${STORAGE_KEY}" \
    --azure-file-share-name "${FILE_SHARE_NAME}" \
    --access-mode ReadWrite \
    --output table
print_success "File share linked to environment."

print_section "Creating Container App"
echo "Creating or updating the Container App '${APP_NAME}' with external ingress on port ${CONTAINER_PORT}..."
echo "Using min replicas = ${MIN_REPLICAS} and max replicas = ${MAX_REPLICAS} so the game server stays warm and does not scale out unexpectedly."
echo "Using revision suffix '${REVISION_SUFFIX}' so each deployment creates a fresh Container Apps revision, even when reusing the same image tag."
echo "Mounting file share at ${MOUNT_PATH} for server-settings.json and log files."

ACR_USERNAME="$(az acr credential show --name "${ACR_NAME}" --query username -o tsv)"
ACR_PASSWORD="$(az acr credential show --name "${ACR_NAME}" --query 'passwords[0].value' -o tsv)"
YAML_PATH="$(mktemp)"
cleanup_yaml() {
    rm -f "${YAML_PATH}"
}
trap cleanup_yaml EXIT

cat > "${YAML_PATH}" <<EOF
properties:
  configuration:
    ingress:
      external: true
      targetPort: ${CONTAINER_PORT}
      transport: auto
    registries:
      - server: ${REGISTRY_SERVER}
        username: ${ACR_USERNAME}
        passwordSecretRef: acr-password
    secrets:
      - name: acr-password
        value: ${ACR_PASSWORD}
  template:
    revisionSuffix: ${REVISION_SUFFIX}
    scale:
      minReplicas: ${MIN_REPLICAS}
      maxReplicas: ${MAX_REPLICAS}
    containers:
      - name: ${APP_NAME}
        image: ${IMAGE}
        resources:
          cpu: ${CPU}
          memory: ${MEMORY}
        command: ["python", "main.py", "${MOUNT_PATH}/server-settings.json", "--log-file", "${MOUNT_PATH}/server-log.txt"]
        volumeMounts:
          - volumeName: config-volume
            mountPath: ${MOUNT_PATH}
    volumes:
      - name: config-volume
        storageType: AzureFile
        storageName: copperheadfiles
EOF

if az containerapp show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" >/dev/null 2>&1; then
    print_info "Container App already exists. Updating with volume mount."
    az containerapp update \
        --name "${APP_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --yaml "${YAML_PATH}" \
        --output table
else
    az containerapp create \
        --name "${APP_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --environment "${ENVIRONMENT}" \
        --yaml "${YAML_PATH}" \
        --output table
fi

rm -f "${YAML_PATH}"
trap - EXIT
print_success "Container App deployment completed."

print_section "Fetching deployed URL"
FQDN="$(az containerapp show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --query properties.configuration.ingress.fqdn -o tsv)"
HTTPS_URL="https://${FQDN}"
WEBSOCKET_URL="wss://${FQDN}"
WS_ENCODED="$(python3 -c "import urllib.parse; print(urllib.parse.quote('wss://${FQDN}/ws/', safe=''))" 2>/dev/null \
    || echo "wss%3A%2F%2F${FQDN}%2Fws%2F")"
PLAYER_URL="https://${FQDN}/?server=${WS_ENCODED}"

echo "HTTP URL:      ${HTTPS_URL}"
echo "WebSocket URL: ${WEBSOCKET_URL}"
echo "Player URL:    ${PLAYER_URL}"

# Wait for the container to start, then extract the admin token from the logs.
echo ""
echo "Waiting for server to start..."
sleep 15
ADMIN_TOKEN="$(az containerapp logs show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --format text --tail 50 2>&1 \
    | grep -oP 'Admin token: \K\w+' | head -1)"

if [ -n "${ADMIN_TOKEN}" ]; then
    ADMIN_URL="${PLAYER_URL}&admin=${ADMIN_TOKEN}"
    echo ""
    print_success "Admin console:"
    echo "${ADMIN_URL}"
else
    print_info "Could not find admin token in logs. Check logs manually:"
    echo "  az containerapp logs show --name ${APP_NAME} --resource-group ${RESOURCE_GROUP} --format text --tail 30"
fi

echo ""
print_success "Deployment finished successfully."

print_section "Useful management commands"
cat <<EOF
View logs:
  az containerapp logs show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --follow --format text

View server log file (from file share):
  az storage file download --share-name "${FILE_SHARE_NAME}" --account-name "${STORAGE_ACCOUNT}" --path server-log.txt --dest ./server-log.txt --account-key <key>

Edit server-settings.json:
  1. Open the Azure Portal: https://portal.azure.com
  2. Go to Storage Accounts > ${STORAGE_ACCOUNT} > File shares > ${FILE_SHARE_NAME}
  3. Click server-settings.json > Edit
  4. Save — the server will auto-reload within seconds

  Or from the command line:
  az storage file download --share-name "${FILE_SHARE_NAME}" --account-name "${STORAGE_ACCOUNT}" --path server-settings.json --dest ./server-settings-downloaded.json --account-key <key>
  # Edit the file, then upload:
  az storage file upload --share-name "${FILE_SHARE_NAME}" --account-name "${STORAGE_ACCOUNT}" --source ./server-settings-downloaded.json --path server-settings.json --account-key <key>

Restart the latest active revision:
  REVISION_NAME=\$(az containerapp revision list --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --query "[?properties.active].name | [0]" -o tsv)
  az containerapp revision restart --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --revision "\$REVISION_NAME"

Redeploy (after code changes):
  bash deploy-azure.sh

Delete all deployed resources:
  az group delete --name "${RESOURCE_GROUP}" --yes --no-wait
EOF
