#!/bin/bash
#
# Deploy Herbarium Mobile API to AWS Lambda
#
# Prerequisites:
# - AWS CLI configured (aws configure)
# - AWS SAM CLI installed (brew install aws-sam-cli or pip install aws-sam-cli)
# - Python 3.11
#
# Usage:
#   ./deploy-aws.sh [stage]
#
# stage: dev, staging, or prod (default: prod)
#

set -e  # Exit on error

STAGE=${1:-prod}
REGION=${AWS_REGION:-us-east-1}
STACK_NAME="herbarium-mobile-api-${STAGE}"

echo "========================================"
echo "Herbarium Mobile API - AWS Deployment"
echo "========================================"
echo "Stage: $STAGE"
echo "Region: $REGION"
echo "Stack: $STACK_NAME"
echo "========================================"

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Install: pip install awscli"
    exit 1
fi

if ! command -v sam &> /dev/null; then
    echo "❌ AWS SAM CLI not found. Install: pip install aws-sam-cli"
    exit 1
fi

# Validate AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Run: aws configure"
    exit 1
fi

echo "✅ Prerequisites OK"

# Build Lambda layer for dependencies
echo ""
echo "Building Lambda dependencies layer..."
mkdir -p dependencies/python
pip install -r requirements-lambda.txt -t dependencies/python/ --upgrade
echo "✅ Dependencies built"

# Validate SAM template
echo ""
echo "Validating SAM template..."
sam validate --lint

# Build SAM application
echo ""
echo "Building SAM application..."
sam build --use-container

# Deploy
echo ""
echo "Deploying to AWS..."
sam deploy \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --parameter-overrides "Stage=$STAGE" \
    --capabilities CAPABILITY_IAM \
    --no-fail-on-empty-changeset \
    --resolve-s3

# Get outputs
echo ""
echo "========================================"
echo "Deployment complete! 🎉"
echo "========================================"

# Extract stack outputs
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' \
    --output text)

S3_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`DataBucketName`].OutputValue' \
    --output text)

echo ""
echo "📱 Mobile App URL:"
echo "   $API_ENDPOINT/"
echo ""
echo "📦 S3 Bucket:"
echo "   $S3_BUCKET"
echo ""
echo "Next steps:"
echo "1. Upload extraction data:"
echo "   aws s3 cp docs/data/aafc/herbarium/latest/raw.jsonl s3://$S3_BUCKET/data/raw.jsonl"
echo ""
echo "2. Upload specimen images:"
echo "   aws s3 sync docs/data/aafc/herbarium/images/ s3://$S3_BUCKET/images/"
echo ""
echo "3. Access mobile app on iPhone:"
echo "   $API_ENDPOINT/"
echo ""
echo "4. Default login: curator / changeme123"
echo ""
echo "========================================"
