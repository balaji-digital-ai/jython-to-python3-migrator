"""CLI behaviour: input resolution, output modes, and the JSON report."""
import json

import pytest

from jython2py3.cli import main

JYTHON = 'print "hi"\nx = releaseVariables["b"]\n'


@pytest.mark.unit
def test_single_file_to_output(tmp_path):
    src = tmp_path / "in.py"
    src.write_text(JYTHON, encoding="utf-8")
    dest = tmp_path / "out.py"

    code = main(["migrate", str(src), "-o", str(dest)])

    assert code == 0
    migrated = dest.read_text(encoding="utf-8")
    assert 'print("hi")' in migrated
    assert 'getReleaseVariable("b")' in migrated


@pytest.mark.unit
def test_directory_mirrored(tmp_path):
    src_dir = tmp_path / "scripts"
    (src_dir / "sub").mkdir(parents=True)
    (src_dir / "a.py").write_text('print "a"\n', encoding="utf-8")
    (src_dir / "sub" / "b.py").write_text('print "b"\n', encoding="utf-8")
    out_dir = tmp_path / "migrated"

    code = main(["migrate", str(src_dir), "-o", str(out_dir)])

    assert code == 0
    assert (out_dir / "a.py").read_text(encoding="utf-8") == 'print("a")\n'
    assert (out_dir / "sub" / "b.py").read_text(encoding="utf-8") == 'print("b")\n'


@pytest.mark.unit
def test_in_place_with_backup(tmp_path):
    src = tmp_path / "in.py"
    src.write_text(JYTHON, encoding="utf-8")

    code = main(["migrate", str(src), "--in-place", "--backup"])

    assert code == 0
    assert 'print("hi")' in src.read_text(encoding="utf-8")
    assert (tmp_path / "in.py.bak").read_text(encoding="utf-8") == JYTHON


@pytest.mark.unit
def test_in_place_and_output_conflict(tmp_path):
    src = tmp_path / "in.py"
    src.write_text(JYTHON, encoding="utf-8")
    code = main(["migrate", str(src), "--in-place", "-o", str(tmp_path / "x.py")])
    assert code == 2


@pytest.mark.unit
def test_report_written(tmp_path):
    src = tmp_path / "in.py"
    src.write_text('from java.util import Calendar\n', encoding="utf-8")
    report = tmp_path / "report.json"

    main(["migrate", str(src), "--dry-run", "--report", str(report)])

    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["tool"] == "jython2py3"
    assert data["files"][0]["todo_count"] == 1
    assert data["files"][0]["changed"] is True


@pytest.mark.unit
def test_report_counts_tier1_transforms(tmp_path):
    # Two silent Tier-1 rewrites (print, getReleaseVariable) and no annotations.
    src = tmp_path / "in.py"
    src.write_text(JYTHON, encoding="utf-8")
    report = tmp_path / "report.json"

    main(["migrate", str(src), "--dry-run", "--report", str(report)])

    file_report = json.loads(report.read_text(encoding="utf-8"))["files"][0]
    assert file_report["transform_count"] == 2
    assert file_report["todo_count"] == 0


@pytest.mark.unit
def test_header_prepended_and_idempotent(tmp_path):
    src = tmp_path / "in.py"
    src.write_text(JYTHON, encoding="utf-8")
    dest = tmp_path / "out.py"

    main(["migrate", str(src), "-o", str(dest), "--header"])
    once = dest.read_text(encoding="utf-8")
    assert once.startswith("# Migrated from Jython by jython2py3")
    assert 'getReleaseVariable("b")' in once  # the migration still happened

    # Re-running over the already-stamped output must not stack a second header.
    main(["migrate", str(dest), "-o", str(dest), "--header"])
    assert dest.read_text(encoding="utf-8").count("# Migrated from Jython") == 1


@pytest.mark.unit
def test_no_header_by_default(tmp_path):
    src = tmp_path / "in.py"
    src.write_text(JYTHON, encoding="utf-8")
    dest = tmp_path / "out.py"

    main(["migrate", str(src), "-o", str(dest)])

    assert "# Migrated from Jython" not in dest.read_text(encoding="utf-8")


@pytest.mark.unit
def test_no_inputs_found_is_usage_error(tmp_path):
    code = main(["migrate", str(tmp_path / "does_not_exist.py")])
    assert code == 2
