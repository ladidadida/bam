from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper

DESCRIPTOR: _descriptor.FileDescriptor

class ServerCapabilities(_message.Message):
    __slots__ = (
        "cache_capabilities",
        "execution_capabilities",
        "low_api_version",
        "high_api_version",
    )
    CACHE_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    LOW_API_VERSION_FIELD_NUMBER: _ClassVar[int]
    HIGH_API_VERSION_FIELD_NUMBER: _ClassVar[int]
    cache_capabilities: CacheCapabilities
    execution_capabilities: ExecutionCapabilities
    low_api_version: ApiVersion
    high_api_version: ApiVersion
    def __init__(
        self,
        cache_capabilities: CacheCapabilities | _Mapping | None = ...,
        execution_capabilities: ExecutionCapabilities | _Mapping | None = ...,
        low_api_version: ApiVersion | _Mapping | None = ...,
        high_api_version: ApiVersion | _Mapping | None = ...,
    ) -> None: ...

class CacheCapabilities(_message.Message):
    __slots__ = (
        "digest_function",
        "action_cache_update_capabilities",
        "max_batch_total_size_bytes",
        "compression_supported",
    )
    DIGEST_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    ACTION_CACHE_UPDATE_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    MAX_BATCH_TOTAL_SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    COMPRESSION_SUPPORTED_FIELD_NUMBER: _ClassVar[int]
    digest_function: _containers.RepeatedScalarFieldContainer[DigestFunction.Value]
    action_cache_update_capabilities: ActionCacheUpdateCapabilities
    max_batch_total_size_bytes: int
    compression_supported: bool
    def __init__(
        self,
        digest_function: _Iterable[DigestFunction.Value | str] | None = ...,
        action_cache_update_capabilities: ActionCacheUpdateCapabilities | _Mapping | None = ...,
        max_batch_total_size_bytes: int | None = ...,
        compression_supported: bool = ...,
    ) -> None: ...

class ActionCacheUpdateCapabilities(_message.Message):
    __slots__ = ("update_enabled",)
    UPDATE_ENABLED_FIELD_NUMBER: _ClassVar[int]
    update_enabled: bool
    def __init__(self, update_enabled: bool = ...) -> None: ...

class ExecutionCapabilities(_message.Message):
    __slots__ = ("digest_function", "exec_enabled")
    DIGEST_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    EXEC_ENABLED_FIELD_NUMBER: _ClassVar[int]
    digest_function: DigestFunction.Value
    exec_enabled: bool
    def __init__(
        self, digest_function: DigestFunction.Value | str | None = ..., exec_enabled: bool = ...
    ) -> None: ...

class DigestFunction(_message.Message):
    __slots__ = ()
    class Value(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[DigestFunction.Value]
        SHA256: _ClassVar[DigestFunction.Value]
        SHA1: _ClassVar[DigestFunction.Value]
        MD5: _ClassVar[DigestFunction.Value]
        VSO: _ClassVar[DigestFunction.Value]
        SHA384: _ClassVar[DigestFunction.Value]
        SHA512: _ClassVar[DigestFunction.Value]
        MURMUR3: _ClassVar[DigestFunction.Value]

    UNKNOWN: DigestFunction.Value
    SHA256: DigestFunction.Value
    SHA1: DigestFunction.Value
    MD5: DigestFunction.Value
    VSO: DigestFunction.Value
    SHA384: DigestFunction.Value
    SHA512: DigestFunction.Value
    MURMUR3: DigestFunction.Value
    def __init__(self) -> None: ...

class ApiVersion(_message.Message):
    __slots__ = ("major", "minor", "patch", "prerelease")
    MAJOR_FIELD_NUMBER: _ClassVar[int]
    MINOR_FIELD_NUMBER: _ClassVar[int]
    PATCH_FIELD_NUMBER: _ClassVar[int]
    PRERELEASE_FIELD_NUMBER: _ClassVar[int]
    major: int
    minor: int
    patch: int
    prerelease: str
    def __init__(
        self,
        major: int | None = ...,
        minor: int | None = ...,
        patch: int | None = ...,
        prerelease: str | None = ...,
    ) -> None: ...

class GetCapabilitiesRequest(_message.Message):
    __slots__ = ("instance_name",)
    INSTANCE_NAME_FIELD_NUMBER: _ClassVar[int]
    instance_name: str
    def __init__(self, instance_name: str | None = ...) -> None: ...
