## ADDED Requirements

### Requirement: Restrained surfaces
TON workspace surfaces SHALL use flat backgrounds with a hairline border and no drop shadow, a small corner radius, and no hover lift; decorative gradients SHALL NOT be used.

#### Scenario: Card hover
- **WHEN** a user hovers an interactive card or row
- **THEN** only its border or background tone changes and the element does not move

### Requirement: Decoration only with meaning
Icon tiles, uppercase labels and pills SHALL appear only where they carry information: icons to recognize an object type, uppercase labels for table headers and group labels, pills for states.

#### Scenario: Metric card
- **WHEN** a metric is displayed
- **THEN** it shows label, value and detail without a decorative icon tile

### Requirement: Correct status semantics
Status colors SHALL match meaning: success for completed or ready, warning for attention, danger for failure, neutral for informational states.

#### Scenario: Completed report
- **WHEN** a report run finished successfully
- **THEN** its status is shown in the success tone, not warning

### Requirement: Numbers never wrap
Currency and quantity values SHALL render on a single line with tabular numerals, and containers SHALL size so that the largest expected value fits.

#### Scenario: Drawer metrics
- **WHEN** the composition drawer shows −R$ 1.048.837,46
- **THEN** the value is displayed on one line without truncation

### Requirement: Composition drawer as a readable table
Opening a DRE line SHALL show a wide drawer with the line total and a table of entries with date, unit name, NG account, document, history, amount and source location (sheet and row), stating the source file once.

#### Scenario: Fuel line in June
- **WHEN** a user opens Combustível for June 2026
- **THEN** the drawer lists 36 entries in a table with unit names and histories, and the file name appears once in the header

### Requirement: Business language only
Client screens SHALL show names instead of internal codes or e-mail addresses whenever a name exists, and SHALL NOT show internal identifiers such as run_id or enum values.

#### Scenario: Decision author
- **WHEN** a decision was recorded by a user with a display name
- **THEN** the activity list shows the name, not the e-mail
