from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Digest(_message.Message):
    __slots__ = ("hash", "size_bytes")
    HASH_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    hash: str
    size_bytes: int
    def __init__(self, hash: _Optional[str] = ..., size_bytes: _Optional[int] = ...) -> None: ...

class FindMissingBlobsRequest(_message.Message):
    __slots__ = ("blob_digests",)
    BLOB_DIGESTS_FIELD_NUMBER: _ClassVar[int]
    blob_digests: _containers.RepeatedCompositeFieldContainer[Digest]
    def __init__(self, blob_digests: _Optional[_Iterable[_Union[Digest, _Mapping]]] = ...) -> None: ...

class FindMissingBlobsResponse(_message.Message):
    __slots__ = ("missing_blob_digests",)
    MISSING_BLOB_DIGESTS_FIELD_NUMBER: _ClassVar[int]
    missing_blob_digests: _containers.RepeatedCompositeFieldContainer[Digest]
    def __init__(self, missing_blob_digests: _Optional[_Iterable[_Union[Digest, _Mapping]]] = ...) -> None: ...

class BatchReadBlobsRequest(_message.Message):
    __slots__ = ("digests",)
    DIGESTS_FIELD_NUMBER: _ClassVar[int]
    digests: _containers.RepeatedCompositeFieldContainer[Digest]
    def __init__(self, digests: _Optional[_Iterable[_Union[Digest, _Mapping]]] = ...) -> None: ...

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
        def __init__(self, digest: _Optional[_Union[Digest, _Mapping]] = ..., data: _Optional[bytes] = ..., status_code: _Optional[int] = ..., status_message: _Optional[str] = ...) -> None: ...
    RESPONSES_FIELD_NUMBER: _ClassVar[int]
    responses: _containers.RepeatedCompositeFieldContainer[BatchReadBlobsResponse.Response]
    def __init__(self, responses: _Optional[_Iterable[_Union[BatchReadBlobsResponse.Response, _Mapping]]] = ...) -> None: ...

class BatchUpdateBlobsRequest(_message.Message):
    __slots__ = ("requests",)
    class Request(_message.Message):
        __slots__ = ("digest", "data")
        DIGEST_FIELD_NUMBER: _ClassVar[int]
        DATA_FIELD_NUMBER: _ClassVar[int]
        digest: Digest
        data: bytes
        def __init__(self, digest: _Optional[_Union[Digest, _Mapping]] = ..., data: _Optional[bytes] = ...) -> None: ...
    REQUESTS_FIELD_NUMBER: _ClassVar[int]
    requests: _containers.RepeatedCompositeFieldContainer[BatchUpdateBlobsRequest.Request]
    def __init__(self, requests: _Optional[_Iterable[_Union[BatchUpdateBlobsRequest.Request, _Mapping]]] = ...) -> None: ...

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
        def __init__(self, digest: _Optional[_Union[Digest, _Mapping]] = ..., status_code: _Optional[int] = ..., status_message: _Optional[str] = ...) -> None: ...
    RESPONSES_FIELD_NUMBER: _ClassVar[int]
    responses: _containers.RepeatedCompositeFieldContainer[BatchUpdateBlobsResponse.Response]
    def __init__(self, responses: _Optional[_Iterable[_Union[BatchUpdateBlobsResponse.Response, _Mapping]]] = ...) -> None: ...
