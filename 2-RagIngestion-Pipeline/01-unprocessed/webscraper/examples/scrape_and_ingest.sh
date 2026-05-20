#!/bin/bash
#
# Complete workflow: Scrape documentation → Preprocess → Ingest to JADE RAG
#
# Usage:
#   ./scrape_and_ingest.sh kubernetes 100
#   ./scrape_and_ingest.sh terraform 50
#

set -e  # Exit on error

SITE=${1:-kubernetes}
MAX_PAGES=${2:-100}

# Centralized paths - all within GP-OPENSEARCH
GP_ROOT="/home/jimmie/linkops-industries/GP-copilot"
OPENSEARCH_ROOT="$GP_ROOT/GP-OPENSEARCH"
SCRAPER_DIR="$OPENSEARCH_ROOT/01-unprocessed/webscraper"
OUTPUT_DIR="$OPENSEARCH_ROOT/01-unprocessed/night-learning/scraped-docs"
PREPROCESS_SCRIPT="$OPENSEARCH_ROOT/03-preprocessed/preprocess_pipeline.py"
INGEST_SCRIPT="$OPENSEARCH_ROOT/04-ingesting/ingest_to_chromadb.py"
CHROMA_DIR="$OPENSEARCH_ROOT/05-ragged-data/chroma"

echo "=================================================="
echo "Documentation Scraping & Ingestion Workflow"
echo "=================================================="
echo "Site: $SITE"
echo "Max Pages: $MAX_PAGES"
echo "Output: $OUTPUT_DIR"
echo ""

# Step 1: Scrape documentation (output goes directly to night-learning)
echo "📡 Step 1: Scraping $SITE documentation..."
cd "$SCRAPER_DIR"
python3 doc_scraper.py --site "$SITE" --max-pages "$MAX_PAGES" --output-format jsonl

# Find the most recent output file
LATEST_FILE=$(ls -t "$OUTPUT_DIR"/${SITE}_docs_*.jsonl 2>/dev/null | head -1)

if [ -z "$LATEST_FILE" ]; then
    echo "❌ No output file found in $OUTPUT_DIR!"
    exit 1
fi

echo "✅ Scraped: $LATEST_FILE"
echo ""

# Step 2: Run preprocessing pipeline
echo "🔄 Step 2: Running preprocessing pipeline..."
cd "$GP_ROOT"
python3 "$PREPROCESS_SCRIPT" --verbose --category night-learning

echo ""

# Step 3: Run ingestion pipeline
echo "📦 Step 3: Running ingestion to ChromaDB..."
python3 "$INGEST_SCRIPT"

echo ""
echo "=================================================="
echo "✅ Complete! Documentation ingested into JADE RAG"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Test JADE knowledge:"
echo "   jade chat \"what is a $SITE pod?\""
echo ""
echo "2. Verify in ChromaDB:"
echo "   python3 -c 'import chromadb; client = chromadb.PersistentClient(path=\"$CHROMA_DIR\"); print(f\"Total docs: {sum(c.count() for c in [client.get_collection(n) for n in client.list_collections()])}\")'"
