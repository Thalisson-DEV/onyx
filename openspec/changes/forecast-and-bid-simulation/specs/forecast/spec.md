## ADDED Requirements

### Requirement: Minimum history gate
Forecasts SHALL be produced only for scopes with at least six closed, readable competences; otherwise the system SHALL state the number available and that forecasting is unavailable.

#### Scenario: Four readable months
- **WHEN** a unit has four readable closed competences
- **THEN** the forecast is unavailable and the reason states four of six

### Requirement: Three scenarios with explicit premises
Every forecast SHALL present optimistic, base and pessimistic scenarios with versioned explicit premises (including named seasonality), and SHALL never be presented as certainty.

#### Scenario: Seasonality premise
- **WHEN** seasonality from the 2021/2022 collection history is used
- **THEN** it appears as a named premise in all three scenarios

### Requirement: Forecast versus actual
At each closing the system SHALL compare the previous forecast with the actual result and publish the deviation per scenario.

#### Scenario: Deviation published
- **WHEN** the September actual closes
- **THEN** the August forecast deviation for September is shown per scenario

### Requirement: Bid simulation
The bid simulator SHALL compute result and margin as proposed revenue minus labour, fleet, fuel, maintenance, third parties, administrative and taxes, using realized unit costs of comparable units, and SHALL output the minimum price for the target margin and the value-destruction point.

#### Scenario: Target margin 15%
- **WHEN** a user simulates a bid with target margin 15%
- **THEN** the simulator shows the minimum price, the value-destruction price and the comparable units used
