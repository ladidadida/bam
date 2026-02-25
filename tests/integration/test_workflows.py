"""Integration tests for complete workflow execution."""

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from bam.cache import LocalCache, compute_cache_key, expand_globs
from bam.cli import app
from bam.config import load_config
from bam.executor import TaskExecutor
from bam.graph import build_task_graph, execution_order_for_targets


@pytest.fixture
def runner():
    """Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def multi_stage_workspace(tmp_path: Path) -> Path:
    """Create workspace with multi-stage build pipeline."""
    # Config
    config = dedent("""
        version: 1

        tasks:
          generate:
            inputs:
              - "template.txt"
            outputs:
              - "generated.txt"
            command: cat template.txt | sed 's/PLACEHOLDER/Generated/' > generated.txt

          build:
            inputs:
              - "generated.txt"
              - "source.py"
            outputs:
              - "build/app.txt"
            command: mkdir -p build && cat generated.txt source.py > build/app.txt
            depends_on:
              - generate

          test:
            inputs:
              - "build/app.txt"
            outputs: []
            command: grep "Generated" build/app.txt && grep "print" build/app.txt
            depends_on:
              - build

          package:
            inputs:
              - "build/app.txt"
            outputs:
              - "dist/bundle.tar.gz"
            command: mkdir -p dist && tar czf dist/bundle.tar.gz -C build app.txt
            depends_on:
              - test
    """)
    (tmp_path / "bam.yaml").write_text(config)

    # Input files
    (tmp_path / "template.txt").write_text("This is PLACEHOLDER content\n")
    (tmp_path / "source.py").write_text("print('Hello World')\n")

    return tmp_path


@pytest.fixture
def parallel_workspace(tmp_path: Path) -> Path:
    """Create workspace with parallel independent tasks."""
    config = dedent("""
        version: 1

        tasks:
          lint-python:
            inputs:
              - "*.py"
            outputs: []
            command: echo "Linting Python..."

          lint-js:
            inputs:
              - "*.js"
            outputs: []
            command: echo "Linting JavaScript..."

          compile:
            inputs:
              - "*.py"
              - "*.js"
            outputs:
              - "build/output.txt"
            command: mkdir -p build && echo "Compiled" > build/output.txt
            depends_on:
              - lint-python
              - lint-js
    """)
    (tmp_path / "bam.yaml").write_text(config)
    (tmp_path / "main.py").write_text("# Python code\n")
    (tmp_path / "app.js").write_text("// JS code\n")

    return tmp_path


@pytest.mark.asyncio
async def test_multi_stage_pipeline_execution(multi_stage_workspace: Path):
    """Test complete multi-stage pipeline execution."""
    _, config = load_config(multi_stage_workspace / "bam.yaml")
    graph = build_task_graph(config.tasks)
    task_names = execution_order_for_targets(graph, ["package"])

    # Should execute all tasks in dependency order
    assert len(task_names) == 4
    assert task_names[0] == "generate"
    assert task_names[1] == "build"
    assert task_names[2] == "test"
    assert task_names[3] == "package"

    # Execute tasks
    executor = TaskExecutor()
    for task_name in task_names:
        task_config = config.tasks[task_name]

        expanded_inputs = expand_globs(task_config.inputs, multi_stage_workspace)
        result = await executor.execute_task(
            task_name=task_name,
            command=task_config.command,
            inputs=expanded_inputs,
            outputs=[multi_stage_workspace / p for p in task_config.outputs],
            env=task_config.env,
            working_dir=multi_stage_workspace,
        )
        assert result.exit_code == 0, f"Task {task_name} failed: {result.stderr}"

    # Verify outputs
    assert (multi_stage_workspace / "generated.txt").exists()
    assert (multi_stage_workspace / "build/app.txt").exists()
    assert (multi_stage_workspace / "dist/bundle.tar.gz").exists()


def test_parallel_task_ordering(parallel_workspace: Path):
    """Test parallel task ordering."""
    _, config = load_config(parallel_workspace / "bam.yaml")
    graph = build_task_graph(config.tasks)
    task_names = execution_order_for_targets(graph, ["compile"])

    # Should have 3 tasks
    assert len(task_names) == 3

    # lint-python and lint-js can be in any order (parallel)
    lint_tasks = {task_names[0], task_names[1]}
    assert lint_tasks == {"lint-python", "lint-js"}

    # compile must be last
    assert task_names[2] == "compile"


def test_partial_target_execution(multi_stage_workspace: Path):
    """Test running only specific target without full pipeline."""
    _, config = load_config(multi_stage_workspace / "bam.yaml")
    graph = build_task_graph(config.tasks)

    # Run only 'build' - should also run 'generate' as dependency
    task_names = execution_order_for_targets(graph, ["build"])
    assert len(task_names) == 2
    assert task_names[0] == "generate"
    assert task_names[1] == "build"

    # Should NOT include test or package
    assert "test" not in task_names
    assert "package" not in task_names


def test_multiple_targets(multi_stage_workspace: Path):
    """Test running multiple targets simultaneously."""
    _, config = load_config(multi_stage_workspace / "bam.yaml")
    graph = build_task_graph(config.tasks)

    # Run both 'build' and 'test'
    task_names = execution_order_for_targets(graph, ["build", "test"])
    assert len(task_names) == 3
    assert task_names[0] == "generate"
    assert task_names[1] == "build"
    assert task_names[2] == "test"


@pytest.mark.asyncio
async def test_task_failure_stops_execution(multi_stage_workspace: Path):
    """Test that task failure prevents dependent tasks from running."""
    # Add a failing task
    config_path = multi_stage_workspace / "bam.yaml"
    config_text = config_path.read_text()
    config_text = config_text.replace(
        "command: cat template.txt",
        "command: exit 1  # Force failure",
    )
    config_path.write_text(config_text)

    _, config = load_config(config_path)
    graph = build_task_graph(config.tasks)
    task_names = execution_order_for_targets(graph, ["build"])

    executor = TaskExecutor()
    results = []

    for task_name in task_names:
        task_config = config.tasks[task_name]

        try:
            result = await executor.execute_task(
                task_name=task_name,
                command=task_config.command,
                inputs=[],
                outputs=[],
                env=task_config.env,
                working_dir=multi_stage_workspace,
            )
            results.append(result)

            # Stop on failure
            if result.exit_code != 0:
                break
        except Exception:
            # Task failed with exception
            break

    # First task should have failed, only one result
    assert len(results) == 0  # Task raised exception before appending

    # Build should not have been executed
    assert not (multi_stage_workspace / "build/app.txt").exists()


@pytest.mark.asyncio
async def test_env_vars_in_command(tmp_path: Path):
    """Test environment variable expansion in commands."""
    config = dedent("""
        version: 1

        tasks:
          env-test:
            inputs: []
            outputs:
              - "output.txt"
            command: echo "$CUSTOM_VAR" > output.txt
            env:
              CUSTOM_VAR: "HelloFromEnv"
    """)
    (tmp_path / "bam.yaml").write_text(config)

    _, loaded_config = load_config(tmp_path / "bam.yaml")
    graph = build_task_graph(loaded_config.tasks)
    task_names = execution_order_for_targets(graph, ["env-test"])

    task_config = loaded_config.tasks[task_names[0]]

    executor = TaskExecutor()
    result = await executor.execute_task(
        task_name=task_names[0],
        command=task_config.command,
        inputs=[],
        outputs=[tmp_path / "output.txt"],
        env=task_config.env,
        working_dir=tmp_path,
    )

    assert result.exit_code == 0
    output = (tmp_path / "output.txt").read_text().strip()
    assert output == "HelloFromEnv"


def test_glob_pattern_expansion(tmp_path: Path):
    """Test glob pattern input expansion."""
    # Create multiple input files
    (tmp_path / "src").mkdir()
    (tmp_path / "src/file1.txt").write_text("Content 1\n")
    (tmp_path / "src/file2.txt").write_text("Content 2\n")
    (tmp_path / "src/file3.txt").write_text("Content 3\n")

    expanded = expand_globs(["src/*.txt"], tmp_path)

    assert len(expanded) == 3
    assert all(p.suffix == ".txt" for p in expanded)
    assert all(p.parent.name == "src" for p in expanded)


def test_cache_key_computation(tmp_path: Path):
    """Test cache key based on inputs."""
    (tmp_path / "input.txt").write_text("test content")

    key1 = compute_cache_key(
        command="echo test",
        inputs=[tmp_path / "input.txt"],
        env={"VAR": "value"},
    )

    # Same inputs = same key
    key2 = compute_cache_key(
        command="echo test",
        inputs=[tmp_path / "input.txt"],
        env={"VAR": "value"},
    )
    assert key1 == key2

    # Different command = different key
    key3 = compute_cache_key(
        command="echo different",
        inputs=[tmp_path / "input.txt"],
        env={"VAR": "value"},
    )
    assert key1 != key3

    # Different input content = different key
    (tmp_path / "input.txt").write_text("modified content")
    key4 = compute_cache_key(
        command="echo test",
        inputs=[tmp_path / "input.txt"],
        env={"VAR": "value"},
    )
    assert key1 != key4


@pytest.mark.asyncio
async def test_local_cache_workflow(tmp_path: Path):
    """Test complete cache put/get workflow."""
    cache = LocalCache(tmp_path / ".bam/cache")

    # Create output files
    (tmp_path / "output1.txt").write_text("output 1")
    (tmp_path / "output2.txt").write_text("output 2")

    cache_key = "test_cache_key_12345"

    # Store in cache
    success = await cache.put(cache_key, [tmp_path / "output1.txt", tmp_path / "output2.txt"])
    assert success

    # Should exist
    assert await cache.exists(cache_key)

    # Delete outputs
    (tmp_path / "output1.txt").unlink()
    (tmp_path / "output2.txt").unlink()

    # Restore from cache
    restored = await cache.get(cache_key, [tmp_path / "output1.txt", tmp_path / "output2.txt"])
    assert restored

    # Files should be back
    assert (tmp_path / "output1.txt").read_text() == "output 1"
    assert (tmp_path / "output2.txt").read_text() == "output 2"


def test_cli_list_command(multi_stage_workspace: Path, runner: CliRunner):
    """Test 'bam list' command."""
    result = runner.invoke(
        app,
        ["list", "--config", str(multi_stage_workspace / "bam.yaml")],
    )

    assert result.exit_code == 0
    assert "Available tasks:" in result.stdout
    assert "generate" in result.stdout
    assert "build" in result.stdout
    assert "test" in result.stdout
    assert "package" in result.stdout


def test_cli_clean_command(tmp_path: Path, runner: CliRunner):
    """Test 'bam clean' command."""
    # Create cache directory with content
    cache_dir = tmp_path / ".bam/cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "testfile.txt").write_text("cached data")

    result = runner.invoke(
        app,
        ["clean", "--cache-dir", str(cache_dir), "--force"],
    )

    assert result.exit_code == 0
    assert "Cache cleared" in result.stdout


def test_cli_graph_ascii(multi_stage_workspace: Path, runner: CliRunner):
    """Test 'bam graph' ASCII output."""
    result = runner.invoke(
        app,
        [
            "graph",
            "--config",
            str(multi_stage_workspace / "bam.yaml"),
            "--format",
            "ascii",
        ],
    )

    assert result.exit_code == 0
    assert "generate" in result.stdout
    assert "build" in result.stdout
    assert "test" in result.stdout
    assert "package" in result.stdout


def test_cli_graph_dot(multi_stage_workspace: Path, runner: CliRunner):
    """Test 'bam graph' DOT output."""
    result = runner.invoke(
        app,
        [
            "graph",
            "--config",
            str(multi_stage_workspace / "bam.yaml"),
            "--format",
            "dot",
        ],
    )

    assert result.exit_code == 0
    assert "digraph" in result.stdout
    assert "generate" in result.stdout
    assert "->" in result.stdout
