# US Economy Pulse Pipeline - Project Tracker

**Last Updated:** 2026-03-20
**Status:** Phase 1 - In Progress
**Project Duration:** 4 weeks | 4 phases

---

## Project Overview

### Name
**US Economy Pulse Pipeline**

### Description
A production-grade data engineering pipeline that ingests, transforms, and monitors economic indicators from the Federal Reserve Economic Data (FRED) API. The system provides near-real-time visibility into key US economic metrics including GDP, CPI, unemployment rate, federal funds rate, consumer sentiment, and housing starts. The pipeline includes quality assurance, data transformation with dbt, orchestration via GitHub Actions, security hardening, and comprehensive documentation for cross-functional teams.

### Team Roster (7 Agents + 1 Tech Lead)

| Role | Agent | Responsibility |
|------|-------|-----------------|
| **Tech Lead** | Senior Engineer | Architecture oversight, code reviews, escalations |
| **Project Manager** | Agent 0 | Project coordination, status tracking, risk management |
| **Data Ingestor** | Agent 1 | FRED API integration, data loading, backfill tooling |
| **Transformer** | Agent 2 | dbt models, data transformations, analytics marts |
| **Quality Guardian** | Agent 3 | Data validation, quality checks, alerting framework |
| **Orchestrator** | Agent 4 | GitHub Actions workflows, scheduling, orchestration |
| **Documenter** | Agent 5 | Technical documentation, data dictionary, setup guides |
| **Security Lead** | Agent 6 | Security audit, access control, compliance, secrets management |

### Tech Stack

- **Data Source:** Federal Reserve Economic Data (FRED) API
- **Data Warehouse:** Supabase (PostgreSQL, free tier)
- **Transformation:** dbt Core v1.5+
- **Orchestration:** GitHub Actions
- **Alerting:** Slack webhooks
- **Visualization:** Metabase (optional)
- **Runtime:** Python 3.10+

### FRED Economic Series

| Code | Indicator | Frequency | Description |
|------|-----------|-----------|-------------|
| GDPC1 | Real GDP | Quarterly | Chained 2012 dollars |
| CPIAUCSL | CPI | Monthly | All items, not seasonally adjusted |
| UNRATE | Unemployment Rate | Monthly | Percent |
| FEDFUNDS | Federal Funds Rate | Monthly | Effective rate |
| UMCSENT | Consumer Sentiment | Monthly | Index |
| HOUST | Housing Starts | Monthly | Thousands of units |

---

## Phase Overview

| Phase | Duration | Focus | Gate Criteria |
|-------|----------|-------|---------------|
| **Phase 1** | Week 1 | Data ingestion, base infrastructure | Successful FRED data load, Supabase DB initialized |
| **Phase 2** | Week 2 | Transformation & analytics | dbt models deployed, quality checks pass, sample transformations verified |
| **Phase 3** | Week 3 | Quality & Orchestration | Automated workflows running, alerts configured, all quality gates active |
| **Phase 4** | Week 4 | Documentation & Security | Full documentation complete, security audit passed, hardening applied, production ready |

---

## Phase 1 Status Table

**Phase 1 Focus:** Data Ingestion & Infrastructure Setup
**Target Completion:** End of Week 1

| Agent | Component | Status | Completion % | Blocker | Notes |
|-------|-----------|--------|--------------|---------|-------|
| Agent 0 (PM) | Project tracker | 🟡 In Progress | 30% | None | Creating initial structure |
| Agent 0 (PM) | Ticket breakdown | 🟡 In Progress | 30% | None | Defining all work items |
| Agent 1 (Ingestor) | fred_client.py | 🔴 Pending | 0% | API credentials setup | Awaits .env.example |
| Agent 1 (Ingestor) | config.py | 🔴 Pending | 0% | None | Environment configuration |
| Agent 1 (Ingestor) | requirements.txt | 🔴 Pending | 0% | None | Python dependencies |
| Agent 1 (Ingestor) | .env.example | 🔴 Pending | 0% | None | Template for secrets |
| Agent 1 (Ingestor) | load_to_supabase.py | 🔴 Pending | 0% | Supabase setup | Data loading script |
| Agent 1 (Ingestor) | Backfill script | 🔴 Pending | 0% | load_to_supabase.py | Historical data ingestion |
| Agent 2 (Transformer) | dbt init | 🔴 Pending | 0% | None | Project scaffold only |
| Agent 3 (Quality) | quality_checks table | 🔴 Pending | 0% | Supabase DB | DDL definition |
| Agent 4 (Orchestrator) | GitHub Actions setup | 🔴 Pending | 0% | Agent 1 fred_client | Daily workflow template |
| Agent 5 (Documenter) | README.md (draft) | 🔴 Pending | 0% | None | Initial setup docs |
| Agent 6 (Security) | .gitignore hardened | 🔴 Pending | 0% | None | Secrets protection |

