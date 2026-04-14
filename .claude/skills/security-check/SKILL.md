---
name: security-check
description: Security check for git operations. MUST run this skill before every `git push` to scan for leaked API keys, tokens, passwords, and sensitive data. Triggers automatically when pushing code to remote repositories.
---

# Security Check

Scan staged/committed changes for sensitive data before pushing to remote.

## Pre-Push Checklist

Before ANY `git push`, scan the diff for:

1. **API Keys & Tokens**
   - `pat-`, `sk-`, `pk-`, `api_`, `token`, `Bearer`
   - HubSpot: `pat-na1-`, `pat-eu1-`
   - Stripe: `sk_live_`, `pk_live_`, `sk_test_`
   - OpenAI: `sk-`
   - AWS: `AKIA`, `aws_secret`
   - Google: `AIza`

2. **Credentials**
   - Passwords in config files
   - `.env` file contents
   - `client_secret`, `private_key`
   - Database connection strings

3. **Sensitive Files**
   - `.env`, `.env.local`, `.env.production`
   - `credentials.json`, `service-account.json`
   - `*.pem`, `*.key`, `id_rsa`

## Scan Commands

```bash
# Check diff for sensitive patterns
git diff origin/HEAD..HEAD | grep -iE "(api_key|token|secret|password|pat-|sk-|pk-|Bearer|AKIA|AIza)"

# Check staged files
git diff --cached | grep -iE "(api_key|token|secret|password|pat-|sk-|pk-|Bearer)"

# Check specific commit
git show <commit> | grep -iE "(pat-|sk-|secret|token|password)"
```

## Response Protocol

**If sensitive data found:**
1. STOP - Do not push
2. Report findings to user
3. Suggest fix: remove hardcoded value, use env var
4. After fix: reset history if already committed (soft reset + recommit)

**If clean:**
- Confirm "✅ Security check passed - no sensitive data detected"
- Proceed with push

## Quick Patterns

| Type | Pattern |
|------|---------|
| HubSpot | `pat-na1-`, `pat-eu1-` |
| Stripe | `sk_live_`, `sk_test_`, `pk_` |
| OpenAI | `sk-` |
| AWS | `AKIA`, `aws_secret_access_key` |
| Google | `AIza` |
| Generic | `api_key=`, `token=`, `password=` |
