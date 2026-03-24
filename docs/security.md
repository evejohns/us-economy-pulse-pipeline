# Security Documentation - US Economy Pulse Pipeline

## Overview

This document outlines the security architecture and practices for the US Economy Pulse Pipeline project. The project implements multiple layers of security to protect sensitive credentials, API keys, and database access.

**Key Security Measures:**
- Environment variable isolation via `.env` files
- GitHub Actions automated secret detection
- Row Level Security (RLS) on Supabase PostgreSQL
- Dependency vulnerability scanning
- Code quality and security analysis
- Comprehensive `.gitignore` to prevent accidental commits

## Table of Contents

1. [Secrets Management](#secrets-management)
2. [Environment Variables](#environment-variables)
3. [Supabase Row Level Security](#supabase-row-level-security)
4. [CI/CD Security](#cicd-security)
5. [Dependency Scanning](#dependency-scanning)
6. [Credential Rotation](#credential-rotation)
7. [Security Checklist for Contributors](#security-checklist-for-contributors)

---

## Secrets Management

### What Constitutes a Secret?

Secrets include any sensitive information that should not be exposed in version control:
- API keys (FRED API key, Supabase keys)
- Database credentials and connection strings
- JWT tokens
- AWS credentials
- GitHub tokens
- Private keys (PEM, RSA, etc.)
- Passwords

### How Secrets Are Handled

1. **Never commit secrets to Git**
   - All secrets are excluded via `.gitignore`
   - Use `.env` files locally (these are git-ignored)
   - Commit `.env.example` with placeholder values only

2. **Local Development**
   - Create a local `.env` file with your actual credentials
   - This file is automatically ignored by Git
   - Load environment variables in your application startup

3. **CI/CD Pipelines**
   - GitHub Actions uses GitHub Secrets for sensitive values
   - Secrets are never logged or echoed to GitHub Actions output
   - Workflow files reference secrets via `${{ secrets.SECRET_NAME }}`

4. **Secret Scanning**
   - The `audit_secrets.py` script automatically scans for accidentally committed secrets
   - GitHub Actions runs this script on every push and pull request
   - Patterns include: API keys, JWT tokens, connection strings, etc.

### Example `.env` File Structure

```bash
# .env (never commit this file)
FRED_API_KEY=your_actual_fred_api_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
DATABASE_URL=postgresql://user:password@host:port/dbname
DBT_PROFILES_DIR=~/.dbt
```

### Example `.env.example` File Structure

```bash
# .env.example (commit this file)
FRED_API_KEY=your_fred_api_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
DATABASE_URL=postgresql://user:password@host:port/dbname
DBT_PROFILES_DIR=~/.dbt
```

---

## Environment Variables

### FRED API Key

- **Source:** Federal Reserve Economic Data (FRED) API
- **Usage:** Data ingestion from FRED
- **Scope:** Read-only access to public economic data
- **Obtain:** https://fredaccount.stlouisfed.org/login/secure/

### Supabase Keys

Three types of Supabase keys are used:

1. **Anon Key (`SUPABASE_KEY`)**
   - Used by client-side applications
   - Has limited permissions via RLS
   - Can read published views only

2. **Service Role Key (`SUPABASE_SERVICE_ROLE_KEY`)**
   - Used by backend processes and ETL
   - Full database access (bypasses RLS)
   - **Never expose to client applications**
   - Only used in GitHub Actions workflows with proper secret masking

3. **Database Connection String (`DATABASE_URL`)**
   - PostgreSQL connection string
   - Used by dbt and data pipelines
   - Format: `postgresql://user:password@host:port/database`

### Loading Environment Variables

**Python:**
```python
import os
from dotenv import load_dotenv

load_dotenv()
fred_api_key = os.getenv("FRED_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
```

**dbt:**
Create `~/.dbt/profiles.yml`:
```yaml
economy_pulse:
  target: dev
  outputs:
    dev:
      type: postgres
      host: "{{ env_var('SUPABASE_HOST') }}"
      user: "{{ env_var('SUPABASE_USER') }}"
      password: "{{ env_var('SUPABASE_PASSWORD') }}"
      port: 5432
      dbname: postgres
      schema: public
      threads: 4
```

---

## Supabase Row Level Security

### Overview

Row Level Security (RLS) is a PostgreSQL feature that restricts database access based on the authenticated user or application role. This ensures:
- Raw data tables are only accessible by backend processes
- Client applications can only read published views
- Data ingestion and transformation is isolated

### Architecture

**Three Role Types:**

1. **service_role** (Backend/ETL)
   - Full access: SELECT, INSERT, UPDATE, DELETE
   - Used only by dbt and Python scripts
   - Credentials never exposed to client applications

2. **anon** (Anonymous clients)
   - Limited to SELECT on published views
   - Cannot access raw data tables
   - Default role for client applications

3. **authenticated** (Authenticated users)
   - Same as anon in this architecture
   - Can SELECT from published views only
   - Future expansion for user-specific data

### Raw Data Tables (RLS Enabled)

The following tables have RLS enabled:
- `raw_gdp`
- `raw_cpi`
- `raw_unemployment_rate`
- `raw_federal_funds_rate`
- `raw_consumer_sentiment`
- `raw_housing_starts`
- `quality_checks`

### Published Views (Optional)

Create materialized views (mart_*) for public data:
```sql
CREATE MATERIALIZED VIEW public.mart_gdp AS
SELECT
  date,
  gdp_value,
  quarterly_growth,
  annual_growth
FROM raw_gdp
WHERE is_valid = TRUE
ORDER BY date DESC;

-- Enable select access for anon users
CREATE POLICY anon_select_mart_gdp ON mart_gdp
FOR SELECT
USING (TRUE);
```

### Verifying RLS Policies

```sql
-- List all RLS policies
SELECT tablename, policyname, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename;

-- Test access with different roles
SET SESSION authorization 'service_role';
SELECT COUNT(*) FROM raw_gdp;  -- Should work

SET SESSION authorization 'anon';
SELECT COUNT(*) FROM raw_gdp;  -- Should fail
SELECT COUNT(*) FROM mart_gdp;  -- Should work
```

---

## CI/CD Security

### GitHub Actions Workflow: security_scan.yml

The workflow runs on every push and pull request:

**1. Secret Scan Job**
- Runs `audit_secrets.py` script
- Detects: API keys, JWT tokens, passwords, private keys, AWS credentials
- Exit code 1 if critical findings detected
- Blocks merge if secrets are found

**2. Dependency Scan Job**
- Runs `pip-audit` against `requirements.txt`
- Detects vulnerable package versions
- Provides remediation steps
- Exit code 1 if vulnerabilities found

**3. Gitignore Verification Job**
- Checks for tracked `.env` files
- Checks for tracked `profiles.yml`
- Checks for tracked credential files (`.pem`, `.key`, etc.)
- Fails if any are found

**4. Code Quality Job**
- Runs Bandit (security linter) on Python code
- Runs Flake8 (code style linter)
- Reports but doesn't block (advisory only)

**5. Container Scan Job** (optional)
- Runs Trivy on Docker images (if present)
- Scans for known vulnerabilities
- Uploads results to GitHub Security

### Action Versions

All GitHub Actions are pinned to specific SHA commits (not tags) to prevent supply chain attacks:
- `actions/checkout@eace28b...` (v4.1.1)
- `actions/setup-python@0b93645...` (v5.0.0)
- `aquasecurity/trivy-action@6e7b7d...` (v0.24.0)
- `github/codeql-action@662c8f...` (v3.24.1)

### Secret Management in Workflows

GitHub Secrets are used for sensitive data in CI/CD:

1. **Set up secrets in GitHub:**
   - Go to: Settings → Secrets and variables → Actions
   - Add secrets: `FRED_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, etc.

2. **Reference secrets in workflows:**
   ```yaml
   env:
     FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
     DATABASE_URL: ${{ secrets.DATABASE_URL }}
   ```

3. **Never log secrets:**
   - Always use `--quiet` or suppress output for sensitive commands
   - GitHub masks secrets in logs automatically
   - Never echo or print secrets

---

## Dependency Scanning

### pip-audit

Scans Python dependencies for known vulnerabilities:

```bash
# Local scanning
pip install pip-audit
pip-audit -r requirements.txt

# Strict mode (exit code 1 on any findings)
pip-audit -r requirements.txt --strict
```

### requirements.txt Best Practices

1. **Pin exact versions:**
   ```
   requests==2.31.0
   python-dotenv==1.0.0
   dbt-postgres==1.5.0
   ```

2. **Separate dev dependencies:**
   Create `requirements-dev.txt`:
   ```
   pytest==7.4.0
   black==23.7.0
   flake8==6.0.0
   ```

3. **Review before updating:**
   - Check changelog for security issues
   - Update only when necessary
   - Test thoroughly before merging

---

## Credential Rotation

### When to Rotate

- Quarterly (standard practice)
- Immediately if credentials are suspected compromised
- When an employee leaves the project
- After a security incident

### FRED API Key Rotation

1. Log in to https://fredaccount.stlouisfed.org
2. Generate a new API key
3. Update locally: Edit `.env`, set `FRED_API_KEY=<new_key>`
4. Update CI/CD: GitHub Settings → Secrets → Update `FRED_API_KEY`
5. Test the new key in development
6. Revoke the old key in FRED account

### Supabase Key Rotation

1. Go to Supabase Dashboard → Project → Settings → API
2. Click "Regenerate key" next to anon key or service role key
3. Update locally in `.env`
4. Update in GitHub Secrets
5. Test in development environment
6. Re-deploy applications

### Database Password Rotation

1. Change password in Supabase Dashboard:
   - Settings → Database → Reset Database Password
2. Update `DATABASE_URL` in `.env` with new password
3. Update `DATABASE_URL` in GitHub Secrets
4. Verify dbt connection: `dbt debug`
5. Re-run CI/CD pipelines

### Rollback Procedure

If rotation fails:
1. Revert to previous credentials
2. Investigate the issue
3. Document what failed
4. Re-attempt after fixing

---

## Security Checklist for Contributors

Before committing code, verify:

### Local Setup
- [ ] `cp .env.example .env` and fill with your credentials
- [ ] `.env` is listed in `.gitignore`
- [ ] Python virtual environment is activated
- [ ] `profiles.yml` exists locally (not in repo)

### Before Committing
- [ ] No `.env` files are staged: `git status | grep .env`
- [ ] No credentials in code: `grep -r "password" src/`
- [ ] No API keys in code: `grep -r "api_key" src/`
- [ ] Run local secret scan: `python src/security/audit_secrets.py --path .`
- [ ] Run tests: `pytest tests/`
- [ ] Run linter: `flake8 src/`

### Pull Request Review
- [ ] Security scan passed in CI/CD
- [ ] Dependency scan passed (no vulnerabilities)
- [ ] Gitignore verification passed
- [ ] No new secrets detected
- [ ] No hardcoded credentials in code

### Code Review Questions
- Does this code access any secrets? (If yes, are they from env vars?)
- Does this code make API calls? (Are credentials passed safely?)
- Does this code access the database? (Is the connection string from .env?)
- Are there any hardcoded hostnames, usernames, or tokens?

---

## Incident Response

### If Secrets Are Accidentally Committed

1. **Immediate Action:**
   - Do NOT just remove the file and commit again
   - The secret is still in Git history

2. **Steps to Take:**
   ```bash
   # Remove file from history (use with caution!)
   git filter-branch --tree-filter 'rm -f <file>' HEAD

   # Force push (only in private repos!)
   git push --force origin main
   ```

3. **Rotate Credentials:**
   - Immediately rotate any exposed credentials
   - Generate new API keys, passwords, etc.

4. **Post-Mortem:**
   - Document what happened
   - Review contributor training
   - Consider additional safeguards

### If Suspicious Activity Is Detected

1. **Investigate:**
   - Check GitHub Actions logs
   - Review database access logs
   - Check API usage

2. **Remediate:**
   - Rotate all credentials
   - Revoke access tokens
   - Update security policies

3. **Document:**
   - Create incident report
   - Share with team
   - Update procedures

---

## Additional Resources

- [Supabase RLS Documentation](https://supabase.com/docs/guides/auth/row-level-security)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [GitHub Actions Security](https://docs.github.com/en/actions/security-guides)
- [dbt Best Practices](https://docs.getdbt.com/guides/best-practices)
- [pip-audit Documentation](https://github.com/pypa/pip-audit)

---

**Last Updated:** 2026-03-20
**Maintained By:** Security Team
**Review Schedule:** Quarterly
