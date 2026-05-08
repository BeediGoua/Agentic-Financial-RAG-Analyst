#!/bin/bash
# Quick start script for Phase 1 Ingestion

set -e

echo "========================================"
echo "🚀 Agentic Financial RAG - Phase 1"
echo "========================================"
echo ""

# Check Python environment
if ! command -v python &> /dev/null; then
    echo "❌ Python not found"
    exit 1
fi

echo "✅ Python: $(python --version)"
echo ""

# Run simple ingestion (no LLM required)
echo "Starting ingestion..."
echo ""

python simple_ingest.py \
  --companies "CIE CI" \
  --years "2024" \
  --limit 2 \
  --max-pages 2

echo ""
echo "========================================"
echo "✅ Ingestion complete!"
echo "📁 Check results:"
echo "   - PDFs: data/raw/BRVM/"
echo "   - Logs: data/logs/"
echo "========================================"
