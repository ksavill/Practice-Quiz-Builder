#!/usr/bin/env python3
"""
Setup script for AI features - helps configure OpenAI API key
"""

import os

def setup_openai_key():
    """Setup OpenAI API key for AI question generation"""
    
    print("🤖 AI Question Generator Setup")
    print("=" * 40)
    
    # Check if key is already set
    existing_key = os.getenv("OPENAI_API_KEY")
    if existing_key:
        print(f"✅ OpenAI API key is already configured (ends with: ...{existing_key[-4:]})")
        return
    
    print("\n📝 To use AI question generation, you need an OpenAI API key.")
    print("   1. Go to https://platform.openai.com/api-keys")
    print("   2. Create a new API key")
    print("   3. Copy the key and set it as an environment variable")
    print("\n🔧 Set your API key using one of these methods:")
    
    print("\n   Windows (Command Prompt):")
    print("   set OPENAI_API_KEY=your_api_key_here")
    
    print("\n   Windows (PowerShell):")
    print("   $env:OPENAI_API_KEY='your_api_key_here'")
    
    print("\n   Linux/Mac:")
    print("   export OPENAI_API_KEY=your_api_key_here")
    
    print("\n   Or create a .env file in this directory with:")
    print("   OPENAI_API_KEY=your_api_key_here")
    
    print("\n⚠️  Important Notes:")
    print("   - Keep your API key secure and never commit it to version control")
    print("   - OpenAI charges per API usage - monitor your usage at platform.openai.com")
    print("   - The app uses GPT-4o model for best multimodal support")
    
    print("\n🚀 After setting the key, restart the server to enable AI features!")

if __name__ == "__main__":
    setup_openai_key()
