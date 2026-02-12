"""Integration tests for error handling and edge cases."""

from pathlib import Path
from textwrap import dedent

import pytest

from cascade.config import ConfigurationError, load_config
from cascade.graph import CyclicDependencyError, MissingTaskError, build_task_graph


def test_invalid_yaml_syntax(tmp_path: Path):
    """Test error on malformed YAML."""
    (tmp_path / "cascade.yaml").write_text("invalid: yaml: syntax: [")

    with pytest.raises(ConfigurationError):
        load_config(tmp_path / "cascade.yaml")


def test_missing_task_command(tmp_path: Path):
    """Test error when task missing required field."""
    config = dedent("""
        version: 1

        tasks:
          broken:
            inputs: []
            outputs: []
    """)
    (tmp_path / "cascade.yaml").write_text(config)

    with pytest.raises(ConfigurationError):
        load_config(tmp_path / "cascade.yaml")


def test_cyclic_dependency_simple(tmp_path: Path):
    """Test detection of simple cycle."""
    config = dedent("""
        version: 1

        tasks:
          a:
            command: echo "a"
            depends_on:
              - b

          b:
            command: echo "b"
            depends_on:
              - a
    """)
    (tmp_path / "cascade.yaml").write_text(config)

    _, loaded_config = load_config(tmp_path / "cascade.yaml")

    with pytest.raises(CyclicDependencyError):
        build_task_graph(loaded_config.tasks)


def test_cyclic_dependency_complex(tmp_path: Path):
    """Test detection of indirect cycle."""
    config = dedent("""
        version: 1

        tasks:
          a:
            command: echo "a"
            depends_on:
              - b

          b:
            command: echo "b"
            depends_on:
              - c

          c:
            command: echo "c"
            depends_on:
              - a
    """)
    (tmp_path / "cascade.yaml").write_text(config)

    _, loaded_config = load_config(tmp_path / "cascade.yaml")

    with pytest.raises(CyclicDependencyError):
        build_task_graph(loaded_config.tasks)


def test_missing_dependency_task(tmp_path: Path):
    """Test error when dependency task doesn't exist."""
    config = dedent("""
        version: 1

        tasks:
          test:
            command: echo "test"
            depends_on:
              - nonexistent
    """)
    (tmp_path / "cascade.yaml").write_text(config)

    _, loaded_config = load_config(tmp_path / "cascade.yaml")

    with pytest.raises(MissingTaskError, match="nonexistent"):
        build_task_graph(loaded_config.tasks)


def test_empty_tasks_dict(tmp_path: Path):
    """Test handling of config with no tasks."""
    config = dedent("""
        version: 1

        tasks: {}
    """)
    (tmp_path / "cascade.yaml").write_text(config)

    _, loaded_config = load_config(tmp_path / "cascade.yaml")
    assert loaded_config.tasks == {}


def test_glob_with_no_matches(tmp_path: Path):
    """Test glob pattern that matches no files."""
    from cascade.cache import expand_globs

    expanded = expand_globs(["*.nonexistent"], tmp_path)

    # Should return empty list
    assert len(expanded) == 0


def test_glob_expansion(tmp_path: Path):
    """Test glob pattern expansion."""
    (tmp_path / "file1.txt").write_text("1")
    (tmp_path / "file2.txt").write_text("2")

    from cascade.cache import expand_globs

    expanded = expand_globs(["*.txt"], tmp_path)
    assert len(expanded) == 2


def test_env_var_expansion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test environment variable expansion in configuration."""
    monkeypatch.setenv("TEST_VALUE", "expanded_value")

    config = dedent("""
        version: 1

        tasks:
          test:
            command: echo "${TEST_VALUE}"
            env:
              MY_VAR: "${TEST_VALUE}"
    """)
    (tmp_path / "cascade.yaml").write_text(config)

    _, loaded_config = load_config(tmp_path / "cascade.yaml")
    task_config = loaded_config.tasks["test"]

    assert "expanded_value" in task_config.command
    assert task_config.env["MY_VAR"] == "expanded_value"


@pytest.mark.asyncio
async def test_cache_backend_interface(tmp_path: Path):
    """Test cache backend interface contract."""
    from cascade.cache import LocalCache

    cache = LocalCache(tmp_path / ".cascade/cache")

    # Non-existent key
    assert not await cache.exists("nonexistent_key")
    assert not await cache.get("nonexistent_key", [])

    # Put/get cycle
    (tmp_path / "test.txt").write_text("test data")
    success = await cache.put("test_key", [tmp_path / "test.txt"])
    assert success
    assert await cache.exists("test_key")

    # Clear
    await cache.clear()
    assert not await cache.exists("test_key")


def test_config_defaults(tmp_path: Path):
    """Test configuration defaults."""
    config = dedent("""
        version: 1

        tasks:
          simple:
            command: echo "test"
    """)
    (tmp_path / "cascade.yaml").write_text(config)

    _, loaded_config = load_config(tmp_path / "cascade.yaml")
    task = loaded_config.tasks["simple"]

    # Defaults should be applied
    assert task.inputs == []
    assert task.outputs == []
    assert task.depends_on == []
    assert task.env == {}


def test_task_ordering_deterministic(tmp_path: Path):
    """Test that task ordering is deterministic."""
    config = dedent("""
        version: 1

        tasks:
          z:
            command: echo "z"
          a:
            command: echo "a"
          m:
            command: echo "m"
            depends_on: [a, z]
    """)
    (tmp_path / "cascade.yaml").write_text(config)

    _, loaded_config = load_config(tmp_path / "cascade.yaml")
    graph = build_task_graph(loaded_config.tasks)

    from cascade.graph import execution_order_for_targets

    # Run multiple times - should always get same order
    orders = [execution_order_for_targets(graph, ["m"]) for _ in range(5)]

    # All should be identical
    assert all(order == orders[0] for order in orders)
