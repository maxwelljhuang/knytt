# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Knytt, please report it by emailing **[your-security-email@example.com]**.

Please **do not** open a public issue for security vulnerabilities.

### What to Include in Your Report

- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Suggested fix (if any)

We will acknowledge your email within 48 hours and provide a detailed response within 7 days.

---

## Security Best Practices for Deployment

### Environment Variables & Secrets

#### ✅ DO:
- Generate new secrets for production using `openssl rand -hex 32`
- Store secrets in Railway/Vercel environment variables
- Use Railway's secret reference syntax: `${{Service.VARIABLE}}`
- Rotate secrets regularly (at least every 90 days)
- Use different secrets for each environment (dev, staging, prod)

#### ❌ DON'T:
- Commit `.env.production` or any file containing secrets to Git
- Hardcode secrets in source code
- Share secrets via email, Slack, or other insecure channels
- Reuse secrets across multiple services
- Use default or example secrets in production

### Required Secret Generation

Before deploying to production, generate these secrets:

```bash
# Run the secret generation script
./scripts/generate_secrets.sh

# Or manually generate:
openssl rand -hex 32  # For JWT_SECRET_KEY
openssl rand -hex 32  # For SECRET_KEY
openssl rand -base64 32  # For DB passwords (if needed)
```

---

## Production Security Checklist

### Application Configuration

- [ ] `DEBUG=false` in production
- [ ] `APP_ENV=production`
- [ ] `LOG_LEVEL=INFO` or `WARNING` (not `DEBUG`)
- [ ] Strong, unique `JWT_SECRET_KEY` generated
- [ ] Strong, unique `SECRET_KEY` generated
- [ ] CORS configured with specific origins (not `*`)
- [ ] Rate limiting enabled: `RATE_LIMIT_ENABLED=true`

### Database Security

