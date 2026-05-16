## ADDED Requirements

### Requirement: System SHALL maintain a deduplicated peer company layer for Lixiaoyun raw companies

The system SHALL clean `lixiaoyun_raw_companies` into a platform-internal peer company layer that stores one row per deduplicated peer company and keeps raw rows as source evidence.

#### Scenario: Raw company has a website
- **GIVEN** a `lixiaoyun_raw_companies` row has a non-empty website or domain value
- **WHEN** the system cleans the row into the peer company layer
- **THEN** the system SHALL normalize the website to a stable host
- **AND** the system SHALL use that normalized host as the peer company identity
- **AND** the system SHALL create or update one peer company for that website host

#### Scenario: Raw company has no website but has source id
- **GIVEN** a `lixiaoyun_raw_companies` row has no usable website or domain value
- **AND** the row has a non-empty `source_id`
- **WHEN** the system cleans the row into the peer company layer
- **THEN** the system SHALL use the `source_id` as the peer company identity fallback
- **AND** the system SHALL create or update one peer company for that source id

#### Scenario: Existing raw source later gains a website
- **GIVEN** a `lixiaoyun_raw_companies` row was already linked to a peer company by `source_id` fallback
- **AND** a later raw upsert for the same raw source includes a usable website or domain value
- **WHEN** the system cleans the updated row into the peer company layer
- **THEN** the system SHALL keep the existing raw-source-to-peer relation
- **AND** it SHALL NOT automatically move the raw source to a different website-identity peer
- **AND** it MAY update display or diagnostic fields such as `domain` or `website_host`

#### Scenario: Raw company has no website and no source id
- **GIVEN** a `lixiaoyun_raw_companies` row has no usable website or domain value
- **AND** the row has no usable `source_id`
- **WHEN** the system attempts to clean the row into the peer company layer
- **THEN** the system SHALL NOT create a peer company from that row
- **AND** the raw row SHALL remain available for admin/debug review

### Requirement: Website identity SHALL be normalized before peer deduplication

The system SHALL normalize website identity before using it for peer company deduplication.

#### Scenario: Equivalent website strings are cleaned
- **GIVEN** raw rows contain website values such as `https://www.example.com/path?a=1`, `http://example.com/`, and `example.com`
- **WHEN** the system derives peer company identity
- **THEN** all three values SHALL resolve to the same normalized host identity `example.com`
- **AND** the system SHALL deduplicate them into the same peer company

#### Scenario: Website is blank or malformed
- **GIVEN** a raw row has a blank website value or a value that cannot produce a usable host
- **WHEN** the system derives peer company identity
- **THEN** the system SHALL treat the website identity as missing
- **AND** the system SHALL use `source_id` fallback when available

### Requirement: Peer company keyword matches SHALL be retained as a multi-keyword relation

The system SHALL retain all platform keywords that discovered a peer company without creating duplicate peer companies.

#### Scenario: Same website is discovered by multiple keywords
- **GIVEN** two `lixiaoyun_raw_companies` rows have equivalent website host identity
- **AND** the rows reference different `keyword_master_id` values
- **WHEN** the system cleans both rows into the peer company layer
- **THEN** the system SHALL keep one peer company row
- **AND** the system SHALL associate that peer company with both platform keywords

#### Scenario: Same keyword is processed repeatedly
- **GIVEN** a peer company is already associated with a platform keyword
- **WHEN** another raw row or retry attempts to associate the same peer company with the same platform keyword
- **THEN** the system SHALL keep exactly one peer-company-to-keyword relation for that pair
- **AND** the operation SHALL remain idempotent

### Requirement: Peer company source evidence SHALL remain traceable

The system SHALL preserve source evidence linking every cleaned peer company back to the contributing Lixiaoyun raw rows.

#### Scenario: Raw row contributes to a peer company
- **GIVEN** a `lixiaoyun_raw_companies` row is cleaned into a peer company
- **WHEN** the clean operation completes
- **THEN** the system SHALL create or retain a peer source relation referencing the raw company id
- **AND** the relation SHALL allow admin/debug flows to trace the peer company back to raw evidence

