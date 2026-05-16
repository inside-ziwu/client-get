# cross-surface-company-filter-alignment Specification

## Purpose
TBD - created by archiving change align-tenant-company-admin-customer-filters. Update Purpose after archive.
## Requirements
### Requirement: Admin and tenant use the same base company filters
The system SHALL expose the same base V3 company filter dimensions on the admin customer data page, tenant company list, and tenant curated customers page.

#### Scenario: User compares available base filters
- **WHEN** a user opens the admin customer data page, tenant company list, or tenant curated customers page
- **THEN** all three pages MUST provide the same base filters for keyword, country/region, industry segment, product tags, data source, employee count range, founded date year range, import amount, import count, contact count range, and PCB supplier presence
- **AND** tenant-only filters such as score or private status MUST be visually and technically separated from the shared base filters if they remain available
- **AND** range controls MUST be grouped with a `～` separator instead of a second field label such as “止” or “截止”
- **AND** filter placeholder copy MUST describe user intent rather than implementation semantics such as “多选 OR”
- **AND** wrapped filter rows MUST have visible vertical spacing between rows
- **AND** filter controls MUST render as a flat set of operation items without visible category headings or keys such as “基础条件”, “区间条件”, or “租户专属”

### Requirement: Shared base filters use consistent parameter semantics
The system SHALL map shared base filters to consistent API parameter semantics across the admin customer data page, tenant company list, and tenant curated customers page.

#### Scenario: Multi-select base filter is applied
- **WHEN** a user selects multiple values for country, industry segment, product tags, or data source
- **THEN** the API request MUST represent those values as OR semantics
- **AND** admin customer data, tenant company list, and tenant curated customers requests MUST use the same value vocabulary for the selected filter

#### Scenario: Range base filter is applied
- **WHEN** a user enters founded date year, import amount, import count, employee count, or contact count bounds
- **THEN** the API request MUST preserve the same minimum and maximum semantics across admin customer data, tenant company list, and tenant curated customers

#### Scenario: Founded date filter is displayed
- **WHEN** any of the three covered pages renders the founded-date filter
- **THEN** the UI label MUST use “成立日期”
- **AND** the control MUST select years and submit `founded_year_from` / `founded_year_to`

#### Scenario: Contact count range is applied
- **WHEN** a user enters contact count minimum or maximum values
- **THEN** admin customer data, tenant company list, and tenant curated customers requests MUST use `contact_count_min` and `contact_count_max` as shared external parameters
- **AND** all covered backend paths MUST apply the same `contacts_count` minimum and maximum predicates
- **AND** all three UI surfaces MUST use numeric range controls as the primary contact-count filter control rather than fixed buckets

#### Scenario: Employee count range filter is applied
- **WHEN** a user enters employee count minimum or maximum values
- **THEN** admin customer data, tenant company list, and tenant curated customers requests MUST use `employee_count_min` and `employee_count_max` as shared external parameters
- **AND** each backend path MUST parse its current employee-count storage field into comparable numeric bounds before applying the range predicate

#### Scenario: PCB supplier presence filter is applied
- **WHEN** a user selects PCB supplier presence
- **THEN** shared frontend mapping MUST send `pcb_supplier_presence` with `has` or `none`
- **AND** all covered backend paths MUST use `pcb_supplier_presence` as the only shared PCB supplier filter parameter
- **AND** the legacy `pcb=yes` or `pcb=no` parameter MUST NOT remain part of the shared filter contract

### Requirement: Same base filter intent produces same clean-company match logic
The system SHALL evaluate shared base filters against the same clean-company fields and source tables on admin customer data, tenant company list, and tenant curated customers.

#### Scenario: Same base filters are submitted
- **WHEN** admin customer data, tenant company list, and tenant curated customers submit the same shared base filter values
- **THEN** all covered backend queries MUST apply equivalent predicates to `clean_companies` and `clean_company_sources`
- **AND** any result difference MUST be explainable by tenant visibility constraints, not by different filter semantics

### Requirement: Shared filter mapping is regression-tested
The system SHALL include automated coverage for shared filter mapping and backend filter semantics.

#### Scenario: Filter contract changes
- **WHEN** a shared base filter option, parameter, or bucket changes
- **THEN** tests MUST fail unless admin and tenant mapping and query semantics are updated together

