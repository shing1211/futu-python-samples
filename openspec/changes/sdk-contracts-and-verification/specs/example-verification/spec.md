# Spec Delta

## Purpose

Defines the observable contract of the example verification harness — how a pass or failure verdict is derived, which outcomes must never be reported as a pass, and what a green run is permitted to assert — so that a successful run constitutes evidence rather than an absence of complaints.

## ADDED Requirements

### Requirement: Verdicts are derived from process outcome, not from output text

A verdict SHALL be derived from the example process's termination status together with an inspection of its captured output. The harness SHALL NOT infer a pass by searching the output for terms that indicate a failure.

Absence of failure-indicating text in a failing process SHALL NOT be reported as a pass.

#### Scenario: A process fails with no recognizable output

- **WHEN** an example process terminates unsuccessfully and its captured output contains no recognized failure indicator
- **THEN** the harness reports the outcome as a failure
- **AND** the harness does not report it as a pass

#### Scenario: A process succeeds

- **WHEN** an example process terminates successfully
- **THEN** the harness reports the outcome as a pass

#### Scenario: Output is discarded

- **WHEN** an example process produces diagnostic output on its standard output stream
- **THEN** the harness inspects that output as part of deriving the verdict
- **AND** the harness does not discard it without inspection

### Requirement: Verification is capable of failing

The harness SHALL be able to report a failing overall result for a set of examples whose code is broken. A harness in which every reachable outcome resolves to a pass does not satisfy this requirement.

The harness SHALL NOT contain declared example classifications that are never consulted when deriving a verdict.

#### Scenario: A declared classification is never used

- **WHEN** the harness declares a set of examples requiring distinct handling
- **AND** that set is not consulted when deriving any verdict
- **THEN** the declaration is a defect
- **AND** it is not retained as documentation of intent

#### Scenario: Every outcome resolves to a pass

- **WHEN** no input to the harness can produce a failing overall result
- **THEN** the harness does not satisfy this capability

### Requirement: Outcomes blocked by external state are distinct from passes

Where an example cannot complete because of external state outside the example's control — an unavailable gateway, an unauthenticated session, or a gateway-side cooldown after repeated failed unlock attempts — the harness SHALL report a distinct outcome that is not a pass.

Such an outcome SHALL NOT increment the pass count, and SHALL NOT be reported as a pass with an annotation. A pass count SHALL mean that the example ran and demonstrated its behavior.

#### Scenario: An example is blocked by a gateway cooldown

- **WHEN** an example is refused because repeated unlock attempts triggered a gateway-side cooldown
- **THEN** the harness reports it as blocked
- **AND** the pass count does not include it
- **AND** the harness does not report it as a pass with an annotation

#### Scenario: The pass count is reported

- **WHEN** the harness reports a total
- **THEN** the pass count reflects only examples that ran and demonstrated their behavior
- **AND** blocked and failed examples are counted separately from passes

### Requirement: Examples that cannot signal failure are treated as defects

Where an example suppresses all errors such that it terminates successfully regardless of whether its API calls succeeded, the harness SHALL treat that example as defective rather than as passing. An example whose own error handling prevents any failure from being observable does not satisfy this capability.

Suppression of errors SHALL NOT be treated as acceptable because the example reports a successful exit status.

#### Scenario: An example suppresses every error

- **WHEN** an example catches exceptions without recording or re-raising them
- **AND** the example therefore terminates successfully whether or not its API calls succeeded
- **THEN** the harness treats the example as defective
- **AND** the harness does not report it as a pass

#### Scenario: A suppressed error hides a real failure

- **WHEN** an example's API call raises and the example suppresses the error
- **THEN** the harness does not report the example as a pass
- **AND** the defect is attributable to the example, not to the harness's classification

### Requirement: Examples expected not to terminate declare that expectation explicitly

Where an example is designed to run until an external limit — a push subscription loop, or any unbounded wait — the harness SHALL treat the example's classification as authoritative for whether its termination is expected, and that classification SHALL be consulted when deriving the verdict.

A timeout SHALL be reported as the expected outcome only for examples declared to be unbounded, and SHALL be reported as a failure for every other example.

#### Scenario: A declared unbounded example times out

- **WHEN** an example declared as unbounded is terminated by the harness's time limit
- **THEN** the harness reports the expected outcome
- **AND** the outcome is distinguishable from a pass produced by successful completion

#### Scenario: A bounded example times out

- **WHEN** an example not declared as unbounded is terminated by the harness's time limit
- **THEN** the harness reports a failure

### Requirement: The verified set is explicit and matches the repository

The harness SHALL determine the set of examples to verify from the repository's example directories rather than from a list maintained separately, and SHALL report any example present in the repository but not verified.

The harness SHALL report which examples it verified, so that an example absent from a run is distinguishable from an example that passed.

#### Scenario: An example exists but is not verified

- **WHEN** an example directory exists in the repository
- **AND** the harness does not run it
- **THEN** the harness reports the example as not verified
- **AND** the omission does not appear as a pass

#### Scenario: The run completes

- **WHEN** a verification run finishes
- **THEN** the reported verified set is derived from the repository's example directories
- **AND** every example directory is accounted for as passed, failed, blocked, or not verified

### Requirement: A source check asserts the property the behavior depends on

Where a static check asserts a source property, it SHALL assert the property the example's behavior depends on, and SHALL NOT assert a proxy that a broken example can still satisfy.

A check that passes for an example which cannot run satisfies the letter of its property and fails its purpose.

#### Scenario: A check asserts ordering where reachability is what matters

- **WHEN** a check asserts that a path is added before an import
- **AND** the added path does not make that import resolve
- **THEN** the check reports the example
- **AND** does not accept it because the ordering was correct

#### Scenario: An example inserts several paths

- **WHEN** an example adds more than one directory to the search path
- **THEN** the check accepts the example if at least one added directory makes the required import resolve
- **AND** does not require every added directory to do so

### Requirement: Declared execution classes match the example's actual control flow

Where an example is classified as not terminating, the classification SHALL be justified by the example's control flow containing an unbounded loop. An example that performs a bounded wait SHALL NOT be classified as not terminating, and SHALL be given a time limit above its own runtime instead.

Misclassifying a bounded example as not terminating converts a genuine hang into an expected outcome, which is the failure mode this capability exists to prevent.

#### Scenario: A bounded example with a long wait

- **WHEN** an example waits a fixed duration and then finishes
- **THEN** it is given a time limit above that duration
- **AND** it is not classified as not terminating

#### Scenario: An example is classified as not terminating

- **WHEN** an example is classified as not terminating
- **THEN** its source contains an unbounded loop that justifies the classification

#### Scenario: A classification is both bounded and unbounded

- **WHEN** an example appears in both the time-limited and not-terminating classifications
- **THEN** the classifications are in conflict
- **AND** the conflict is reported rather than resolved by precedence