- [ ] Strong database password (if self-managed)
- [ ] Database not publicly accessible (use Railway's private networking)
- [ ] SSL/TLS enabled for database connections
- [ ] Regular automated backups configured
- [ ] Backup encryption enabled (if using S3)
- [ ] Database audit logging enabled

### API Security

- [ ] HTTPS/TLS enabled (automatic on Railway)
- [ ] CORS properly configured (specific origins only)
- [ ] Rate limiting implemented
- [ ] Input validation on all endpoints
- [ ] SQL injection protection (using SQLAlchemy ORM)
- [ ] Authentication required for sensitive endpoints
- [ ] JWT tokens with reasonable expiration times

### Frontend Security

- [ ] HTTPS/TLS enabled (automatic on Vercel)
- [ ] No sensitive data in client-side code
- [ ] Environment variables prefixed with `NEXT_PUBLIC_` only for truly public data
- [ ] XSS protection (React handles this by default)
- [ ] CSRF protection implemented where needed
- [ ] Content Security Policy headers configured

### Infrastructure Security

- [ ] Services in private network (Railway default)
- [ ] Minimal public exposure
- [ ] Regular security updates applied
- [ ] Monitoring and alerting configured
- [ ] Access logs enabled and monitored

---

## Security Features Already Implemented

### Backend

✅ **Authentication & Authorization**
- JWT-based authentication
- Password hashing with industry-standard algorithms
- Token expiration and refresh mechanisms
- User session management

✅ **Input Validation**
- Pydantic models for request validation
- Type checking at runtime
- SQL injection prevention via SQLAlchemy ORM

✅ **API Security**
- CORS middleware configured
- Request rate limiting support
- GZip compression for responses
- Request logging and monitoring

### Frontend

✅ **React Security**
- XSS protection (automatic escaping)
- Safe rendering of user content
- Secure cookie handling
- HTTPS-only communication in production

✅ **Authentication Flow**
- Secure token storage
- Automatic token refresh
- Protected routes
- Session timeout handling

---

## Common Security Vulnerabilities & Mitigations

### SQL Injection

**Mitigation**: ✅ Implemented
- Using SQLAlchemy ORM (not raw SQL)
- Parameterized queries
- Input validation with Pydantic

### Cross-Site Scripting (XSS)

**Mitigation**: ✅ Implemented
- React automatic escaping
- Content Security Policy headers (configure in production)
- Input sanitization

### Cross-Site Request Forgery (CSRF)

**Mitigation**: ⚠️ Partial
- JWT tokens in headers (not cookies)
- SameSite cookie attributes
- **TODO**: Implement CSRF tokens for state-changing operations

### Authentication Bypass

**Mitigation**: ✅ Implemented
- Strong JWT secret keys
- Token expiration
- Secure password hashing
- Protected API routes

### Sensitive Data Exposure

**Mitigation**: ✅ Implemented
- No sensitive data in logs
- Environment variables for secrets
- HTTPS/TLS encryption
- Secure error messages (no stack traces in production)

### Broken Access Control

**Mitigation**: ✅ Implemented
- User ID verification on protected routes
- Resource ownership checks
- Role-based access control

### Using Components with Known Vulnerabilities

**Mitigation**: ⚠️ Ongoing
- Regular dependency updates
- GitHub Dependabot alerts enabled
- **TODO**: Implement automated dependency scanning

---

## Secure Coding Guidelines

### Password Handling

```python
# ✅ Good
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"])
hashed = pwd_context.hash(password)

# ❌ Bad
import hashlib
hashed = hashlib.md5(password.encode()).hexdigest()
```

### Environment Variables

```python
# ✅ Good
from os import getenv
SECRET_KEY = getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY not set")

# ❌ Bad
SECRET_KEY = "hardcoded-secret-key"
```

### Database Queries

```python
# ✅ Good (SQLAlchemy ORM)
user = db.query(User).filter(User.email == email).first()

# ❌ Bad (SQL injection risk)
query = f"SELECT * FROM users WHERE email = '{email}'"
db.execute(query)
```

### CORS Configuration

```python
# ✅ Good (specific origins)
CORS_ORIGINS = [
    "https://your-app.vercel.app",
    "https://your-domain.com"
]

# ❌ Bad (allows all origins)
CORS_ORIGINS = ["*"]
```

---

## Security Monitoring

### Error Tracking

Configure Sentry for production:

```bash
# Railway environment variables
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ENVIRONMENT=production
```

### Logging

**What to Log:**
- Authentication attempts (success and failure)
- Authorization failures
- Input validation failures
- Database errors
- API errors

**What NOT to Log:**
- Passwords or password hashes
- JWT tokens
- Credit card numbers
- API keys or secrets
- Personal Identifiable Information (PII)

### Monitoring Alerts

Set up alerts for:
- High error rates (> 1%)
- Failed authentication attempts (> 10 per minute)
- Unusual traffic patterns
- Database connection failures
- API response time degradation

---

## Incident Response

### If a Security Breach Occurs:

1. **Immediately**:
   - Identify and contain the breach
   - Rotate all compromised credentials
   - Block malicious IP addresses

2. **Within 24 hours**:
   - Assess the impact and scope
   - Notify affected users
   - Document the incident

3. **Within 1 week**:
   - Implement fixes
   - Conduct security audit
   - Update security policies
   - Post-mortem analysis

### Credential Rotation

If secrets are compromised:

```bash
# Generate new secrets
./scripts/generate_secrets.sh

# Update Railway environment variables
railway variables set JWT_SECRET_KEY=<new-secret>
railway variables set SECRET_KEY=<new-secret>

# Redeploy all services
railway up
```

---

## Compliance Considerations

### Data Privacy (GDPR, CCPA)

- [ ] Privacy policy implemented
- [ ] User consent mechanisms
- [ ] Data deletion capabilities
- [ ] Data export functionality
- [ ] Cookie consent banner

### Payment Card Industry (PCI DSS)

⚠️ **Note**: If implementing payment processing:
- Use PCI-compliant payment gateway (Stripe, PayPal)
- Never store credit card numbers
- Use tokenization for payment methods
- Implement strong encryption

### Accessibility (WCAG)

- [ ] Screen reader support
- [ ] Keyboard navigation
- [ ] Color contrast compliance
- [ ] Alt text for images

---

## Security Updates & Maintenance

### Weekly

- [ ] Review security logs in Sentry
- [ ] Check for failed authentication attempts
- [ ] Monitor API error rates

### Monthly

- [ ] Review and update dependencies
- [ ] Check for security advisories
- [ ] Audit user access permissions
- [ ] Review API usage patterns

### Quarterly

- [ ] Rotate secrets and credentials
- [ ] Security audit of new features
- [ ] Penetration testing (if budget allows)
- [ ] Review and update security policies

### Annually

- [ ] Comprehensive security audit
- [ ] Third-party security assessment
- [ ] Update disaster recovery plan
- [ ] Security training for team

---

## Resources

### Security Tools

- **Dependency Scanning**: GitHub Dependabot, Snyk
- **SAST**: Bandit (Python), ESLint (JavaScript)
- **DAST**: OWASP ZAP, Burp Suite
- **Secrets Scanning**: GitGuardian, TruffleHog

### Security References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Next.js Security](https://nextjs.org/docs/app/building-your-application/configuring/content-security-policy)
- [Railway Security](https://docs.railway.app/reference/security)
- [Vercel Security](https://vercel.com/docs/security)

---

## Contact

For security concerns or questions:
- **Security Email**: [your-security-email@example.com]
- **General Contact**: [your-email@example.com]

**Last Updated**: 2025-11-05
**Version**: 1.0
