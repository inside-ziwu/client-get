## 1. Control Directory Structure

- [x] 1.1 Create `_control/README.md` with the new authority order and category definitions
- [x] 1.2 Create target directories for inputs, mockups, evidence, and archive
- [x] 1.3 Move durable business/reference input documents into input locations
- [x] 1.4 Move V3 mockups into `_control/mockups/v3/`
- [x] 1.5 Move database dumps and live snapshots into `_control/evidence/database/`

## 2. Archive Superseded Process Material

- [x] 2.1 Move root control indexes and open questions into `_control/archive/root-control/`
- [x] 2.2 Move superseded V3 planning/status documents into `_control/archive/v3-planning/`
- [x] 2.3 Move completed slice notes into `_control/evidence/slices/`
- [x] 2.4 Move review files into `_control/archive/reviews/`
- [x] 2.5 Remove `.DS_Store` files from `_control/`

## 3. Agent Guidance

- [x] 3.1 Update `AGENTS.md` so implementation work reads OpenSpec changes first and treats `_control/` as input/evidence/archive
- [x] 3.2 Keep `docs/` and `blueprint/` read-only rules unchanged

## 4. Verification

- [x] 4.1 Verify `_control/` contains only the new top-level categories plus README
- [x] 4.2 Verify no active instruction still requires `_control/04-open-questions.md`
- [x] 4.3 Run OpenSpec validation for `reorganize-control-docs`
