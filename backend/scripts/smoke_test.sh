#!/bin/bash
# Smoke Test Script for AIDP Render API
# Tests the complete workflow: upload → render → poll → download

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
TEST_ASSET="${TEST_ASSET:-../test-assets/cube.gltf}"
PRESET="${PRESET:-studio}"
MAX_POLLS=90
POLL_INTERVAL=2

echo "=== AIDP Render API Smoke Test ==="
echo "Base URL: $BASE_URL"
echo "Test Asset: $TEST_ASSET"
echo "Preset: $PRESET"
echo ""

# Check if test asset exists
if [ ! -f "$TEST_ASSET" ]; then
    echo "ERROR: Test asset not found: $TEST_ASSET"
    exit 1
fi

# Step 1: Health Check
echo "Step 1: Health Check..."
HEALTH=$(curl -s "$BASE_URL/health")
echo "Response: $HEALTH"
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    echo "✓ Health check passed"
else
    echo "✗ Health check failed"
    exit 1
fi
echo ""

# Step 2: Upload Asset
echo "Step 2: Uploading asset..."
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/upload" \
    -F "file=@$TEST_ASSET")
echo "Response: $UPLOAD_RESPONSE"

JOB_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"jobId":"[^"]*"' | cut -d'"' -f4)
if [ -z "$JOB_ID" ]; then
    echo "✗ Upload failed - no job ID returned"
    exit 1
fi
echo "✓ Upload successful - Job ID: $JOB_ID"
echo ""

# Step 3: Submit Render
echo "Step 3: Submitting render job with preset '$PRESET'..."
RENDER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/render" \
    -H "Content-Type: application/json" \
    -d "{\"jobId\": \"$JOB_ID\", \"preset\": \"$PRESET\"}")
echo "Response: $RENDER_RESPONSE"

if echo "$RENDER_RESPONSE" | grep -q '"status":"queued"'; then
    echo "✓ Render job submitted"
else
    echo "✗ Render submission failed"
    exit 1
fi
echo ""

# Step 4: Poll Status
echo "Step 4: Polling status (max ${MAX_POLLS}s)..."
FINAL_STATUS=""
for i in $(seq 1 $MAX_POLLS); do
    STATUS_RESPONSE=$(curl -s "$BASE_URL/api/status/$JOB_ID")
    STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

    echo "  Poll $i: status=$STATUS"

    if [ "$STATUS" = "rendering_complete" ] || [ "$STATUS" = "complete" ]; then
        FINAL_STATUS="$STATUS"
        echo "✓ Render completed"
        break
    elif [ "$STATUS" = "failed" ]; then
        echo "✗ Render failed"
        echo "$STATUS_RESPONSE"
        exit 1
    fi

    sleep $POLL_INTERVAL
done

if [ -z "$FINAL_STATUS" ]; then
    echo "✗ Render did not complete within timeout"
    exit 1
fi
echo ""

# Step 5: Download Result
echo "Step 5: Downloading render result..."
OUTPUT_FILE="smoke_test_render_${JOB_ID}.png"
HTTP_CODE=$(curl -s -w "%{http_code}" -o "$OUTPUT_FILE" "$BASE_URL/api/download/$JOB_ID")

if [ "$HTTP_CODE" = "200" ]; then
    FILE_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null)
    echo "✓ Download successful - $OUTPUT_FILE ($FILE_SIZE bytes)"

    # Verify file is valid PNG
    if file "$OUTPUT_FILE" | grep -q "PNG image"; then
        echo "✓ File is valid PNG"
    else
        echo "✗ File is not a valid PNG"
        exit 1
    fi
else
    echo "✗ Download failed with HTTP $HTTP_CODE"
    rm -f "$OUTPUT_FILE"
    exit 1
fi
echo ""

# Cleanup
rm -f "$OUTPUT_FILE"

echo "=== Smoke Test PASSED ==="
echo "All steps completed successfully!"
