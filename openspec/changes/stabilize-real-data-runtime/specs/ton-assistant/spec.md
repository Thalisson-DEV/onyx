## ADDED Requirements

### Requirement: Complete financial context for the requested scope
The assistant SHALL see every persisted DRE calculation for the requested period and scope on the latest normalization base, not a fixed number of most recent calculations per base.

#### Scenario: Many calculations on the same base
- **WHEN** 144 calculations exist on the latest base and the user asks for April at Mossoró-RN
- **THEN** the assistant retrieves the April Mossoró-RN calculation and reports its values

### Requirement: Analytical answer latency budget
The assistant SHALL answer the reference questions ("Como está o fechamento de junho?", "Quais pendências impedem a DRE?", "O que mudou depois das decisões?") in under 45 seconds at the 90th percentile on the local real base, using at most 8 tool calls per answer.

#### Scenario: Reference question
- **WHEN** the reference question set is run against the real base
- **THEN** each answer finishes within the budget and its numbers equal the corresponding screens

### Requirement: Grounding regression suite on real data
The project SHALL keep an automated suite that asks the reference questions and compares the numbers in the answer with the persisted read models, failing on any mismatch.

#### Scenario: Wrong number in answer
- **WHEN** an answer cites a DRE value that differs from the persisted calculation
- **THEN** the suite fails and names the question and the divergent value