#### Scenario: Same raw source is processed again
- **GIVEN** a raw company row is already linked to a peer company as source evidence
- **WHEN** cleanup or backfill processes the same raw row again
- **THEN** the system SHALL NOT create duplicate source evidence rows
- **AND** the operation SHALL remain idempotent

### Requirement: Lixiaoyun raw writes SHALL synchronously update the peer company layer

The system SHALL update the peer company layer when Lixiaoyun raw company rows are inserted or updated by the collection service.

#### Scenario: Collection service upserts a Lixiaoyun raw company
- **GIVEN** the collection service successfully upserts a `lixiaoyun_raw_companies` row
- **WHEN** the raw write transaction runs
- **THEN** the system SHALL upsert the corresponding peer company in the same transaction
- **AND** the system SHALL upsert peer keyword and source relations in the same transaction

#### Scenario: Peer cleanup worker is not running
- **GIVEN** no dedicated peer cleanup worker is running
- **WHEN** a new Lixiaoyun raw company is written through the collection service
- **THEN** the peer company layer SHALL still be updated by the raw write path
- **AND** the system SHALL NOT require a 5-minute polling peer cleanup process for the main path

### Requirement: Historical Lixiaoyun raw rows SHALL be backfillable into peer companies

The system SHALL provide a backfill path that rebuilds the peer company layer from existing `lixiaoyun_raw_companies` rows using the same deduplication rules as the online write path.

#### Scenario: Backfill runs against existing raw rows
- **GIVEN** historical `lixiaoyun_raw_companies` rows already exist
- **WHEN** an operator runs the peer company backfill
- **THEN** the system SHALL create or update peer companies from those rows
- **AND** the system SHALL create or retain keyword and source relations
- **AND** repeated backfill runs SHALL be idempotent

#### Scenario: Backfill dry run is requested
- **GIVEN** an operator runs the peer company backfill in dry-run mode
- **WHEN** the command completes
- **THEN** the system SHALL report candidate raw rows and expected peer/source/keyword changes
- **AND** the system SHALL NOT mutate peer company tables

### Requirement: Admin peer company API SHALL return deduplicated peer companies

The Admin peer company list API SHALL return one row per peer company rather than one row per Lixiaoyun raw company.

#### Scenario: Admin lists peer companies
- **WHEN** an admin requests the peer company list
- **THEN** each response item SHALL represent one deduplicated peer company
- **AND** each item SHALL include `id`, `name`, `english_name`, `domain` or `website_host`, `keywords`, `raw_count`, and latest/first seen timestamps
- **AND** `keywords` SHALL be an array of keyword objects containing platform keyword identity and display text

#### Scenario: Admin filters by keyword
- **GIVEN** a peer company is associated with multiple platform keywords
- **WHEN** an admin filters the peer list by one of those keywords
- **THEN** the API SHALL include that peer company in the result
- **AND** the response item SHALL still include the full keyword array for the peer company

#### Scenario: Admin requests a page with no matching peers
- **WHEN** an admin peer company query has no matching peer companies
- **THEN** the API SHALL return an empty data array
- **AND** pagination metadata SHALL report zero matching rows

#### Scenario: Admin views contact count for a merged peer company
- **GIVEN** a peer company is linked to multiple Lixiaoyun raw rows
- **AND** those raw rows have contacts that may overlap by email or source contact id
- **WHEN** the Admin peer company cleaning API returns the peer company
- **THEN** the contact count SHALL count unique contacts across all linked raw rows
- **AND** contact identity SHALL prefer email, then `source_contact_id`, then raw contact id as fallback

#### Scenario: Admin filters by contact count
- **GIVEN** a peer company has a deduplicated peer-level contact count
- **WHEN** an admin filters the cleaning list by contact count
- **THEN** the API SHALL evaluate the filter against the peer-level deduplicated contact count

### Requirement: Admin peer company cleaning page SHALL be implemented with Next.js while preserving existing list and filter semantics

The Admin SHALL add a separate peer company cleaning page implemented with Next.js for this change, while keeping the original peer company page unchanged. The new cleaning page SHALL keep default list columns and filter conditions consistent with the existing peer company page.

