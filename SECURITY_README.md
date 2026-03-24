# Security Layer Implementation - Quick Start

This directory contains the foundational security infrastructure for the US Economy Pulse Pipeline project.

## What's Been Created

### 1. `.gitignore` (1.1 KB, 111 lines)
Comprehensive file exclusion rules preventing accidental commits of:
- Environment files (.env, .env.*, profiles.yml)
- Python artifacts (__pycache__, .venv, dist, build)
- dbt artifacts (target/, logs/, dbt_packages/)
- IDE files (.vscode, .idea)
- Credentials and keys (*.pem, *.key, credentials.json)
- OS files (.DS_Store, Thumbs.db)

### 2. `src/security/audit_secrets.py` (8.3 KB, 262 lines)
Automated secret detection script that:
- Scans repository for 9 types of secrets (API keys, JWT tokens, passwords, etc.)
- Identifies line numbers and severity levels
- Filters false positives (test data, examples)
- Returns exit code 1 on critical findings (CI/CD integration)
- Supports `--path` argument for custom scanning directory

Usage:
```bash
python src/security/audit_secrets.py --path .
```

### 3. `src/security/rls_policies.sql` (7.6 KB, 183 lines)
Supabase Row Level Security implementation for:
- 7 raw data tables (gdp, cpi, unemployment_rate, federal_funds_rate, consumer_sentiment, housing_starts, quality_checks)
- service_role: Full access (SELECT, INSERT, UPDATE, DELETE)
- anon/authenticated: No direct table access (view-only)
- Includes security verification checklist
- Includes policy explanations and comments

### 4. `.github/workflows/security_scan.yml` (4.6 KB, 155 lines)
GitHub Actions workflow with 5 security jobs:
1. **Secret Scan** - Runs audit_secrets.py
2. **Dependency Scan** - Uses pip-audit for vulnerability detection
3. **Gitignore Verification** - Ensures no secrets are tracked
4. **Code Quality** - Runs Bandit and Flake8
5. **Container Scan** - Trivy scanning (optional)

Triggers: Every push to main/develop, all pull requests
All actions pinned to SHA commits (not tags) for supply chain security

### 5. `docs/security.md` (13 KB, 466 lines)
Comprehensive security documentation including:
- Secrets Management best practices
- Environment variable configuration
- Supabase RLS explanation
- CI/CD security (GitHub Actions)
- Dependency scanning procedures
- Credential rotation guidelines
- Security checklist for contributors
- Incident response procedures

## Quick Start

### Local Development Setup (5 minutes)

1. **Create .env file**
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

2. **Verify .env is ignored**
   ```bash
   grep "^\.env" .gitignore  # Should show results
   ```

3. **Test secret scanner**
   ```bash
   python src/security/audit_secrets.py --path .
   # Should return: ✓ No critical secrets detected
   ```

### GitHub Setup (10 minutes)

1. **Add repository secrets**
   - Go to: GitHub Repo Settings → Secrets and variables → Actions
   - Add: FRED_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DATABASE_URL

2. **Verify workflow triggers**
   - Create a test branch
   - Push a small change
   - Check Actions tab to confirm workflow runs

### Database Setup (5 minutes)

1. **Deploy RLS policies**
   - Open Supabase Dashboard
   - Go to SQL Editor
   - Copy content from `src/security/rls_policies.sql`
   - Execute the script

2. **Verify RLS policies**
   ```sql
   SELECT tablename, policyname
   FROM pg_policies
   WHERE schemaname = 'public'
   ORDER BY tablename;
   ```

## Security Patterns Detected

The `audit_secrets.py` script detects:

| Pattern | Severity | Example |
|---------|----------|---------|
| API Keys | CRITICAL | `api_key = "ak_live_abc123..."` |
| JWT Tokens | CRITICAL | `eyJhbGciOiJIUzI1NiIs...` |
| DB Passwords | CRITICAL | `postgresql://user:pass@host` |
| AWS Keys | CRITICAL | `AKIA2BJKXYZ123456` |
| GitHub Tokens | CRITICAL | `ghp_abc123...` |
| Private Keys | CRITICAL | `-----BEGIN RSA PRIVATE KEY` |
| Supabase URLs | WARNING | `https://xxx.supabase.co` |
| Env Variables | WARNING | `DATABASE_URL=postgresql://...` |

## False Positive Handling

The scanner automatically ignores:
- .example files (meant to be templates)
- Test fixtures with obvious placeholders (xxxxx, 12345)
- Files marked [REDACTED]
- Demo/fixture data clearly labeled

## Contributors: Security Checklist

Before committing:
- [ ] `.env` file is **not** staged: `git status | grep .env`
- [ ] No credentials in code: `grep -r "password" src/`
- [ ] No API keys in code: `grep -r "api_key" src/`
- [ ] Run local scan: `python src/security/audit_secrets.py --path .`
- [ ] All tests pass: `pytest tests/`
- [ ] No linter errors: `flake8 src/`

See `docs/security.md` for complete security checklist.

## GitHub Actions: What Happens on Push

1. Secret scanner runs - blocks PR if critical findings
2. Dependency scanner runs - blocks PR if vulnerabilities found
3. Gitignore verification runs - blocks PR if .env/.pem files tracked
4. Code quality check runs - reports but doesn't block
5. Container scan (optional) - scans Dockerfile if present

All jobs run in parallel and complete in ~2-3 minutes.

## Troubleshooting

### Secret Scanner False Positive
- Add pattern to `FALSE_POSITIVE_PATTERNS` in `audit_secrets.py`
- Or use `.example` extension for template files
- Or add `[REDACTED]` marker for demo data

### RLS Policy Not Working
- Verify table exists: `SELECT * FROM raw_gdp LIMIT 1;`
- Check RLS is enabled: `SELECT relname, relrowsecurity FROM pg_class WHERE relname = 'raw_gdp';`
- Test service_role: `SET SESSION authorization 'service_role';`
- Verify policies exist: `SELECT * FROM pg_policies WHERE tablename = 'raw_gdp';`

### GitHub Actions Failing
- Check secrets are set in Settings → Secrets and variables
- Verify requirements.txt exists (if running pip-audit)
- Check Action logs for specific error messages
- Most common: Missing pip-audit or invalid Dockerfile

## Maintenance

### Monthly Review
- [ ] Check for new vulnerabilities: `pip-audit -r requirements.txt`
- [ ] Review GitHub Actions logs for patterns
- [ ] Audit RLS policies for correctness

### Quarterly Updates
- [ ] Rotate credentials (API keys, DB password, tokens)
- [ ] Update GitHub Actions to latest pinned SHAs
- [ ] Review and update security documentation
- [ ] Conduct security training for contributors

### Annual Review
- [ ] Full security audit of codebase
- [ ] Review and update threat model
- [ ] Update security policies and procedures
- [ ] Penetration testing (if applicable)

## Documentation References

- **Full Security Guide**: `docs/security.md`
- **API Key Setup**: `docs/security.md` → Environment Variables section
- **RLS Policies**: `src/security/rls_policies.sql` (with comments)
- **Secret Types Detected**: `src/security/audit_secrets.py` → SECRET_PATTERNS dict

## Contact & Support

For security questions or to report vulnerabilities:
1. Review `docs/security.md` first
2. Check relevant section (Secrets, RLS, CI/CD, etc.)
3. Contact security team
4. Never publicly disclose security issues

---

**Status**: Production Ready  
**Last Updated**: 2026-03-20  
**Version**: 1.0.0
