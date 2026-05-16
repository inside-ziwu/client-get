## Overview

This change removes the final known skipped legacy backend test after the Phase 2 skipped-test cleanup. The test is explicitly skipped because it inserts into `shared_companies`, which was removed by the V3 migration path, and because the CRM behavior it asserts is not currently implemented.

## Scope

- Delete `backend/tests/test_webhook_api.py` if it contains only the obsolete skipped webhook scenario and its private setup helper.
- If current-schema webhook tests are added later, they must be introduced under a new OpenSpec change with current V3 fixtures and acceptance criteria.
- Do not modify application webhook handlers, EngageLab integration code, migrations, or models in this cleanup.

## Validation

- Run focused collection or file-level pytest after removal when applicable.
- Run backend full-suite pytest with skip reporting:

```bash
cd backend
.venv/bin/python -m pytest tests -q -rs
```

Expected result: no skipped tests remain from obsolete Phase 2 / `shared_companies` CRM coverage.
