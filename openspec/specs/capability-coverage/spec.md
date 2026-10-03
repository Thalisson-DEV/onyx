# capability-coverage Specification

## Purpose
Linha de base da cobertura do Prompt Mestre exposta pelo produto: registrar uma capability não a
torna operacional. Código: `backend/onyx/ton/agent/{capabilities,registry}.py`,
`GET /api/ton/agent/capabilities`, `/routines`, `/specialists`, `web/src/views/ton/CoveragePage`.
Estado em 2026-10-02: S10 OPERATIONAL, T4 PARTIAL, demais S1–S9, T1–T3, T5–T30
NOT_IMPLEMENTED; R3 operacional, R1, R2, R4–R9 bloqueadas; 3 de 9 especialistas atuando.

## Requirements

### Requirement: Registration never activates a rule
The system SHALL report each Prompt Mestre rule (S1–S10, T1–T30), routine (R1–R9) and specialist with a status derived from an existing executor and available sources, and SHALL report NOT_IMPLEMENTED or BLOCKED otherwise, with the missing source and next dependency.

#### Scenario: Rule with only a catalogue entry
- **WHEN** a rule has a name and owner but no executor
- **THEN** its status is "Não implementada" and the reason states that NG review does not equal this test

### Requirement: Coverage updates with real executors
The system SHALL change a capability status only in the same change that delivers its executor and tests, and every OpenSpec change that implements an S, T or R code SHALL update `capabilities.py` or `registry.py` accordingly.

#### Scenario: New executor delivered
- **WHEN** a change ships the executor for T6 with tests on real data
- **THEN** T6 moves to OPERATIONAL (or PARTIAL with reason) in the coverage API in that change
