#!/bin/bash
set -e

# =============================================================================
# RAG Modulo Setup Script for Jules
# =============================================================================
# This script sets up RAG Modulo in Jules environment where Docker is not
# available. It only installs dependencies and does NOT start services.
#
# Infrastructure (Postgres, Milvus, MinIO) must run remotely.
# See: /app/JULES_SETUP.md for detailed setup instructions.
# =============================================================================

echo "🚀 Setting up RAG Modulo for Jules environment..."
echo ""

cd /app

# Check if .env exists, if not copy from template
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp env.jules.example .env
    echo "✅ .env created"
else
    echo "ℹ️  .env already exists, skipping..."
fi

echo ""
echo "📦 Installing dependencies (this may take a few minutes)..."
echo ""

# Run the dependency installation (Poetry + npm)
make local-dev-setup

echo ""
echo "✅ RAG Modulo setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1️⃣  Set up remote infrastructure services"
echo "   See: /app/JULES_SETUP.md for provider recommendations"
echo "   Quick option: Supabase + Pinecone + Backblaze B2 (all free tier)"
echo ""
echo "2️⃣  Configure .env with your remote service connection details"
echo "   Edit: nano /app/.env"
echo "   Required:"
echo "   - POSTGRES_HOST, POSTGRES_PORT, COLLECTIONDB_USER, COLLECTIONDB_PASS"
echo "   - PINECONE_API_KEY (or MILVUS_HOST/MILVUS_PORT)"
echo "   - MINIO_ENDPOINT, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD"
echo "   - WATSONX_APIKEY, WATSONX_INSTANCE_ID"
echo ""
echo "3️⃣  Verify remote connections"
echo "   Run: make verify-remote-connections"
echo ""
echo "4️⃣  Start services"
echo "   Backend:  make local-dev-backend"
echo "   Frontend: make local-dev-frontend (if supported)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 DOCUMENTATION:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Quick Start:     /app/JULES_SETUP.md"
echo "Full Guide:      /app/docs/deployment/jules-setup.md"
echo "API Docs:        http://localhost:8000/docs (after starting backend)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
