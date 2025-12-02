# Security Configuration Guide

## Critical Security Updates

The mobile API has been hardened with enterprise-grade security practices. **You MUST configure these settings before deploying to production.**

## Quick Setup (Development)

For local testing only:

```bash
# Set development environment
export ENVIRONMENT=development

# Run server (will use test credentials)
python mobile/run_mobile_server.py --port 8000
```

**Default development credentials:** `testuser` / `testpass123`

⚠️ **WARNING:** These credentials are ONLY for development and will NOT work in production mode.

## Production Setup

### 1. Generate JWT Secret Key

```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Save this value - you'll use it in environment variables.

### 2. Generate Password Hashes

```bash
python mobile/generate_password_hash.py
```

This will prompt you for a password and generate a bcrypt hash.

**Example output:**
```
Hashed password:
$2b$12$abc123...xyz789

Environment variable format:
AUTH_USERS=curator:$2b$12$abc123...xyz789
```

### 3. Set Environment Variables

**For local server:**

```bash
# Required
export JWT_SECRET_KEY="your-secret-from-step-1"
export AUTH_USERS="curator:$2b$12$abc123...xyz789"
export ENVIRONMENT=production

# Recommended
export ALLOWED_ORIGINS="https://your-domain.com"
export ALLOWED_HOSTS="your-domain.com"
export ACCESS_TOKEN_EXPIRE_MINUTES="1440"  # 24 hours

# Start server
python mobile/run_mobile_server.py --port 8000
```

**For AWS Lambda:**

Add to `template.yaml` or use AWS Parameter Store/Secrets Manager:

```yaml
Environment:
  Variables:
    JWT_SECRET_KEY: !Sub '{{resolve:secretsmanager:herbarium/jwt:SecretString:key}}'
    AUTH_USERS: !Sub '{{resolve:secretsmanager:herbarium/users:SecretString:users}}'
    ALLOWED_ORIGINS: 'https://your-api.execute-api.us-east-1.amazonaws.com'
    ENVIRONMENT: 'production'
```

### 4. Create AWS Secrets (Recommended)

```bash
# Create JWT secret
aws secretsmanager create-secret \
  --name herbarium/jwt \
  --secret-string "{\"key\":\"your-generated-secret\"}"

# Create user credentials
aws secretsmanager create-secret \
  --name herbarium/users \
  --secret-string "{\"users\":\"curator:$2b$12$...\"}"
```

## Security Features

### ✅ Implemented

1. **Password Hashing**
   - Bcrypt with automatic salt generation
   - Timing-attack resistant verification
   - Industry-standard security

2. **JWT Authentication**
   - Secure token-based auth
   - Configurable expiration
   - Required for all API endpoints

3. **Rate Limiting**
   - 5 login attempts per 15 minutes per IP
   - Prevents brute force attacks
   - Automatic reset on success

4. **CORS Restrictions**
   - Must specify allowed origins
   - No wildcard (*) in production
   - Credentials require exact origin match

5. **Security Headers**
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: DENY
   - X-XSS-Protection: 1; mode=block
   - Strict-Transport-Security (HSTS)

6. **Secure Defaults**
   - API docs disabled in production
   - Environment-based configuration
   - Mandatory secret key in production
   - Trusted host middleware

7. **Audit Logging**
   - Failed login attempts logged
   - Successful authentications logged
   - Rate limit violations logged

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | **Yes** (prod) | Auto-generated (dev) | Secret for JWT signing |
| `AUTH_USERS` | **Yes** (prod) | testuser:hash (dev) | Comma-separated user:hash pairs |
| `ENVIRONMENT` | **Yes** | development | `development` or `production` |
| `ALLOWED_ORIGINS` | Recommended | localhost | Comma-separated allowed CORS origins |
| `ALLOWED_HOSTS` | Recommended | None | Comma-separated trusted hostnames |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | 1440 (24h) | JWT token lifetime in minutes |

## Multi-User Configuration

**Format:** `username1:hash1,username2:hash2`

```bash
# Generate hashes for each user
python mobile/generate_password_hash.py

