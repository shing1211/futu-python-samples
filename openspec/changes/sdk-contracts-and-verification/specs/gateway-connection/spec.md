# Spec Delta

## Purpose

Defines how OpenD connection settings are resolved and validated, so that a misconfigured RSA key or an ambiguous host entry produces an immediate, actionable error instead of an indefinite retry that only manifests as a timeout.

## ADDED Requirements

### Requirement: RSA key configuration is validated before a connection is attempted

When RSA is enabled for a host and the configured RSA private key is missing or unreadable, the system SHALL raise an error before attempting the protocol handshake. That error SHALL identify the key path that was tried and SHALL name the configuration variables that set it.

The system SHALL NOT fall through to a connection attempt when the key cannot be read, because the handshake cannot succeed and the attempt does not return.

#### Scenario: RSA enabled with a key path that does not exist

- **WHEN** a connection is requested with RSA enabled
- **AND** the configured RSA private key path does not exist or is not readable
- **THEN** an error is raised before the handshake is attempted
- **AND** the error names the key path that was tried
- **AND** the error names the variables that configure the key and the host

#### Scenario: RSA enabled with a readable key

- **WHEN** a connection is requested with RSA enabled
- **AND** the configured RSA private key is readable
- **THEN** no configuration error is raised
- **AND** the connection proceeds

#### Scenario: RSA disabled

- **WHEN** a connection is requested with RSA disabled
- **THEN** no RSA key is read
- **AND** a missing RSA key path does not raise a configuration error

### Requirement: A misconfigured gateway fails within a bounded time

A configuration error SHALL be reported as an error rather than as an indefinite retry. Where the SDK retries an unsuccessful handshake internally, the system SHALL establish a usable connection or raise, and SHALL NOT rely on a handshake failure returning so that a fallback attempt can run.

A caller SHALL NOT be left waiting on a retry loop in order to discover that its configuration is wrong.

#### Scenario: The handshake never succeeds

- **WHEN** the gateway refuses the handshake repeatedly
- **THEN** the system surfaces the failure as an error within the configured time bound
- **AND** does not leave the caller inside the SDK's internal retry loop

#### Scenario: A fallback attempt is still required

- **WHEN** a first connection attempt fails and a fallback is configured
- **THEN** the fallback is attempted
- **AND** the fallback is not defeated by the first attempt failing to return

### Requirement: Single-host and host-list configuration agree on RSA

Where a host is configured through the single-host variable and where it is configured through the host-list variable, the system SHALL apply the same default assumption about whether that host uses RSA. The assumption SHALL be documented, and the documented assumption SHALL state that it applies to local gateways as well as remote ones.

A local gateway SHALL NOT be assumed not to use RSA, because a local gateway configured with a protocol-encryption key requires RSA.

#### Scenario: Same host expressed two ways

- **WHEN** one host is configured through the single-host variable
- **AND** the same host is configured through the host-list variable without an explicit RSA flag
- **THEN** both configurations resolve to the same RSA assumption

#### Scenario: The RSA flag is stated explicitly

- **WHEN** a host entry states whether it uses RSA
- **THEN** that stated value is used
- **AND** it overrides the default assumption

#### Scenario: The documented assumption

- **WHEN** the documentation describes the default RSA assumption
- **THEN** it states that the assumption applies to local gateways as well as remote ones