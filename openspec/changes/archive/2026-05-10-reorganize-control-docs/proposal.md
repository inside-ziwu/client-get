## Why

`_control/` was created as a temporary PM control area, but the project has now moved into OpenSpec-driven implementation. Keeping project-status snapshots, review rounds, and open-question lists in `_control/` creates duplicate authority and stale guidance that can conflict with active OpenSpec changes.

## What Changes

- Reorganize `_control/` into a slim evidence/input area:
  - `_control/inputs/` for business, reference, and database input materials.
  - `_control/mockups/` for UI prototype inputs.
  - `_control/evidence/` for completed-slice records, deployment evidence, dumps, and live snapshots.
  - `_control/archive/` for old planning/review/process documents kept only for traceability.
- Add `_control/README.md` to document the new authority order:
  - Active OpenSpec change artifacts are implementation authority.
  - `_control/` is read-only input/evidence/archive unless a current OpenSpec change explicitly updates it.
- Move V3 business goals and mockups into input locations.
- Move completed slice notes, release manifest, deployment checklist, database dumps, and schema snapshots into evidence locations.
- Move stale root indexes, gap audits, delivery plans, open questions, and review files into archive.
- Remove `.DS_Store` files from `_control/`.
- Update `AGENTS.md` so agents no longer treat `_control/04-open-questions.md` or root control files as mandatory current workflow inputs.

## Capabilities

### New Capabilities
- `control-doc-governance`: Defines `_control/` document categories, authority order, and lifecycle rules under OpenSpec implementation.

### Modified Capabilities

## Impact

- Affected files are documentation and control artifacts only.
- No application code, database schema, runtime configuration, or deployment behavior changes.
- Existing active OpenSpec changes remain the source of implementation scope and task status.
