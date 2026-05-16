## Context

The workspace now uses OpenSpec changes as the execution authority for feature work, bug fixes, refactors, deployment changes, and documentation changes. `_control/` still contains older planning snapshots, review rounds, open questions, and slice notes that were useful before OpenSpec became the workflow, but those files can now conflict with active `openspec/changes/*` artifacts.

The reorganization must preserve useful raw inputs and evidence while making stale status documents hard to mistake for current instructions.

## Goals / Non-Goals

**Goals:**
- Make `_control/` safe to read during OpenSpec implementation.
- Keep business inputs, UI mockups, database/reference materials, production snapshots, and completed-slice evidence.
- Archive or quarantine process/status documents that have been superseded by OpenSpec.
- Document the authority order in `_control/README.md` and `AGENTS.md`.
- Preserve file history where possible with `git mv`.

**Non-Goals:**
- Do not edit business content inside the moved documents.
- Do not change active feature OpenSpec scopes.
- Do not modify application code, database schema, deployment scripts, or runtime configuration.
- Do not delete historical process documents in this pass except `.DS_Store` noise.

## Decisions

1. **Use archive-first cleanup rather than immediate deletion.**
   - Rationale: The worktree already contains many ongoing changes. Archiving reduces risk while removing stale documents from the normal reading path.
   - Alternative rejected: Delete reviews and project-status snapshots immediately. That is cleaner, but makes it harder to recover context if an active change still links to one.

2. **Keep `_control/inputs/` for materials that are external, business-facing, or factual.**
   - Business goals, reference implementation research, database access protocol, schema snapshots, and raw schema notes stay as inputs/evidence.

3. **Move V3 mockups out of `_control/v3/` into `_control/mockups/v3/`.**
   - Rationale: Mockups are durable input assets, not project status.

4. **Move completed slice notes into `_control/evidence/slices/`.**
   - Rationale: Slice notes are evidence of past work, not instructions for future work.

5. **Move reviews and superseded planning/status files into `_control/archive/`.**
   - Rationale: They remain traceable without being mistaken for current implementation guidance.

6. **Make OpenSpec authority explicit.**
   - Active OpenSpec artifacts supersede `_control` content for implementation decisions.

## Risks / Trade-offs

- **Broken links in archived documents** → Acceptable for archived material; `_control/README.md` will document the new paths for current materials.
- **Existing active changes may still mention old `_control/v3/...` paths** → Keep archived files in-repo rather than deleting them; update only the global agent guidance in this pass.
- **Git status is already dirty** → Scope edits to `_control/`, `AGENTS.md`, and this change directory; do not revert unrelated changes.
