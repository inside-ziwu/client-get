## ADDED Requirements

### Requirement: OpenSpec remains implementation authority
The workspace MUST treat active `openspec/changes/<change-id>/` artifacts as the implementation authority. `_control/` documents MUST NOT override an active change proposal, design, tasks, or spec.

#### Scenario: Agent starts implementation work
- **WHEN** an agent prepares to implement or modify project behavior
- **THEN** the agent MUST read the relevant active OpenSpec change artifacts before using `_control/` material

### Requirement: Control documents are categorized by lifecycle
`_control/` MUST organize documents into input, mockup, evidence, and archive categories so readers can tell whether a file is current input, completed evidence, or historical process.

#### Scenario: Reader opens control directory
- **WHEN** a reader opens `_control/`
- **THEN** `_control/README.md` MUST describe each category and the authority order

### Requirement: Project status snapshots are not current workflow inputs
Project-status snapshots, gap audits, old delivery plans, open-question lists, and review rounds MUST be archived or otherwise marked historical once their decisions are represented in OpenSpec changes.

#### Scenario: A stale review or gap audit exists
- **WHEN** a review, gap audit, or project-status file is no longer the source of current implementation tasks
- **THEN** it MUST be placed under `_control/archive/` or removed after user approval

### Requirement: Durable inputs remain easy to find
Business goals, UI mockups, database access rules, schema snapshots, production dumps, and reference implementation research MUST remain available in `_control/` under input or evidence paths.

#### Scenario: A change needs background material
- **WHEN** an active OpenSpec change needs business, UI, database, or reference context
- **THEN** the relevant durable input MUST be discoverable under `_control/inputs/`, `_control/mockups/`, or `_control/evidence/`
