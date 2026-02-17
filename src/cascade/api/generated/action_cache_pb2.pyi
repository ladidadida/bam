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
    def __init__(self, output_files: _Iterable[OutputFile | _Mapping] | None = ..., output_directories: _Iterable[OutputDirectory | _Mapping] | None = ..., exit_code: int | None = ..., stdout_raw: bytes | None = ..., stderr_raw: bytes | None = ..., stdout_digest: Digest | _Mapping | None = ..., stderr_digest: Digest | _Mapping | None = ...) -> None: ...

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
    def __init__(self, path: str | None = ..., digest: Digest | _Mapping | None = ..., is_executable: bool = ..., contents: bytes | None = ...) -> None: ...

class OutputDirectory(_message.Message):
    __slots__ = ("path", "tree_digest")
    PATH_FIELD_NUMBER: _ClassVar[int]
    TREE_DIGEST_FIELD_NUMBER: _ClassVar[int]
    path: str
    tree_digest: Digest
    def __init__(self, path: str | None = ..., tree_digest: Digest | _Mapping | None = ...) -> None: ...

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
    def __init__(self, instance_name: str | None = ..., action_digest: Digest | _Mapping | None = ..., inline_stdout: bool = ..., inline_stderr: bool = ..., inline_output_files: _Iterable[str] | None = ...) -> None: ...

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
    def __init__(self, instance_name: str | None = ..., action_digest: Digest | _Mapping | None = ..., action_result: ActionResult | _Mapping | None = ..., results_cache_policy_priority: int | None = ...) -> None: ...
