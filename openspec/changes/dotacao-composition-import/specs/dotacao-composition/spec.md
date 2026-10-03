## ADDED Requirements

### Requirement: Structure-specific deterministic profiles
The system SHALL read each dotação workbook with a versioned profile for its structure, extracting cost synthesis and price per service, ABC curve, BDI, social charges percentage, technical reserve percentage, category salaries, labour sizing by role, fleet sizing by vehicle type, hourly cost per vehicle, service quantities with unit of measure, and the contracting authority budget, each value with sheet and cell of origin.

#### Scenario: Mossoró workbook
- **WHEN** the Mossoró-RN dotação is processed
- **THEN** the extraction includes BDI, social charges, technical reserve, ABC curve, DP-01 headcount and hourly costs per vehicle type with their cells

#### Scenario: Expected sheet missing
- **WHEN** a workbook lacks a sheet the profile expects
- **THEN** a diagnostic names the sheet and no value for it is guessed

### Requirement: Human-confirmed extraction feeds the contract master
An extracted dotação version SHALL feed the contract master Econômico-operacional block only after a Controladoria user confirms it, and confirmation SHALL be versioned and audited.

#### Scenario: Unconfirmed extraction
- **WHEN** an extraction exists but is not confirmed
- **THEN** analyses that need dotação data remain blocked with "dotação extraída aguardando confirmação"

### Requirement: Planned contract margin
The system SHALL compute the planned contract margin as (contracting authority monthly budget − Vale Norte monthly budget) ÷ contracting authority monthly budget from the confirmed dotação, showing both amounts and the cells used.

#### Scenario: Mossoró planned margin
- **WHEN** the confirmed Mossoró-RN dotação has authority budget R$ 4.525.843,89 and Vale Norte budget R$ 3.761.365,15 per month
- **THEN** the planned margin is 16,89% (R$ 764.478,74 per month)
