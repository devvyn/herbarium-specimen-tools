# AWS Lambda Deployment Guide

Deploy the Herbarium Mobile API to AWS Lambda for **serverless, pay-per-request** operation.

## Why AWS Lambda?

- **~$0/month** for single-user usage (1M requests/month FREE)
- Only charged when API is actually used (no idle costs)
- Auto-scales automatically
- No server maintenance
- Works with existing AWS credentials

## Cost Estimate

**Free tier (first 12 months):**
- Lambda: 1M requests/month FREE
- API Gateway: 1M requests/month FREE
- S3: 5GB storage FREE

**After free tier:**
- Lambda: $0.20 per 1M requests
- API Gateway: $1.00 per 1M requests
- S3: $0.023/GB/month

**Expected monthly cost for single user:** **$0-2**

## Prerequisites

1. **AWS Account** with billing configured
2. **AWS CLI** installed and configured
3. **AWS SAM CLI** installed
4. **Python 3.11**

### Install AWS CLI

```bash
# macOS
brew install awscli

# Linux/WSL
pip install awscli

# Configure credentials
aws configure
# Enter: AWS Access Key ID, Secret Access Key, Region (e.g., us-east-1)
```

### Install AWS SAM CLI

```bash
# macOS
brew install aws-sam-cli

# Linux/WSL
pip install aws-sam-cli

# Verify
sam --version
```

## Deployment Steps

### 1. Deploy Infrastructure

```bash
cd mobile

# Make scripts executable
chmod +x deploy-aws.sh upload-data-to-s3.sh

# Deploy (one command!)
./deploy-aws.sh prod
```

This will:
- Create S3 bucket for data/images
- Deploy Lambda function
- Create API Gateway
- Set up IAM permissions
- Output your API URL

**Deployment takes ~2-3 minutes.**

### 2. Upload Data to S3

```bash
# Upload extraction data and images
./upload-data-to-s3.sh prod \
  ../docs/data/aafc/herbarium/latest \
  ../docs/data/aafc/herbarium/images
```

Or manually:
```bash
# Get bucket name from deployment output
BUCKET="herbarium-specimens-ACCOUNT_ID-prod"

# Upload extraction data
aws s3 cp ../docs/data/aafc/herbarium/latest/raw.jsonl \
  s3://$BUCKET/data/raw.jsonl

# Upload images
aws s3 sync ../docs/data/aafc/herbarium/images/ \
  s3://$BUCKET/images/
```

### 3. Access Mobile App

Your API URL will be shown in deployment output:
```
https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/
```

**On iPhone:**
1. Open Safari
2. Navigate to the URL above
3. Login: `curator` / `changeme123`
4. Tap Share → "Add to Home Screen"

Done! ✅

## Architecture

```
┌─────────────────────────────────────────┐
│  iPhone Safari                          │
│  Progressive Web App                    │
└──────────────┬──────────────────────────┘
               │ HTTPS
┌──────────────▼──────────────────────────┐
│  Amazon API Gateway                     │
│  - HTTPS endpoint                       │
│  - Authentication                       │
│  - CORS handling                        │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  AWS Lambda                             │
│  - FastAPI app (Mangum adapter)         │
│  - ReviewEngine                         │
│  - Runs only when called                │
│  - Auto-scales                          │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Amazon S3                              │
│  - Extraction data (raw.jsonl)          │
│  - Specimen images                      │
│  - Served via signed URLs               │
└─────────────────────────────────────────┘
```

## How It Works

### Cold Start Behavior

**First request after idle (~15 min):**
- Lambda downloads extraction data from S3
- Initializes FastAPI app
- Response time: 2-5 seconds

**Subsequent requests (while warm):**
- Lambda container reused
- Response time: 100-500ms

**Warmth duration:** ~15 minutes of inactivity

### Image Serving

Images are served directly from S3 via **signed URLs**:
1. Client requests image
2. Lambda generates temporary S3 URL (valid 1 hour)
3. Client redirected to S3
4. Image downloaded from S3 (not through Lambda)

**Advantages:**
- No Lambda bandwidth costs
- Fast image loading
- CDN-compatible (optional CloudFront)

## Management

### View Logs

```bash
# Live logs
sam logs --stack-name herbarium-mobile-api-prod --tail

# Last 10 minutes
sam logs --stack-name herbarium-mobile-api-prod --start-time '10m ago'
```

Or in AWS Console:
- CloudWatch → Log Groups → `/aws/lambda/herbarium-mobile-api-prod`

### Update Deployment

After code changes:
```bash
# Redeploy
./deploy-aws.sh prod

# Data persists in S3 (not redeployed)
```

### Delete Stack

```bash
# Delete everything (including S3 bucket)
aws cloudformation delete-stack --stack-name herbarium-mobile-api-prod

# Wait for deletion
aws cloudformation wait stack-delete-complete \
  --stack-name herbarium-mobile-api-prod
```

## Environment Stages

Deploy to multiple environments:

```bash
# Development
./deploy-aws.sh dev

# Staging
./deploy-aws.sh staging

# Production
./deploy-aws.sh prod
```

