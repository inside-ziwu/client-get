## ADDED Requirements

### Requirement: Tenant settings routes render
The system SHALL allow authenticated tenant users with settings access to open every existing Tenant settings subpage without an uncaught render error, blank page, or infinite loading state.

#### Scenario: Tenant opens settings root route
- **WHEN** an authenticated tenant user opens `/settings`
- **THEN** the system redirects to a default settings subpage or renders a valid settings index page

#### Scenario: Tenant opens an existing settings subpage
- **WHEN** an authenticated tenant user opens an existing route under `/settings`
- **THEN** the Tenant layout and target settings subpage render successfully

#### Scenario: Tenant navigates between settings subpages
- **WHEN** an authenticated tenant user switches between existing settings menu items
- **THEN** the target subpage loads without requiring a full browser refresh

### Requirement: Settings data loading is recoverable
The system SHALL handle loading, empty, and failed data states inside each Tenant settings subpage without breaking the surrounding Tenant layout or other settings routes.

#### Scenario: Settings API returns empty data
- **WHEN** a settings subpage receives an empty but valid API response
- **THEN** the page renders an empty or default state appropriate for that setting

#### Scenario: Settings API request fails
- **WHEN** a settings subpage initial API request fails
- **THEN** the page shows a recoverable error state or message instead of an uncaught exception, blank page, or infinite spinner

### Requirement: Existing settings behavior remains unchanged
The system MUST preserve the existing business behavior of Tenant settings while fixing page availability.

#### Scenario: User saves an existing setting
- **WHEN** an authenticated tenant user saves a supported setting after the page loads
- **THEN** the system uses the existing API contract and preserves the current permission and validation rules