**Legend:** 🟢 Complete | 🟡 In Progress | 🔴 Pending | 🔵 Blocked

---

## Dependency Map

### Phase 1 Dependencies

```
Agent 1 (Ingestor)
├─ .env.example (no deps)
├─ config.py (depends: .env.example)
├─ requirements.txt (no deps)
├─ fred_client.py (depends: requirements.txt, config.py, API credentials)
├─ load_to_supabase.py (depends: fred_client.py, Supabase account)
└─ backfill script (depends: load_to_supabase.py)

Agent 3 (Quality)
├─ quality_checks table (depends: Supabase DB ready)
└─ pre_ingestion_checks.py (depends: quality_checks table, fred_client.py)

Agent 6 (Security)
├─ hardened .gitignore (no deps)
└─ audit_secrets.py (depends: Agent 1 code complete)

Agent 4 (Orchestrator)
└─ daily_pipeline.yml (depends: Agent 1 fred_client.py, Agent 3 checks)

Agent 5 (Documenter)
└─ README.md draft (depends: Phase 1 architecture agreed)
```

### Cross-Phase Critical Path

```
PHASE 1 → PHASE 2 → PHASE 3 → PHASE 4
  ↓          ↓          ↓          ↓
Ingest    Transform   Quality   Documentation
  ↓          ↓          ↓          ↓
Load DB   dbt models  Alerts     Security
  ↓          ↓          ↓          ↓
 [Gate]    [Gate]     [Gate]     [Gate]
```

**Critical Path Agents:** 1 → 2 → 3 → 4 → 5 → 6

---

## Integration Checkpoints

### Phase 1 Gate (End of Week 1)

**Checkpoint:** Data Ingestion & Infrastructure Ready

**Requirements:**
- [ ] FRED API credentials configured securely in .env
- [ ] All 6 FRED series successfully ingested into Supabase
- [ ] Raw data tables created: `raw_fred_gdpc1`, `raw_fred_cpiaucsl`, `raw_fred_unrate`, `raw_fred_fedfunds`, `raw_fred_umcsent`, `raw_fred_houst`
- [ ] Backfill completed for last 10 years of data
- [ ] Pre-ingestion quality checks deployed and passing
- [ ] .gitignore hardened, no secrets in version control
- [ ] Daily ingestion workflow scheduled via GitHub Actions (dry-run mode)

**Owner:** Agent 0 (PM) with Agent 1 & 3 leads

**Exit Criteria Met:** ✓ When all data is in Supabase and pre-checks pass

---

### Phase 2 Gate (End of Week 2)

**Checkpoint:** Transformation & Analytics Models Ready

**Requirements:**
- [ ] dbt project initialized with sources, staging models (6 base models)
- [ ] Intermediate models deployed: YoY changes, rolling averages, recession indicators, correlation analysis
- [ ] Mart models created for analytics: `mart_economic_trends`, `mart_recession_risk`, `mart_sentiment_correlation`
- [ ] dbt generic tests passing: not_null, unique, relationships, custom tests
- [ ] dbt documentation generated and accessible
- [ ] All transformations produce correct output (validation against manual checks)

**Owner:** Agent 2 (Transformer) with Agent 0 review

**Exit Criteria Met:** ✓ When dbt runs without errors and all tests pass

---

### Phase 3 Gate (End of Week 3)

