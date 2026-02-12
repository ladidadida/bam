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

class ActionResult(_message.Message):
    __slots__ = ("output_files", "output_directories", "exit_code", "stdout_raw", "stderr_raw", "stdout_digest", "stderr_digest")
    OUTPUT_FILES_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_DIRECTORIES_FIELD_NUMBER: _ClassVar[int]
    EXIT_CODE_FIELD_NUMBER: _ClassVar[int]
    STDOUT_RAW_FIELD_NUMBER: _ClassVar[int]
    STDERR_RAW_FIELD_NUMBER: _ClassVar[int]
    STDOUT_DIGEST_FIELD_NUMBER: _ClassVar[int]
    STDERR_DIGEST_FIELD_NUMBER: _ClassVar[int]
    output_files: _containers.RepeatedCompositeFieldContainer[OutputFile]
    output_directories: _containers.RepeatedCompositeFieldContainer[OutputDirectory]
    exit_code: int
    stdout_raw: bytes
    stderr_raw: bytes
    stdout_digest: Digest
    stderr_digest: Digest
    def __init__(self, output_files: _Optional[_Iterable[_Union[OutputFile, _Mapping]]] = ..., output_directories: _Optional[_Iterable[_Union[OutputDirectory, _Mapping]]] = ..., exit_code: _Optional[int] = ..., stdout_raw: _Optional[bytes] = ..., stderr_raw: _Optional[bytes] = ..., stdout_digest: _Optional[_Union[Digest, _Mapping]] = ..., stderr_digest: _Optional[_Union[Digest, _Mapping]] = ...) -> None: ...

class OutputFile(_message.Message):
    __slots__ = ("path", "digest", "is_executable", "contents")
    PATH_FIELD_NUMBER: _ClassVar[int]
    DIGEST_FIELD_NUMBER: _ClassVar[int]
    IS_EXECUTABLE_FIELD_NUMBER: _ClassVar[int]
    CONTENTS_FIELD_NUMBER: _ClassVar[int]
    path: str
    digest: Digest
    is_executable: bool
    contents: bytes
    def __init__(self, path: _Optional[str] = ..., digest: _Optional[_Union[Digest, _Mapping]] = ..., is_executable: bool = ..., contents: _Optional[bytes] = ...) -> None: ...

class OutputDirectory(_message.Message):
    __slots__ = ("path", "tree_digest")
    PATH_FIELD_NUMBER: _ClassVar[int]
    TREE_DIGEST_FIELD_NUMBER: _ClassVar[int]
    path: str
    tree_digest: Digest
    def __init__(self, path: _Optional[str] = ..., tree_digest: _Optional[_Union[Digest, _Mapping]] = ...) -> None: ...

class GetActionResultRequest(_message.Message):
    __slots__ = ("instance_name", "action_digest", "inline_stdout", "inline_stderr", "inline_output_files")
    INSTANCE_NAME_FIELD_NUMBER: _ClassVar[int]
    ACTION_DIGEST_FIELD_NUMBER: _ClassVar[int]
    INLINE_STDOUT_FIELD_NUMBER: _ClassVar[int]
    INLINE_STDERR_FIELD_NUMBER: _ClassVar[int]
    INLINE_OUTPUT_FILES_FIELD_NUMBER: _ClassVar[int]
    instance_name: str
    action_digest: Digest
    inline_stdout: bool
    inline_stderr: bool
    inline_output_files: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, instance_name: _Optional[str] = ..., action_digest: _Optional[_Union[Digest, _Mapping]] = ..., inline_stdout: bool = ..., inline_stderr: bool = ..., inline_output_files: _Optional[_Iterable[str]] = ...) -> None: ...

class UpdateActionResultRequest(_message.Message):
    __slots__ = ("instance_name", "action_digest", "action_result", "results_cache_policy_priority")
    INSTANCE_NAME_FIELD_NUMBER: _ClassVar[int]
    ACTION_DIGEST_FIELD_NUMBER: _ClassVar[int]
    ACTION_RESULT_FIELD_NUMBER: _ClassVar[int]
    RESULTS_CACHE_POLICY_PRIORITY_FIELD_NUMBER: _ClassVar[int]
    instance_name: str
    action_digest: Digest
    action_result: ActionResult
    results_cache_policy_priority: int
    def __init__(self, instance_name: _Optional[str] = ..., action_digest: _Optional[_Union[Digest, _Mapping]] = ..., action_result: _Optional[_Union[ActionResult, _Mapping]] = ..., results_cache_policy_priority: _Optional[int] = ...) -> None: ...
