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

4. Set the resource group environment variable. This MUST be done as a separate command — it cannot be chained with `&&`.

   ```powershell
   $env:RESOURCE_GROUP = "copperhead-west-rg"
   ```

5. Run the deploy script using `pwsh` (PowerShell 7). IMPORTANT: Do NOT use `powershell` — that launches Windows PowerShell 5.1 which lacks required features like `Get-Date -AsUTC`.

   ```powershell
   pwsh -ExecutionPolicy Bypass -File .\deploy-azure.ps1
   ```

   This script will:
   - Bundle the client files from copperhead-client/ (if found alongside)
   - Build the Docker image in Azure Container Registry
   - Upload server-settings.json to the Azure File Share
   - Update the Container App with the new image and volume mount
   - Clean up bundled client files after build
   - Print the deployed URL and admin console URL

   The script runs for 2-3 minutes. Run it in **async mode** and monitor output with `read_powershell`.

6. After deployment, restore the original `server-settings.json` from git.

   ```powershell
   git checkout server-settings.json
   ```

7. Get the admin token. The token may be a fixed value from `server-settings.azure.json` (check the `admin_token` field there first). If not configured, download `server-log.txt` from the Azure File Share and extract the auto-generated token:

   ```powershell
   $key = az storage account keys list --account-name copperheadstore --resource-group copperhead-west-rg --query "[0].value" -o tsv
   az storage file download --share-name copperhead-config --account-name copperheadstore --account-key $key --path server-log.txt --dest "$env:TEMP\server-log.txt" --output none
   $adminToken = Get-Content "$env:TEMP\server-log.txt" | Select-String "Admin token: (\w+)" | ForEach-Object { $_.Matches[0].Groups[1].Value } | Select-Object -Last 1
   ```

8. Report to the user using the **Azure-hosted client URL** (not GitHub Pages). The deployed server serves the client at its root URL:
   - Player URL: `https://<FQDN>/?server=wss%3A%2F%2F<FQDN>%2Fws%2F`
   - Admin URL: `https://<FQDN>/?server=wss%3A%2F%2F<FQDN>%2Fws%2F&admin=<TOKEN>`
   - Where `<FQDN>` is the Container App FQDN from the deploy script output
   - Remind them they can edit settings in the Azure Portal:
     Storage Accounts → copperheadstore → File shares → copperhead-config → server-settings.json

## Important notes

- Always use `$env:RESOURCE_GROUP = "copperhead-west-rg"` — this is the existing resource group in westus2.
- **Use `pwsh` not `powershell`** to run the deploy script. `powershell` invokes Windows PowerShell 5.1 which does not support `Get-Date -AsUTC` and will fail.
- **Set `$env:RESOURCE_GROUP` as a separate command**, not chained with `&&`. PowerShell does not allow `$env:VAR = "value"` assignments in `&&` chains.
- The admin token may not be captured from logs if polling traffic pushes startup messages out. In that case, check `server-settings.azure.json` for a configured `admin_token`, or tell the user to check the Azure Portal File Share for `server-log.txt`.
- Do NOT push to GitHub — this skill only deploys to Azure.
- The project root is the parent directory that contains `copperhead-server\`.