**Checkpoint:** Orchestration & Quality Assurance Active

**Requirements:**
- [ ] Daily pipeline workflow (daily_pipeline.yml) running successfully
- [ ] Weekly deep test workflow deployed (weekly_deep_test.yml)
- [ ] Backfill workflow operational (backfill.yml) for historical reprocessing
- [ ] Slack alerts configured and tested
- [ ] Post-transform quality checks passing consistently
- [ ] Quality metrics dashboard in Metabase (or grafana alternative)
- [ ] No data loss or duplication in 7-day test run

**Owner:** Agent 4 (Orchestrator) with Agent 3 quality gates

**Exit Criteria Met:** ✓ When workflows run for 7 days without manual intervention

---

### Phase 4 Gate (End of Week 4)

**Checkpoint:** Production Ready & Fully Documented

**Requirements:**
- [ ] Complete README.md with architecture diagram
- [ ] Data dictionary documenting all fields, transformations, lineage
- [ ] Quality monitoring guide and dashboard setup
- [ ] Setup guide for new team members (< 30 minutes to first run)
- [ ] Security audit complete: RLS policies, encryption, audit logging
- [ ] No secrets in repository (audit_secrets.py clean)
- [ ] Security.md with threat model and mitigation
- [ ] Runbook for common failures and recovery procedures
- [ ] Knowledge transfer session completed with team

**Owner:** Agent 5 (Documenter) & Agent 6 (Security) with Agent 0 sign-off

**Exit Criteria Met:** ✓ When entire team can operate pipeline independently

---

## Risk Register

### Risk 1: FRED API Rate Limits
**Severity:** High | **Probability:** Medium | **Impact:** Pipeline fails to ingest new data

| Aspect | Detail |
|--------|--------|
| **Description** | FRED API has rate limits; exceeding them causes throttling or 429 errors |
| **Trigger** | High-frequency polling (> 120 calls/min) or large backfill requests |
| **Mitigation** | Implement exponential backoff, request caching, batch requests; monitor rate-limit headers |
| **Owner** | Agent 1 (Ingestor) |
| **Contingency** | Manual backfill API requests during off-peak hours; switch to daily batch mode |
| **Monitor** | API response times, HTTP 429 count in logs |

---

### Risk 2: Supabase Tier Limitations
**Severity:** High | **Probability:** Low | **Impact:** Data loss, service unavailable

| Aspect | Detail |
|--------|--------|
| **Description** | Free tier has storage (500MB) and concurrent connection limits; monthly query quota |
| **Trigger** | Rapid data growth, historical backfill, high concurrent queries from Metabase |
| **Mitigation** | Right-size data retention (2-year window), optimize queries, partition large tables, document upgrade path |
| **Owner** | Agent 1 (Ingestor) & Agent 2 (Transformer) |
| **Contingency** | Upgrade to Pro tier; archive old data; implement data compression |
| **Monitor** | Supabase resource usage dashboard; storage consumption trends |

---

### Risk 3: dbt Model Compilation Errors
**Severity:** Medium | **Probability:** Medium | **Impact:** Transformation jobs fail, no fresh analytics

| Aspect | Detail |
|--------|--------|
| **Description** | Complex dbt DAG with macros, tests, and dependencies; schema drift causes failures |
| **Trigger** | Raw data schema changes, circular dependencies in models, missing source definitions |
| **Mitigation** | Comprehensive dbt testing (dbt test), CI/CD validation on PR, source contracts, data contracts |
| **Owner** | Agent 2 (Transformer) |
| **Contingency** | Manual model repair; rollback to last known good version; pause downstream jobs |
| **Monitor** | dbt test results, compilation logs, model dependency graph |

---

### Risk 4: GitHub Actions Secret Exposure
**Severity:** Critical | **Probability:** Low | **Impact:** FRED API key, Supabase credentials leaked

