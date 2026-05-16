## ADDED Requirements

### Requirement: Admin MUST use canonical frontend app path
The frontend workspace SHALL use `apps/admin` as the only active Admin application path.

#### Scenario: Legacy target path residue is handled
- **WHEN** `frontend/apps/admin` exists before migration
- **THEN** implementation SHALL verify it has no git-tracked source files before removal
- **AND** implementation SHALL NOT overwrite tracked files in that directory

#### Scenario: Canonical path exists
- **WHEN** a developer inspects the frontend workspace
- **THEN** `frontend/apps/admin` SHALL exist and contain the Next.js Admin application
- **AND** `frontend/apps/admin-next` SHALL NOT exist as an active application directory

#### Scenario: Root app is not created
- **WHEN** a developer inspects the repository root
- **THEN** root-level `admin/` SHALL NOT be required for the Admin frontend
- **AND** Admin SHALL remain inside the `frontend/` git repository

### Requirement: Admin MUST use canonical workspace package name
The Admin workspace package SHALL be named `@apps/admin`.

#### Scenario: Package name is canonical
- **WHEN** `frontend/apps/admin/package.json` is inspected
- **THEN** its `name` field SHALL equal `@apps/admin`

#### Scenario: Transitional package name is rejected
- **WHEN** active frontend package scripts, Dockerfile, or contract tests are inspected
- **THEN** they SHALL NOT target `@apps/admin-next`

### Requirement: Admin build and deploy files MUST target canonical app
Admin build and deploy configuration SHALL target `apps/admin` while preserving the formal `clientget-admin` image identity.

#### Scenario: Dockerfile builds canonical app
- **WHEN** `frontend/Dockerfile.admin` is inspected
- **THEN** it SHALL copy files from `apps/admin`
- **AND** it SHALL run `pnpm --filter @apps/admin build`
- **AND** it SHALL start `apps/admin/server.js` from the Next.js standalone output

#### Scenario: Image name remains stable
- **WHEN** `frontend/deploy/push-admin.sh` is inspected
- **THEN** it SHALL keep the image repository name `clientget-admin`
- **AND** it SHALL NOT introduce `clientget-admin-next`

### Requirement: Transitional admin-next commands MUST be removed
The frontend root package scripts SHALL expose formal Admin commands and remove transitional `admin-next` aliases.

#### Scenario: Formal commands exist
- **WHEN** `frontend/package.json` is inspected
- **THEN** `dev:admin` SHALL target `@apps/admin`
- **AND** `build:admin` SHALL target `@apps/admin`

#### Scenario: Transitional commands are absent
- **WHEN** `frontend/package.json` is inspected
- **THEN** `dev:admin-next` SHALL NOT exist
- **AND** `build:admin-next` SHALL NOT exist

### Requirement: Active references MUST reject admin-next naming
Active Admin source, test, build, and deploy files SHALL not retain transitional `admin-next` paths or package names.

#### Scenario: Active references are clean
- **WHEN** active files under `frontend/apps/admin`, `frontend/Dockerfile.admin`, `frontend/package.json`, and `frontend/deploy/push-admin.sh` are searched
- **THEN** `apps/admin-next` SHALL NOT appear
- **AND** `@apps/admin-next` SHALL NOT appear

#### Scenario: Historical records are allowed
- **WHEN** archived OpenSpec changes or historical evidence files are searched
- **THEN** historical mentions of `admin-next` MAY remain because they document past decisions rather than active build or runtime behavior
