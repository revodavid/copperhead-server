# CopperHead Server — Tools

Utility scripts for development, testing, and deployment.

## Scripts

| File | Description |
|------|-------------|
| `launch_bots.py` | Launches N bots against a running server. Useful for stress-testing tournaments, filling a lobby, or testing a bot against many competitors. Run `python tools/launch_bots.py --help` for usage. |
| `deploy-azure.ps1` | PowerShell script to deploy the server to Azure Container Apps. Run with `pwsh -ExecutionPolicy Bypass -File tools\deploy-azure.ps1`. |
| `deploy-azure.sh` | Bash version of the Azure deployment script for Linux/macOS environments. |