| Aspect | Detail |
|--------|--------|
| **Description** | Secrets accidentally committed or logged; action logs expose environment variables |
| **Trigger** | Developer commits .env file, hardcoded credentials in code, verbose logging |
| **Mitigation** | Hardened .gitignore, secret scanning tools, no console logging of sensitive data, GitHub secret masking |
| **Owner** | Agent 6 (Security) |
| **Contingency** | Immediate credential rotation, audit commit history, revoke leaked keys |
| **Monitor** | GitGuardian, GitHub secret scanning alerts, audit logs |

---

### Risk 5: Data Quality Degradation
**Severity:** Medium | **Probability:** Medium | **Impact:** Invalid insights, poor decision-making

| Aspect | Detail |
|--------|--------|
| **Description** | Missing values, duplicates, outliers, staleness not detected until analysis phase |
| **Trigger** | FRED API returning incomplete data, network failures, transformation logic errors |
| **Mitigation** | Automated quality checks at each stage (pre-ingest, post-transform), data profiling, anomaly detection |
| **Owner** | Agent 3 (Quality Guardian) |
| **Contingency** | Halt pipeline, investigate root cause, reprocess with corrected logic |
| **Monitor** | Quality metrics dashboard, Slack alerts on check failures |

---

### Risk 6: Knowledge Silos & Onboarding Friction
**Severity:** Medium | **Probability:** High | **Impact:** Slow incident response, maintainability issues

| Aspect | Detail |
|--------|--------|
| **Description** | Documentation incomplete or out-of-sync; hard to debug without subject-matter experts |
| **Trigger** | Key team member unavailable, new team member joining, incident during off-hours |
| **Mitigation** | Comprehensive docs (README, data dict, runbooks), code comments, architecture diagrams |
| **Owner** | Agent 5 (Documenter) with all agents |
| **Contingency** | Pair programming, escalation to tech lead, knowledge transfer sessions |
| **Monitor** | Doc freshness (update on each major change), onboarding time metrics |

---

### Risk 7: Workflow Scheduling Conflicts
**Severity:** Low | **Probability:** Medium | **Impact:** Workflows skip runs or overlap, data inconsistency

| Aspect | Detail |
|--------|--------|
| **Description** | Daily ingestion, weekly deep test, backfill tasks compete for resources or cause locks |
| **Trigger** | Overlapping job runs, long-running backfill blocking daily ingest, database locks |
| **Mitigation** | Staggered scheduling, job timeout limits, concurrency controls, lock-free transformations |
| **Owner** | Agent 4 (Orchestrator) |
| **Contingency** | Manual job cancellation, priority queuing, dedicated slots for backfill |
| **Monitor** | Workflow execution times, overlap detection, error logs |

---

## Key Dates & Milestones

| Date | Milestone | Status |
|------|-----------|--------|
| 2026-03-20 | Phase 1 Kickoff | ✓ Active |
| 2026-03-27 | Phase 1 Gate Review | 🔴 Pending |
| 2026-04-03 | Phase 2 Gate Review | 🔴 Pending |
| 2026-04-10 | Phase 3 Gate Review | 🔴 Pending |
| 2026-04-17 | Phase 4 Gate Review / Launch | 🔴 Pending |

---

## Communication & Escalation

**Sync Frequency:**
- Daily standup: 15 min (9:30 AM)
- Weekly review: 30 min (Fri 4 PM)
- Phase gate reviews: Ad-hoc, as needed

**Escalation Path:**
1. Task-level issues → Assigned agent + Agent 0 (PM)
2. Cross-agent blockers → Tech Lead + Agent 0 (PM)
3. Critical risks (security, data loss) → Immediate escalation to tech lead & stakeholders

**Slack Channel:** #economy-pulse-pipeline

---

## Success Criteria (Definition of Done)

By end of Phase 4:
- ✓ All 6 FRED series ingesting automatically daily
- ✓ 4+ dbt models transformed and tested, producing analytics
- ✓ Quality checks passing > 99% of runs
- ✓ Workflows automated and requiring zero manual intervention
- ✓ Team can onboard and operate independently
- ✓ Zero security vulnerabilities or exposed credentials
- ✓ Documentation is complete and maintained

---

**Document Owner:** Agent 0 (PM)
**Last Review:** 2026-03-20
**Next Review:** 2026-03-27 (Phase 1 Gate)
