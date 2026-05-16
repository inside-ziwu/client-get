## Context

This change records work already completed during `v3-tenant-companies`: tenant company code still referenced legacy columns and API fields that no longer exist in the current V3 schema. Tenant has no production real data, so compatibility aliases would add complexity without protecting users.

The cleanup crosses backend API, service SQL, frontend pages, shared API contracts, and OpenSpec tasks, so it needs a standalone design record even though implementation is already done.

## Goals / Non-Goals

**Goals:**
- Make tenant company API responses, frontend display, and shared types use only the V3 field contract.
- Remove legacy grade-based tenant UI and email stats semantics.
- Ensure tenant company visibility uses `visibility_status`, not `deleted_at`.
- Keep scoring summaries on tenant companies to `model_score` and `score`.

**Non-Goals:**
- Do not implement C4 private note/tag/group UX beyond removing obsolete score adjustment UI.
- Do not implement full C5 ten-dimension filters beyond the already completed `grade` removal.
- Do not implement C6 industry scoring template UI/data model.
- Do not remove `grade` / `total_score` from internal scoring record tables such as `company_scores`; those are outside the tenant company external contract.

## Decisions

1. Tenant company external contract is breaking-clean, not compatibility-clean.
   - Decision: Remove old aliases and old query parameters.
   - Rationale: Tenant has no real production data, and keeping aliases would make the current V3 schema harder to verify.

2. `visibility_status` is the only tenant company visibility gate.
   - Decision: Replace tenant company `deleted_at` checks with `visibility_status = 'visible'` in relevant tenant company queries.
   - Rationale: Current V3 schema does not use `tenant_companies.deleted_at`.

3. `grade` is not derived for tenant-facing company UX.
   - Decision: Do not map score ranges back into grade labels for tenant company lists, prospects, filters, or email distribution charts.
   - Rationale: The product decision is to keep tenant-facing scoring summaries as `model_score` and `score`.

4. Internal scoring detail can retain historical field names.
   - Decision: Leave `company_scores.grade`, `company_scores.total_score`, and scoring template `grade_thresholds` untouched.
   - Rationale: The cleanup boundary is tenant company external contract and `tenant_companies` references, not internal scoring history.

## Risks / Trade-offs

- Existing callers using removed fields will break -> acceptable because tenant has no real production data and this is explicitly breaking.
- Broad `rg` checks still find `grade` in scoring internals -> mitigated by documenting the boundary and limiting cleanup validation to tenant company external contract.
- Moving completed work into a standalone change can duplicate context from `v3-tenant-companies` -> mitigated by keeping this change narrow and marking tasks as completed.

## Migration Plan

No data migration is required for tenant production data. Deployment is code-only for this cleanup.

Rollback would restore the previous tenant company compatibility surface, but that is not desired unless a caller dependency is discovered before launch.

## Open Questions

None. User decision already recorded: tenant has no real production data, no compatibility is required, and UC-21 score adjustment remains out of scope.
