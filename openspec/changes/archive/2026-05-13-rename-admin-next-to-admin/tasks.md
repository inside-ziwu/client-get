## 1. Workspace Rename

- [x] 1.1 Confirm existing `frontend/apps/admin` has no git-tracked files.
- [x] 1.2 List legacy local `frontend/apps/admin` residue and preserve any non-build local env file if needed.
- [x] 1.3 Remove legacy local `frontend/apps/admin` residue before rename.
- [x] 1.4 Remove ignored build artifacts from `frontend/apps/admin-next` (`.next`, `node_modules`, `*.tsbuildinfo`) while preserving tracked source changes.
- [x] 1.5 Rename `frontend/apps/admin-next` to `frontend/apps/admin`.
- [x] 1.6 Update `frontend/apps/admin/package.json` package name from `@apps/admin-next` to `@apps/admin`.
- [x] 1.7 Update frontend root scripts so `dev:admin` and `build:admin` target `@apps/admin`.
- [x] 1.8 Remove transitional `dev:admin-next` and `build:admin-next` scripts.

## 2. Build and Deploy Wiring

- [x] 2.1 Update `frontend/Dockerfile.admin` COPY paths from `apps/admin-next` to `apps/admin`.
- [x] 2.2 Update `frontend/Dockerfile.admin` build filter from `@apps/admin-next` to `@apps/admin`.
- [x] 2.3 Update Next standalone output copy paths and `CMD` to `apps/admin`.
- [x] 2.4 Confirm `frontend/deploy/push-admin.sh` still builds `clientget-admin` via `Dockerfile.admin` without `admin-next` transitional naming.

## 3. Tests and Active References

- [x] 3.1 Move Admin contract tests under `frontend/apps/admin/test`.
- [x] 3.2 Update contract tests to assert `@apps/admin`, `apps/admin`, and reject `@apps/admin-next` / `apps/admin-next`.
- [x] 3.3 Search active frontend source/build/deploy/test files and remove stale `admin-next` references.
- [x] 3.4 Refresh `frontend/pnpm-lock.yaml` for the workspace package rename.

## 4. Verification

- [x] 4.1 Run Admin contract tests from the new path.
- [x] 4.2 Run `pnpm --filter @apps/admin type-check`.
- [x] 4.3 Run `pnpm --filter @apps/admin build`.
- [x] 4.4 Run local Docker build for `Dockerfile.admin` without pushing.
- [x] 4.5 Run OpenSpec status/apply check and verify all tasks are complete.
