#!/bin/bash
#
# Upload specimen data and images to S3
#
# Usage:
#   ./upload-data-to-s3.sh [stage] [data-dir] [image-dir]
#
# Example:
#   ./upload-data-to-s3.sh prod docs/data/aafc/herbarium/latest docs/data/aafc/herbarium/images
#

set -e

STAGE=${1:-prod}
DATA_DIR=${2:-docs/data/aafc/herbarium/latest}
IMAGE_DIR=${3:-docs/data/aafc/herbarium/images}
STACK_NAME="herbarium-mobile-api-${STAGE}"
REGION=${AWS_REGION:-us-east-1}

echo "========================================"
echo "Upload Data to S3"
echo "========================================"
echo "Stage: $STAGE"
echo "Data dir: $DATA_DIR"
echo "Image dir: $IMAGE_DIR"
echo "========================================"

# Get S3 bucket from stack outputs
echo "Getting S3 bucket name..."
S3_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`DataBucketName`].OutputValue' \
    --output text)

if [ -z "$S3_BUCKET" ]; then
    echo "❌ Could not find S3 bucket. Is the stack deployed?"
    echo "   Run: ./deploy-aws.sh $STAGE"
    exit 1
fi

echo "S3 Bucket: $S3_BUCKET"

# Upload extraction data
echo ""
echo "Uploading extraction data..."
if [ -f "$DATA_DIR/raw.jsonl" ]; then
    aws s3 cp "$DATA_DIR/raw.jsonl" "s3://$S3_BUCKET/data/raw.jsonl"
    echo "✅ Uploaded raw.jsonl"
else
    echo "⚠️  Warning: $DATA_DIR/raw.jsonl not found"
fi

# Upload images
echo ""
echo "Uploading specimen images..."
if [ -d "$IMAGE_DIR" ]; then
    # Count images
    IMAGE_COUNT=$(find "$IMAGE_DIR" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" \) | wc -l)
    echo "Found $IMAGE_COUNT images"

    # Upload with progress
    aws s3 sync "$IMAGE_DIR" "s3://$S3_BUCKET/images/" \
        --exclude "*" \
        --include "*.jpg" \
        --include "*.jpeg" \
        --include "*.png" \
        --include "*.tif" \
        --include "*.tiff"

    echo "✅ Uploaded images"
else
    echo "⚠️  Warning: $IMAGE_DIR not found"
fi

echo ""
echo "========================================"
echo "Upload complete! 🎉"
echo "========================================"
echo ""
echo "S3 Bucket contents:"
aws s3 ls "s3://$S3_BUCKET/" --recursive --human-readable --summarize

echo ""
echo "Your mobile app is ready at:"
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' \
    --output text)
echo "$API_ENDPOINT/"
