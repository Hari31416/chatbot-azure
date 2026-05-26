import json
import subprocess
import os

def main():
    print("🚀 Fetching deployment outputs from Azure...")
    try:
        result = subprocess.run(
            ["az", "deployment", "sub", "show", "--name", "main", "--query", "properties.outputs", "--output", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        outputs = json.loads(result.stdout)
    except Exception as e:
        print(f"❌ Error fetching deployment outputs: {e}")
        return

    env_updates = {
        "AZURE_STORAGE_ACCOUNT_NAME": outputs.get("azurE_STORAGE_ACCOUNT_NAME", {}).get("value"),
        "COSMOS_ENDPOINT": outputs.get("cosmoS_ENDPOINT", {}).get("value"),
        "AZURE_KEYVAULT_NAME": outputs.get("azurE_KEYVAULT_NAME", {}).get("value"),
        "AZURE_CONTAINER_REGISTRY": outputs.get("azurE_CONTAINER_REGISTRY", {}).get("value"),
        "AZURE_SWA_DEPLOYMENT_TOKEN": outputs.get("azurE_SWA_DEPLOYMENT_TOKEN", {}).get("value")
    }

    env_vars = {}
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()
    else:
        # Load from .env.example if .env does not exist
        if os.path.exists(".env.example"):
            with open(".env.example", "r") as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()

    # Update with new Bicep outputs
    for k, v in env_updates.items():
        if v:
            env_vars[k] = v

    # Write back to .env
    with open(".env", "w") as f:
        f.write("# ──────────────────────────────────────────────\n")
        f.write("# Azure Environment Configuration (Auto-Generated)\n")
        f.write("# ──────────────────────────────────────────────\n")
        for k, v in sorted(env_vars.items()):
            f.write(f"{k}={v}\n")
            
    print("✅ Successfully updated .env with Azure deployment outputs!")

if __name__ == "__main__":
    main()
