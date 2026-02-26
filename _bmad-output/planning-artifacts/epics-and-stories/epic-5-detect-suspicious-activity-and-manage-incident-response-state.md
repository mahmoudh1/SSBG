# Epic 5: Detect Suspicious Activity and Manage Incident Response State

**Epic Goal:** Enable the system and responders to detect suspicious restore behavior, create alerts, and enforce staged incident controls.

**User Value:** Suspicious activity can be detected and contained before mass exfiltration.

**Depends On:** Epics 1-4 (Epics 2-3 provide the monitored restore activity)

## Story 5.1 Evaluate Monitoring Rules and Create Alerts

**User Story:** As a security administrator, I want suspicious behavior detection rules to generate alerts so risky activity is surfaced quickly.

**Traceability:** FR-13, UJ-03/UJ-04

**Dependencies:** Epic 3 restore flow events, Epic 4 audit/event recording foundations

**Acceptance Criteria:**
- Given monitored events match configured suspicious patterns, when thresholds are crossed, then alert records are created with rule ID, severity, and timestamp.
- Given no threshold breach occurs, when monitored events are processed, then no false alert is created for that rule.
- Given an alert is created, when processing completes, then alert creation is auditable.

## Story 5.2 Manage Incident Response State Transitions

**User Story:** As an incident responder, I want to view and change incident response levels so the system enforces the correct security posture.

**Traceability:** FR-14, FR-17, UJ-04

**Dependencies:** Epic 1 admin auth/authorization stories

**Acceptance Criteria:**
- Given an authorized responder, when the current incident level is requested, then the system returns the current level and relevant metadata.
- Given an authorized responder initiates an allowed transition, when the transition is applied, then the new incident level is persisted and audited.
- Given an invalid or unauthorized transition request, when it is processed, then the system denies the request with a documented error response.

## Story 5.3 Apply Incident-Level Restrictions Across Restore Workflows

**User Story:** As an incident responder, I want incident levels enforced in restore workflows so the system automatically restricts risky operations.

**Traceability:** FR-09, FR-14, UJ-03/UJ-04

**Dependencies:** Story 5.2, Epic 3 restore authorization flow

**Acceptance Criteria:**
- Given a restricted incident level is active, when a restore request is evaluated, then the system applies the documented restriction behavior.
- Given incident level changes, when subsequent restore requests occur, then enforcement behavior reflects the latest persisted level.
- Given restrictions are enforced, when outcomes are returned, then the reason is auditable and visible in the error/response contract.

## Story 5.4 Provide Admin Alert Review APIs

**User Story:** As a security administrator, I want authorized APIs to review and acknowledge alerts so I can manage incident response operations.

**Traceability:** FR-17, UJ-04

**Dependencies:** Story 5.1, Epic 1 admin auth/authorization stories

**Acceptance Criteria:**
- Given an authorized admin, when alert review endpoints are called, then alert data is returned in a consistent format.
- Given alert acknowledgment or status updates are performed, when the action completes, then the change is persisted and auditable.
- Given an unauthorized caller, when alert admin endpoints are called, then access is denied.
