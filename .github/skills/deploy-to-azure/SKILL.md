---
name: deploy-to-azure
description: Redeploy the CopperHead server to Azure Container Apps using server-settings.azure.json as the config file.
---

# Deploy CopperHead to Azure

Use this skill when the user asks to deploy, redeploy, or update the Azure deployment.

Examples:
- "deploy to azure"
- "update the azure deployment"
- "redeploy to azure"
- "push to azure"

## Goal

Rebuild the Docker image, upload `server-settings.azure.json` to the Azure File Share, and update the Container App. Report the deployed URL and admin console URL when finished.

## Prerequisites

- Azure CLI installed and logged in (`az login`)
- The deploy script `copperhead-server\deploy-azure.ps1` exists
- The file `copperhead-server\server-settings.azure.json` exists (gitignored config for Azure)
- Resource group `copperhead-west-rg` already exists from initial deployment

## Deploy procedure

1. Verify Azure CLI is logged in.

   ```powershell
   az account show --query name -o tsv
   ```

2. Verify `server-settings.azure.json` exists.

   ```powershell
   Test-Path <project_root>\copperhead-server\server-settings.azure.json
   ```

3. Copy `server-settings.azure.json` over `server-settings.json` so it gets uploaded to the Azure File Share by the deploy script.

   ```powershell
   Set-Location <project_root>\copperhead-server
   Copy-Item server-settings.azure.json server-settings.json -Force
   ```

4. Run the deploy script with the correct resource group.

   ```powershell
   $env:RESOURCE_GROUP = "copperhead-west-rg"
   .\deploy-azure.ps1
   ```

   This script will:
   - Bundle the client files from copperhead-client/ (if found alongside)
   - Build the Docker image in Azure Container Registry
   - Upload server-settings.json to the Azure File Share
   - Update the Container App with the new image and volume mount
   - Clean up bundled client files after build
   - Print the deployed URL and admin console URL

5. After deployment, restore the original `server-settings.json` from git.

   ```powershell
   git checkout server-settings.json
   ```

6. Get the admin token. Download `server-log.txt` from the Azure File Share and extract the token:

   ```powershell
   $key = az storage account keys list --account-name copperheadstore --resource-group copperhead-west-rg --query "[0].value" -o tsv
   az storage file download --share-name copperhead-config --account-name copperheadstore --account-key $key --path server-log.txt --dest "$env:TEMP\server-log.txt" --output none
   $adminToken = Get-Content "$env:TEMP\server-log.txt" | Select-String "Admin token: (\w+)" | ForEach-Object { $_.Matches[0].Groups[1].Value } | Select-Object -Last 1
   ```

7. Report to the user using the **Azure-hosted client URL** (not GitHub Pages). The deployed server serves the client at its root URL:
   - Player URL: `https://<FQDN>/?server=wss%3A%2F%2F<FQDN>%2Fws%2F`
   - Admin URL: `https://<FQDN>/?server=wss%3A%2F%2F<FQDN>%2Fws%2F&admin=<TOKEN>`
   - Where `<FQDN>` is the Container App FQDN from the deploy script output
   - Remind them they can edit settings in the Azure Portal:
     Storage Accounts → copperheadstore → File shares → copperhead-config → server-settings.json

## Important notes

- Always use `$env:RESOURCE_GROUP = "copperhead-west-rg"` — this is the existing resource group in westus2.
- The deploy script runs for 2-3 minutes. Run it in async mode and monitor output.
- The admin token may not be captured from logs if polling traffic pushes startup messages out. In that case, tell the user to check the Azure Portal File Share for `server-log.txt` which contains the admin token.
- Do NOT push to GitHub — this skill only deploys to Azure.
- The project root is the parent directory that contains `copperhead-server\`.
