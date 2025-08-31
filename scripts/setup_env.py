#!/usr/bin/env python3
"""
Interactive environment setup script for RAG Modulo.
Guides users through creating a working .env file.
"""

import os
import shutil
import secrets
import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, check: bool = True) -> str:
    """Run a command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if check:
            print(f"❌ Command failed: {cmd}")
            print(f"Error: {e.stderr}")
        return ""


def generate_jwt_secret() -> str:
    """Generate a secure JWT secret."""
    return secrets.token_hex(32)


def check_prerequisites() -> bool:
    """Check if required tools are available."""
    print("🔍 Checking prerequisites...")
    
    missing = []
    
    # Check for required commands
    if not run_command("which openssl", check=False):
        missing.append("openssl")
    
    if not run_command("which docker", check=False):
        missing.append("docker")
        
    if missing:
        print(f"❌ Missing required tools: {', '.join(missing)}")
        print("\nPlease install:")
        for tool in missing:
            if tool == "openssl":
                print("  - OpenSSL: brew install openssl (macOS) or apt-get install openssl (Ubuntu)")
            elif tool == "docker":
                print("  - Docker: https://docs.docker.com/get-docker/")
        return False
    
    print("✅ All prerequisites found!")
    return True


def copy_env_template() -> bool:
    """Copy .env.example to .env if it doesn't exist."""
    env_path = Path(".env")
    template_path = Path(".env.example")
    
    if not template_path.exists():
        print("❌ .env.example not found! Make sure you're in the project root.")
        return False
    
    if env_path.exists():
        response = input("⚠️  .env already exists. Overwrite? (y/N): ").lower()
        if response != 'y':
            print("📝 Using existing .env file...")
            return True
    
    shutil.copy(template_path, env_path)
    print("✅ Created .env from template")
    return True


def setup_auto_generated_values() -> None:
    """Set up values that can be auto-generated."""
    print("\n🔧 Setting up auto-generated values...")
    
    # Generate JWT secret
    jwt_secret = generate_jwt_secret()
    
    # Read .env file
    with open(".env", "r") as f:
        content = f.read()
    
    # Replace auto-generated values
    content = content.replace("generate_with_openssl_rand_hex_32", jwt_secret)
    
    # Write back
    with open(".env", "w") as f:
        f.write(content)
    
    print("✅ Generated JWT secret")


def guide_manual_setup() -> None:
    """Guide user through manual credential setup."""
    print("\n🔐 Manual Credential Setup Required")
    print("=" * 50)
    
    credentials_needed = [
        {
            "name": "WATSONX_APIKEY",
            "description": "Watson AI API Key",
            "instructions": "1. Go to IBM Cloud > Watson AI\n   2. Go to your service instance\n   3. Copy API Key from Credentials tab"
        },
        {
            "name": "WATSONX_INSTANCE_ID", 
            "description": "Watson AI Instance ID",
            "instructions": "1. Go to IBM Cloud > Watson AI\n   2. Go to your service instance\n   3. Copy Instance ID from service details"
        },
        {
            "name": "OPENAI_API_KEY",
            "description": "OpenAI API Key", 
            "instructions": "1. Go to https://platform.openai.com/api-keys\n   2. Create new key or copy existing\n   3. Starts with 'sk-'"
        },
        {
            "name": "ANTHROPIC_API_KEY",
            "description": "Anthropic API Key",
            "instructions": "1. Go to https://console.anthropic.com/settings/keys\n   2. Create new key or copy existing\n   3. Starts with 'sk-ant-'"
        }
    ]
    
    for cred in credentials_needed:
        print(f"\n📋 {cred['name']} - {cred['description']}")
        print(f"   {cred['instructions']}")
        print(f"   Then edit .env and replace: {cred['name']}=...")


def validate_setup() -> bool:
    """Validate the setup by running the validation script."""
    print("\n🧪 Validating setup...")
    
    if not Path("scripts/validate_env.py").exists():
        print("⚠️  Validation script not found, skipping validation")
        return True
    
    result = run_command("python scripts/validate_env.py", check=False)
    if "validation passed" in result.lower():
        print("✅ Environment validation passed!")
        return True
    else:
        print("❌ Environment validation failed")
        print(result)
        return False


def main():
    """Main setup flow."""
    print("🚀 RAG Modulo Environment Setup")
    print("=" * 40)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Copy template
    if not copy_env_template():
        sys.exit(1)
    
    # Setup auto-generated values
    setup_auto_generated_values()
    
    # Guide manual setup
    guide_manual_setup()
    
    print("\n✨ Setup Complete!")
    print("=" * 20)
    print("Next steps:")
    print("1. Edit .env and fill in the 🔐 CRITICAL values shown above")
    print("2. Run: make validate-env")
    print("3. Run: make tests")
    print("\n💡 Keep your .env file secure and never commit it!")


if __name__ == "__main__":
    main()