Each stage gets separate:
- Lambda function
- API Gateway
- S3 bucket
- URL

## Security

### Change Default Password

**Option 1: Environment variable**
```bash
# Update template.yaml
Environment:
  Variables:
    DEFAULT_PASSWORD: your-secure-password
```

**Option 2: AWS Secrets Manager**
```yaml
# template.yaml
Resources:
  HerbariumAPIFunction:
    Environment:
      Variables:
        SECRET_ARN: !Ref PasswordSecret

  PasswordSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      SecretString: !Sub '{"password":"${YourSecurePassword}"}'
```

Then in code:
```python
import boto3
secret = boto3.client('secretsmanager').get_secret_value(
    SecretId=os.environ['SECRET_ARN']
)
password = json.loads(secret['SecretString'])['password']
```

### Enable Multi-User Auth

See main [README.md](README.md) for database-backed authentication setup.

### Custom Domain

Add custom domain instead of AWS default:

```bash
# Get ACM certificate
aws acm request-certificate \
  --domain-name herbarium.your-domain.com \
  --validation-method DNS

# Add to template.yaml
HerbariumAPI:
  Type: AWS::Serverless::Api
  Properties:
    Domain:
      DomainName: herbarium.your-domain.com
      CertificateArn: arn:aws:acm:...
```

## Monitoring

### CloudWatch Metrics

View in AWS Console → CloudWatch → Metrics:
- Lambda invocations
- Error count
- Duration
- Throttles

### Cost Monitoring

View in AWS Console → Billing:
- Lambda costs
- API Gateway costs
- S3 costs
- Data transfer

**Set up billing alerts:**
```bash
aws budgets create-budget --account-id YOUR_ACCOUNT \
  --budget file://budget.json
```

## Optimization

### Reduce Cold Starts

**Option 1: Provisioned concurrency** (costs money)
```yaml
HerbariumAPIFunction:
  ProvisionedConcurrencyConfig:
    ProvisionedConcurrentExecutions: 1
```

**Option 2: Scheduled warming** (free)
```yaml
WarmingRule:
  Type: AWS::Events::Rule
  Properties:
    ScheduleExpression: rate(10 minutes)
    Targets:
      - Arn: !GetAtt HerbariumAPIFunction.Arn
```

### Enable Caching

Add API Gateway caching:
```yaml
HerbariumAPI:
  CacheClusterEnabled: true
  CacheClusterSize: '0.5'  # 0.5GB cache
```

### CloudFront CDN

Add CloudFront for global distribution:
```yaml
Distribution:
  Type: AWS::CloudFront::Distribution
  Properties:
    Origins:
      - DomainName: !GetAtt HerbariumAPI.DomainName
```

## Troubleshooting

### Deployment fails: "Stack already exists"

```bash
# Update existing stack
./deploy-aws.sh prod
```

### Lambda timeout errors

Increase timeout in `template.yaml`:
```yaml
Globals:
  Function:
    Timeout: 60  # Increase from 30 to 60 seconds
```

### Images not loading

Check S3 bucket permissions:
```bash
aws s3 ls s3://YOUR_BUCKET/images/
```

Check Lambda IAM role has S3 read permissions (should be automatic).

### Cold start too slow

- Reduce dependencies (remove unused imports)
- Use Lambda layers for large deps
- Consider provisioned concurrency

### CORS errors

Check API Gateway CORS configuration in `template.yaml`.

## Local Testing

Test Lambda handler locally:

```bash
# Install dependencies
pip install -r requirements-lambda.txt

# Set environment variables
export S3_BUCKET=your-bucket
export EXTRACTION_DATA_KEY=data/raw.jsonl

# Run locally with SAM
sam local start-api --port 8000

# Access at http://localhost:8000
```

## Cost Optimization Tips

1. **Use S3 Intelligent-Tiering** for images (auto-moves to cheaper storage)
2. **Enable S3 lifecycle policies** (delete old versions)
3. **Use CloudFront** for frequent image access (caching)
4. **Monitor usage** with CloudWatch alerts
5. **Delete unused deployments** (dev/staging)

## Comparison with Other Platforms

| Platform | Monthly Cost | Cold Start | Scaling | Setup |
|----------|--------------|------------|---------|-------|
| **AWS Lambda** | $0-2 | 2-5s | Auto | Medium |
| Heroku | $7-25 | None | Manual | Easy |
| Fly.io | $0-5 | None | Auto | Easy |
| Digital Ocean | $12+ | None | Manual | Hard |

**Lambda wins for:**
- Sporadic usage patterns
- Low monthly volume
- Existing AWS infrastructure
- Pay-per-request model

## Next Steps

After successful deployment:

1. ✅ Test mobile app on iPhone
2. ✅ Add to Home Screen
3. ✅ Review some specimens
4. 🔒 Change default password
5. 📊 Set up CloudWatch alerts
6. 💰 Enable cost monitoring
7. 🌐 Add custom domain (optional)
8. 👥 Add multi-user auth (when needed)

## Support

For AWS-specific issues:
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [Mangum Documentation](https://mangum.io/)

For app issues:
- See main [README.md](README.md)
