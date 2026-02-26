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
