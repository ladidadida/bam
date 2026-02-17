from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class Digest(_message.Message):
    __slots__ = ("hash", "size_bytes")
    HASH_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    hash: str
    size_bytes: int
    def __init__(self, hash: str | None = ..., size_bytes: int | None = ...) -> None: ...

class FindMissingBlobsRequest(_message.Message):
    __slots__ = ("blob_digests",)
    BLOB_DIGESTS_FIELD_NUMBER: _ClassVar[int]
    blob_digests: _containers.RepeatedCompositeFieldContainer[Digest]
    def __init__(self, blob_digests: _Iterable[Digest | _Mapping] | None = ...) -> None: ...

class FindMissingBlobsResponse(_message.Message):
    __slots__ = ("missing_blob_digests",)
    MISSING_BLOB_DIGESTS_FIELD_NUMBER: _ClassVar[int]
    missing_blob_digests: _containers.RepeatedCompositeFieldContainer[Digest]
    def __init__(self, missing_blob_digests: _Iterable[Digest | _Mapping] | None = ...) -> None: ...

class BatchReadBlobsRequest(_message.Message):
    __slots__ = ("digests",)
    DIGESTS_FIELD_NUMBER: _ClassVar[int]
    digests: _containers.RepeatedCompositeFieldContainer[Digest]
    def __init__(self, digests: _Iterable[Digest | _Mapping] | None = ...) -> None: ...

class BatchReadBlobsResponse(_message.Message):
    __slots__ = ("responses",)
    class Response(_message.Message):
        __slots__ = ("digest", "data", "status_code", "status_message")
        DIGEST_FIELD_NUMBER: _ClassVar[int]
        DATA_FIELD_NUMBER: _ClassVar[int]
        STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
        STATUS_MESSAGE_FIELD_NUMBER: _ClassVar[int]
        digest: Digest
        data: bytes
        status_code: int
        status_message: str
        def __init__(self, digest: Digest | _Mapping | None = ..., data: bytes | None = ..., status_code: int | None = ..., status_message: str | None = ...) -> None: ...
    RESPONSES_FIELD_NUMBER: _ClassVar[int]
    responses: _containers.RepeatedCompositeFieldContainer[BatchReadBlobsResponse.Response]
    def __init__(self, responses: _Iterable[BatchReadBlobsResponse.Response | _Mapping] | None = ...) -> None: ...

class BatchUpdateBlobsRequest(_message.Message):
    __slots__ = ("requests",)
    class Request(_message.Message):
        __slots__ = ("digest", "data")
        DIGEST_FIELD_NUMBER: _ClassVar[int]
        DATA_FIELD_NUMBER: _ClassVar[int]
        digest: Digest
        data: bytes
        def __init__(self, digest: Digest | _Mapping | None = ..., data: bytes | None = ...) -> None: ...
    REQUESTS_FIELD_NUMBER: _ClassVar[int]
    requests: _containers.RepeatedCompositeFieldContainer[BatchUpdateBlobsRequest.Request]
    def __init__(self, requests: _Iterable[BatchUpdateBlobsRequest.Request | _Mapping] | None = ...) -> None: ...

class BatchUpdateBlobsResponse(_message.Message):
    __slots__ = ("responses",)
    class Response(_message.Message):
        __slots__ = ("digest", "status_code", "status_message")
        DIGEST_FIELD_NUMBER: _ClassVar[int]
        STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
        STATUS_MESSAGE_FIELD_NUMBER: _ClassVar[int]
        digest: Digest
        status_code: int
        status_message: str
        def __init__(self, digest: Digest | _Mapping | None = ..., status_code: int | None = ..., status_message: str | None = ...) -> None: ...
    RESPONSES_FIELD_NUMBER: _ClassVar[int]
    responses: _containers.RepeatedCompositeFieldContainer[BatchUpdateBlobsResponse.Response]
    def __init__(self, responses: _Iterable[BatchUpdateBlobsResponse.Response | _Mapping] | None = ...) -> None: ...
