from enum import StrEnum


class Environment(StrEnum):
    DEVELOPMENT = 'development'
    TEST = 'test'
    PRODUCTION = 'production'


class ClassificationLevel(StrEnum):
    PUBLIC = 'PUBLIC'
    INTERNAL = 'INTERNAL'
    CONFIDENTIAL = 'CONFIDENTIAL'
    SECRET = 'SECRET'


class BackupStatus(StrEnum):
    PROCESSING = 'PROCESSING'
    ACTIVE = 'ACTIVE'
    FAILED = 'FAILED'
    IRREVERSIBLE = 'IRREVERSIBLE'


class IncidentLevel(StrEnum):
    NORMAL = 'NORMAL'
    QUARANTINE = 'QUARANTINE'
    LOCKDOWN = 'LOCKDOWN'


class AlertSeverity(StrEnum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'


class AlertStatus(StrEnum):
    OPEN = 'OPEN'
    ACKNOWLEDGED = 'ACKNOWLEDGED'
    RESOLVED = 'RESOLVED'
