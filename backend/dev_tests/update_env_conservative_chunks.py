#!/usr/bin/env python3
"""Update .env to use conservative chunking for all models."""

from pathlib import Path

from dotenv import set_key

env_file = Path("/Users/mg/mg-work/manav/work/ai-experiments/rag_modulo/.env")

# Use conservative chunking for ALL models (512-token limit)
# 500 chars ≈ 200 tokens (safe margin)
print("📝 Updating .env with conservative chunking for all models...")
set_key(str(env_file), "MAX_CHUNK_SIZE", "500", quote_mode="never")
set_key(str(env_file), "MIN_CHUNK_SIZE", "250", quote_mode="never")
set_key(str(env_file), "CHUNK_OVERLAP", "100", quote_mode="never")

print("✅ Updated .env:")
print("   MAX_CHUNK_SIZE=500 chars (~200 tokens)")
print("   MIN_CHUNK_SIZE=250 chars (~100 tokens)")
print("   CHUNK_OVERLAP=100 chars")
print("\n💡 This should work for ALL WatsonX models with 512-token limits")