#### Scenario: Peer company has multiple keywords
- **GIVEN** the Admin peer company API returns one peer item with multiple keywords
- **WHEN** the Next.js Admin peer company console renders the table
- **THEN** the page SHALL display one table row for that peer company
- **AND** the keyword column SHALL display the returned keywords as multiple tags or equivalent compact labels

#### Scenario: Admin opens the peer company cleaning list
- **WHEN** an admin opens the Next.js peer company cleaning page
- **THEN** the default table columns SHALL match the existing peer company page's column semantics
- **AND** the page SHALL NOT add lookup status, failure reason, last lookup time, buyer count, Tendata result count, or already-looked-up columns by default

#### Scenario: Admin opens the original peer company list
- **WHEN** an admin opens the original peer company page
- **THEN** the original page SHALL keep its existing raw-company behavior
- **AND** this change SHALL NOT require replacing, deleting, or rewriting that page

#### Scenario: Admin filters peer companies
- **WHEN** an admin uses filters on the Next.js peer company page
- **THEN** the available filter conditions SHALL match the existing peer company page's filter semantics

#### Scenario: Peer company has no displayable keyword
- **GIVEN** the Admin peer company API returns a peer item with an empty keyword array
- **WHEN** the Next.js Admin peer company console renders the keyword column
- **THEN** the page SHALL display an empty-state marker such as `—`
- **AND** the row SHALL remain visible

#### Scenario: Existing Admin app still exists
- **GIVEN** the current Admin application is still Vite-based
- **WHEN** this change introduces the Next.js peer company cleaning page
- **THEN** the system SHALL provide an entry, redirect, or coexistence path from the existing Admin experience
- **AND** the system SHALL NOT require migrating the entire Admin application to Next.js in this change

#### Scenario: Admin opens peer company details
- **WHEN** an admin opens a peer company cleaning detail view
- **THEN** the detail view SHALL show whether the peer company has an English name
- **AND** it SHALL show raw row count
- **AND** it SHALL show keyword count
- **AND** it SHALL NOT show lookup status, failure reason, latest hit time, buyer count, Tendata result count, or already-looked-up state

### Requirement: Peer company identity decisions SHALL be explainable

The system SHALL expose enough metadata to explain why raw rows were merged into a peer company.

#### Scenario: Peer company is created from website identity
- **GIVEN** a peer company is created or updated from a raw row with a usable website host
- **WHEN** the peer company is stored
- **THEN** the system SHALL retain that the identity came from website normalization
- **AND** the system SHALL retain the normalized identity value

#### Scenario: Peer company is created from source id fallback
- **GIVEN** a peer company is created or updated from a raw row without usable website identity
- **AND** the raw row has a usable `source_id`
- **WHEN** the peer company is stored
- **THEN** the system SHALL retain that the identity came from Lixiaoyun `source_id`
- **AND** the system SHALL retain enough metadata for Admin/debug flows to distinguish fallback identity from website identity

#### Scenario: Merged raw rows show identity conflicts
- **GIVEN** raw rows mapped to the same peer company contain conflicting business identity evidence such as different legal representatives, social credit codes, or company names
- **WHEN** the Admin peer company API or debug path reports the peer company
- **THEN** the system SHALL expose a conflict indicator, low-confidence marker, or equivalent diagnostic signal

### Requirement: Admin peer company cleaning views SHALL expose peer cleaning aggregates without Tendata lookup status fields

The Admin peer company cleaning API or page SHALL expose peer cleaning aggregates needed to understand deduplicated peer rows, while excluding Tendata lookup status fields from the Admin page in this change.

#### Scenario: Admin lists peer companies
- **WHEN** an admin requests the peer company cleaning list
- **THEN** each response item SHALL preserve the existing peer company list field semantics
- **AND** it SHALL include enough data to render keyword arrays for deduplicated peer companies
- **AND** it SHALL NOT require rendering lookup status, failure reason, latest lookup time, buyer count, Tendata result count, or already-looked-up state

#### Scenario: Admin reviews peer company pool health
- **WHEN** an admin or operator reviews peer company cleaning results after backfill
- **THEN** the system SHALL provide statistics for raw row count, peer company count, deduplication rate, and English-name coverage
- **AND** those statistics SHALL be derivable from API responses, backfill output, or an equivalent operational report