# Combine into environment variable
export AUTH_USERS="curator1:$2b$12$abc...,curator2:$2b$12$xyz...,admin:$2b$12$def..."
```

## Security Checklist

Before deploying to production:

- [ ] Set `ENVIRONMENT=production`
- [ ] Generate secure `JWT_SECRET_KEY` (32+ characters)
- [ ] Create strong passwords and hash them
- [ ] Configure `AUTH_USERS` with hashed passwords
- [ ] Set `ALLOWED_ORIGINS` to your domain only
- [ ] Set `ALLOWED_HOSTS` to your domain only
- [ ] Use HTTPS (required for security headers to work)
- [ ] Store secrets in AWS Secrets Manager (not env vars)
- [ ] Review CloudWatch logs regularly
- [ ] Set up billing alerts (prevent abuse)
- [ ] Test rate limiting is working
- [ ] Verify CORS restrictions
- [ ] Disable API docs in production (automatic)

## Common Security Mistakes to Avoid

❌ **Don't:**
- Use default credentials in production
- Hardcode secrets in code
- Use `ALLOWED_ORIGINS=*` in production
- Store plaintext passwords
- Skip HTTPS
- Use weak passwords (<12 characters)
- Expose API docs in production
- Ignore failed login logs

✅ **Do:**
- Use environment variables for all secrets
- Generate strong random keys
- Restrict CORS to specific domains
- Hash all passwords with bcrypt
- Enforce HTTPS everywhere
- Use 16+ character passwords
- Monitor CloudWatch logs
- Set up rate limiting alerts

## Rotating Secrets

### JWT Secret Key Rotation

```bash
# Generate new key
NEW_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

# Update in AWS Secrets Manager
aws secretsmanager update-secret \
  --secret-id herbarium/jwt \
  --secret-string "{\"key\":\"$NEW_KEY\"}"

# Redeploy Lambda
./deploy-aws.sh prod
```

**Note:** Rotating JWT key will invalidate all existing tokens. Users will need to login again.

### Password Rotation

```bash
# Generate new hash
python mobile/generate_password_hash.py

# Update AUTH_USERS with new hash
# Redeploy
```

## Incident Response

### Suspected Compromise

1. **Immediately** rotate JWT secret key
2. Review CloudWatch logs for suspicious activity
3. Check S3 bucket access logs
4. Rotate all user passwords
5. Enable MFA on AWS account
6. Review IAM permissions

### Brute Force Attack

1. Check CloudWatch logs for rate limit violations
2. Identify attacking IPs
3. Consider adding WAF rules (AWS WAF)
4. Tighten rate limits if needed
5. Consider IP allowlist for known users

## Advanced Security (Optional)

### AWS WAF Integration

Add Web Application Firewall:

```yaml
WebACL:
  Type: AWS::WAFv2::WebACL
  Properties:
    DefaultAction:
      Allow: {}
    Rules:
      - Name: RateLimitRule
        Priority: 1
        Statement:
          RateBasedStatement:
            Limit: 2000
            AggregateKeyType: IP
```

### CloudWatch Alarms

Monitor for suspicious activity:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name herbarium-failed-logins \
  --alarm-description "Alert on >10 failed logins" \
  --metric-name FailedLogins \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

### VPC Integration

For extra security, deploy Lambda in VPC:

```yaml
HerbariumAPIFunction:
  Properties:
    VpcConfig:
      SecurityGroupIds:
        - !Ref LambdaSecurityGroup
      SubnetIds:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2
```

## Testing Security

### Verify Password Hashing

```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash a test password
hashed = pwd_context.hash("testpass")
print(f"Hashed: {hashed}")

# Verify it works
assert pwd_context.verify("testpass", hashed)
print("✅ Password hashing works!")
```

### Test Rate Limiting

```bash
# Try 6 failed logins (should block on 6th)
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"fake","password":"wrong"}'
  echo ""
done
```

Expected: First 5 return 401, 6th returns 429 (Too Many Requests)

### Test CORS

```bash
# Should be rejected if origin not in ALLOWED_ORIGINS
curl -H "Origin: https://evil.com" \
  http://localhost:8000/api/v1/health
```

## Support

For security questions or to report vulnerabilities:
- Open a GitHub issue (for non-sensitive questions)
- Email: [your security contact]
- Review logs: `sam logs --stack-name herbarium-mobile-api-prod`

## References

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)
- [Passlib Documentation](https://passlib.readthedocs.io/)
