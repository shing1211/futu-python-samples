# Spec Delta

## Purpose

Records the Futu OpenAPI SDK interfaces whose real behavior contradicts the official documentation, together with the evidence status of each claim, so that examples built on them are correct and any future divergence is detectable.

## ADDED Requirements

### Requirement: Return-shape claims carry an explicit evidence status

Every recorded claim about an SDK interface's return arity or shape SHALL state whether it has been confirmed by direct observation against a live gateway, and SHALL name the means of confirmation. A claim that cannot be confirmed SHALL be recorded as unconfirmed. A recorded claim SHALL NOT be presented as established fact while its status is unconfirmed.

This applies uniformly. A shape inferred from official documentation, inferred from existing example code, or recalled from prior use is unconfirmed unless directly observed.

#### Scenario: A shape is recorded without observation

- **WHEN** a claim about an interface's return shape is recorded
- **AND** the claim has not been confirmed by direct observation against a live gateway
- **THEN** the record states the claim is unconfirmed
- **AND** the record does not present the claim as established

#### Scenario: A shape is confirmed by observation

- **WHEN** a claim about an interface's return shape is confirmed by direct observation against a live gateway
- **THEN** the record states it is confirmed
- **AND** the record identifies the observation that confirmed it

### Requirement: Contradicted return shapes are recorded as open questions with a resolution method

When a recorded return shape and existing call sites disagree, the disagreement SHALL be recorded rather than resolved by assumption. The record SHALL state both readings, identify the call sites that contradict the recorded shape, and state the method by which the question can be settled.

Settling such a question requires a live OpenD gateway; it SHALL NOT be settled by inferring intent from the shape of surrounding code.

#### Scenario: Documentation and call sites disagree on return arity

- **WHEN** a recorded return shape omits a leading status code
- **AND** call sites unpack a leading status code from the same interface
- **THEN** the disagreement is recorded as an open question
- **AND** the record identifies the affected call sites
- **AND** the record states that resolution requires direct observation against a live gateway

#### Scenario: The question is settled

- **WHEN** the interface is observed against a live gateway
- **THEN** the record states the observed arity and shape
- **AND** the record is no longer marked as an open question
- **AND** the call sites that contradict the observed shape are brought into scope for correction

### Requirement: Call sites depending on a contradicted shape are within scope

A call site that depends on a return shape recorded as an open question SHALL be enumerated in the capability's scope. Such call sites SHALL NOT be treated as conforming merely because they execute without an unhandled error, and SHALL NOT be silently exempted from the specification.

#### Scenario: A call site contradicts the recorded shape

- **WHEN** a call site unpacks a value that the recorded shape does not contain
- **THEN** the call site is enumerated as within scope
- **AND** the call site is not recorded as conforming

#### Scenario: A call site is excused because it did not crash

- **WHEN** a contradicting call site executes without an unhandled error
- **THEN** it is not thereby recorded as conforming
- **AND** the open question remains open until observed

### Requirement: Enum members that do not exist are recorded with the working alternative

Where an enumeration member implied by the official documentation does not exist in the supported SDK, the capability SHALL record the member as absent and SHALL record the member or members that exist in its place. Where no equivalent exists, the capability SHALL record the capability as unavailable and examples SHALL guard the reference so that its absence does not raise.

#### Scenario: A documented enumeration member is absent

- **WHEN** an example references an enumeration member implied by the official documentation
- **AND** that member does not exist in the supported SDK
- **THEN** the capability records the member as absent
- **AND** the capability records the member that exists in its place

#### Scenario: No equivalent member exists

- **WHEN** a documented enumeration member has no equivalent in the supported SDK
- **THEN** the capability records the capability as unavailable
- **AND** examples referencing it guard the reference so absence does not raise

### Requirement: DataFrame access patterns that raise are recorded with a safe form

Where an access pattern on a returned DataFrame or Series raises, the capability SHALL record the pattern that raises together with the form that succeeds. Recorded safe forms SHALL be used by examples.

#### Scenario: Positional access on a non-integer index

- **WHEN** an example takes the last element of a Series whose index is not integer-based
- **THEN** it uses label-based positional access
- **AND** it does not use bracket access on the last position

#### Scenario: Truth-value testing of a DataFrame

- **WHEN** an example tests a DataFrame for truthiness
- **THEN** it tests for null and non-empty explicitly
- **AND** it does not rely on the DataFrame's truth value

### Requirement: Claims are scoped to a stated SDK version

Every claim in this capability SHALL state the SDK version or version range it was observed against. Because the project declares a minimum supported SDK version rather than an exact version, the capability SHALL state that claims are not automatically invalidated by a newer SDK, and SHALL record that a version increase is the trigger for re-verification.

#### Scenario: A newer SDK is installed

- **WHEN** the installed SDK version increases beyond the version a claim was observed against
- **THEN** the claim is flagged for re-verification
- **AND** the claim is not treated as invalidated or as confirmed by the version change alone

### Requirement: Confirmed return shapes record their full observed structure

Where a return shape has been observed, the record SHALL state the structure of the whole returned value, not only the structure of one field of it, and SHALL state the SDK version observed against. A claim confirmed at more than one SDK version SHALL record every version observed.

#### Scenario: A shape carries a leading status code and a nested tuple

- **WHEN** an interface is observed to return a leading status code followed by a nested tuple
- **THEN** the record states the outer arity and the nested arity separately
- **AND** the record does not present the nested tuple as the whole return value

#### Scenario: A shape is observed across the supported version range

- **WHEN** a shape is observed at both the minimum supported version and a later version
- **THEN** the record states that the shape held at both
- **AND** the record names each version observed against

### Requirement: A call site conforming to an observed shape is recorded as conforming

A call site that unpacks exactly the observed outer arity SHALL be recorded as conforming and SHALL NOT be listed as contradicting a recorded shape. Where the prose documentation describes only part of a returned value, the prose SHALL be identified as the incorrect record rather than the call site being identified as the defect.

#### Scenario: A call site already matches the observation

- **WHEN** a call site unpacks the observed outer arity
- **THEN** it is recorded as conforming
- **AND** it is not listed as contradicting the recorded shape

#### Scenario: Documentation describes only part of the return value

- **WHEN** the prose documentation omits a leading status code that the observation shows is present
- **THEN** the prose is identified as the incorrect record
- **AND** the conforming call sites are left unchanged