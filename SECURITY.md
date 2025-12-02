# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Best Practices

### Deployment Security

#### 1. Environment Variables
**Never** commit secrets to the repository. All sensitive configuration must use environment variables:

```bash
# Required for production
JWT_SECRET_KEY=<strong-random-secret>
AUTH_USERS=<username:hashed_password>
ALLOWED_ORIGINS=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com
```

#### 2. JWT Secret Key
Generate a strong secret key:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

**Security Requirements**:
- Minimum 32 characters
- Randomly generated (not a password)
- Never logged or exposed
- Rotate periodically (at least annually)

#### 3. Password Hashing
User passwords must be hashed with bcrypt:

```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed = pwd_context.hash("user-password")
```

**Security Requirements**:
- Use bcrypt with automatic salt
- Never store plaintext passwords
- Use timing-safe comparison
- Minimum password length: 8 characters (recommended: 12+)

#### 4. HTTPS/TLS
**Required** for production deployments:

- Use valid SSL/TLS certificates (Let's Encrypt recommended)
- Enforce HTTPS (redirect HTTP → HTTPS)
- Enable HSTS (Strict-Transport-Security header)
- Use TLS 1.2 or higher only

#### 5. CORS Configuration
Restrict origins to your domains only:

```bash
ALLOWED_ORIGINS=https://yourdomain.com,https://mobile.yourdomain.com
```

**Do NOT use**:
- `*` (wildcard - allows all origins)
- `http://` origins in production
- Development URLs in production

#### 6. Rate Limiting
Built-in rate limiting for authentication:
- 5 login attempts per 15 minutes per IP
- Automatic lockout after threshold

**Production Recommendations**:
- Use Redis for distributed rate limiting
- Monitor for brute force attacks
- Consider IP allowlisting for known locations

---

## Known Security Considerations

### 1. In-Memory Session Storage
**Current**: Rate limiting uses in-memory storage
**Limitation**: Resets on server restart
**Production Recommendation**: Use Redis for persistent session storage

### 2. Thumbnail Generation
**Current**: Full images served for thumbnails (client-side resize)
**Limitation**: Bandwidth intensive
**Production Recommendation**: Pre-generate thumbnails or use image processing service

### 3. Image Access Control
**Current**: JWT token required for image access
**Note**: Images served without additional permission checks beyond authentication
**Consideration**: Add specimen-level permissions if needed

### 4. Token Expiration
**Default**: 24 hours
**Configurable**: `ACCESS_TOKEN_EXPIRE_MINUTES` environment variable
**Recommendation**: Shorter expiration (2-8 hours) for high-security deployments

---

## Reporting a Vulnerability

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, email security reports to: **[Your security contact email]**

### What to Include

1. **Description**: Clear description of the vulnerability
2. **Impact**: Potential security impact
3. **Reproduction**: Steps to reproduce the issue
4. **Environment**: Version, Python version, deployment method
5. **Proposed Fix**: If you have suggestions

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Status Update**: Every 2 weeks until resolved
- **Fix Release**: Depends on severity
  - Critical: 1-7 days
  - High: 1-4 weeks
  - Medium: 1-3 months
  - Low: Next scheduled release

### Disclosure Policy

We follow **coordinated disclosure**:
1. Reporter notifies maintainers privately
2. Maintainers confirm and develop fix
3. Fix released and version updated
4. Public disclosure after fix available
5. Reporter credited (if desired)

---

## Security Checklist for Deployments

### Pre-Production

- [ ] JWT_SECRET_KEY generated and set (32+ characters)
- [ ] AUTH_USERS configured with bcrypt hashes
- [ ] ENVIRONMENT=production set
- [ ] HTTPS/TLS certificate configured
- [ ] ALLOWED_ORIGINS restricted to production domains
- [ ] ALLOWED_HOSTS restricted to production domains
- [ ] API docs disabled (check /docs returns 404)
- [ ] Default test credentials removed
- [ ] Firewall rules configured (only ports 80/443 open)
- [ ] System packages up to date
- [ ] Python dependencies up to date
- [ ] Database backups configured (if applicable)
- [ ] Monitoring and alerting configured
- [ ] Incident response plan documented

### Post-Deployment

- [ ] Health check endpoint responding
- [ ] Authentication working correctly
- [ ] Rate limiting functional
- [ ] HTTPS redirect working
- [ ] Security headers present (verify with securityheaders.com)
- [ ] CORS policy enforced
- [ ] No secrets in logs
- [ ] Error messages don't leak sensitive info
- [ ] Backup restoration tested

---

## Security Headers

The API automatically includes security headers:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

**Verify** with:
```bash
curl -I https://yourdomain.com/api/v1/health
```

---

## Common Vulnerabilities Addressed

### ✅ SQL Injection
**Status**: Not applicable (no SQL database in core API)
**Note**: If adding database, use parameterized queries

### ✅ XSS (Cross-Site Scripting)
**Mitigation**:
- X-XSS-Protection header enabled
- Content-Type validation
- Input sanitization in validators

### ✅ CSRF (Cross-Site Request Forgery)
**Mitigation**:
- JWT tokens required (not cookies)
- SameSite cookie policy (if cookies added)

### ✅ Authentication Bypass
**Mitigation**:
- JWT signature verification
- Token expiration enforced
- Constant-time password comparison

### ✅ Rate Limiting Bypass
**Mitigation**:
- Per-IP rate limiting
- Failed attempt tracking
- Exponential backoff

### ✅ Information Disclosure
**Mitigation**:
- Generic error messages
- API docs disabled in production
- No stack traces in responses

### ✅ Insecure Dependencies
**Mitigation**:
- Regular dependency updates
- CI/CD security scanning
- Pin dependency versions

---

## Secure Coding Guidelines

### For Contributors

#### 1. Never Commit Secrets
```bash
# Bad - commits secret
JWT_SECRET_KEY = "hardcoded-secret"

# Good - reads from environment
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
```

#### 2. Use Parameterized Queries
```python
# Bad - SQL injection risk
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# Good - parameterized
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

#### 3. Validate Input
```python
# Bad - no validation
def update_field(field_name, value):
    record[field_name] = value

# Good - validate with Pydantic
class FieldUpdate(BaseModel):
    field_name: str = Field(min_length=1, max_length=100)
    value: str = Field(max_length=1000)
```

#### 4. Handle Errors Safely
```python
# Bad - exposes internal details
except Exception as e:
    return {"error": str(e)}

# Good - generic message
except Exception as e:
    logger.error(f"Update failed: {e}")
    return {"error": "Update failed"}
```

#### 5. Use Type Hints
```python
# Good - catches errors early
def process_specimen(specimen_id: str) -> SpecimenReview:
    pass
```

---

## Security Monitoring

### What to Monitor

1. **Failed Login Attempts**
   - Sudden spikes indicate brute force
   - Pattern: Multiple IPs trying same username

2. **Rate Limit Triggers**
   - Frequent triggers indicate attack
   - Monitor via logs or metrics

3. **Error Rates**
   - Sudden increase may indicate attack
   - Check for input validation errors

4. **Unusual Traffic Patterns**
   - Off-hours access
   - Geographic anomalies
   - User agent patterns

### Recommended Tools

- **SIEM**: Splunk, ELK Stack, or cloud-native
- **IDS/IPS**: Fail2ban, CloudFlare WAF
- **Log Analysis**: Automated alert rules
- **Uptime Monitoring**: UptimeRobot, Pingdom

---

## Incident Response

### If Breach Suspected

1. **Isolate**: Take affected systems offline
2. **Investigate**: Review logs, identify scope
3. **Contain**: Change all secrets (JWT key, passwords)
4. **Notify**: Inform users if data compromised
5. **Remediate**: Fix vulnerability, test thoroughly
6. **Document**: Post-mortem analysis
7. **Monitor**: Enhanced monitoring post-incident

### Contact

For security incidents: **[Your security contact email]**

---

## Security Updates

We take security seriously. Security updates are released as soon as possible:

- **Critical**: Immediate patch release
- **High**: Within 1 week
- **Medium**: Next minor release
- **Low**: Next major release

Subscribe to releases on GitHub to receive notifications.

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)

---

**Last Updated**: 2025-12-02
**Version**: 0.1.x
