"""Тесты repo-unbind и repo-delete."""

from __future__ import annotations

import subprocess

import pytest

from onec_ops.actions.repo_delete import RepoDeleteAction
from onec_ops.actions.repo_unbind import RepoUnbindAction
from onec_ops.cli import build_parser, main
from onec_ops.lib.exceptions import OneCOpsError
from onec_ops.lib.runner import RunContext


@pytest.fixture
def ib(tmp_path):
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").touch()
    return ib


@pytest.fixture
def storage(tmp_path):
    storage = tmp_path / "storage"
    (storage / "data").mkdir(parents=True)
    (storage / "1cv8ddb.1CD").touch()
    (storage / "data" / "x").touch()
    return storage


@pytest.fixture
def platform(tmp_path, mocker):
    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    mocker.patch("onec_ops.cli.check_environment")
    mocker.patch("onec_ops.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")
    return platform


@pytest.fixture
def execute(mocker):
    return mocker.patch(
        "onec_ops.lib.runner._execute", return_value=subprocess.CompletedProcess([], 0, "", "")
    )


def _unbind_ns(ib, *args):
    ns = build_parser().parse_args(["repo-unbind", *args])
    ns.ib = ib
    return ns


# repo-unbind


def test_unbind_minimal(ib):
    ns = _unbind_ns(ib)
    RepoUnbindAction().validate(ns)
    assert RepoUnbindAction().build_1c_args(ns, RunContext(ib / "1cv8")) == [
        "DESIGNER",
        "/F",
        str(ib),
        "/DisableStartupDialogs",
        "/ConfigurationRepositoryUnbindCfg",
    ]


def test_unbind_with_credentials_and_force(ib):
    ns = _unbind_ns(ib, "--storage-user", "dev", "--storage-password", "pw", "--force")
    assert RepoUnbindAction().build_1c_args(ns, RunContext(ib / "1cv8"))[4:] == [
        "/ConfigurationRepositoryN",
        "dev",
        "/ConfigurationRepositoryP",
        "pw",
        "/ConfigurationRepositoryUnbindCfg",
        "-force",
    ]


def test_unbind_has_no_storage_argument(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["repo-unbind", "--storage", "x"])
    assert "--storage" in capsys.readouterr().err


def test_unbind_cli_masks_password(ib, platform, execute, tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    args = ["--platform", str(platform), "--ib", "ib", "repo-unbind"]
    args += ["--storage-user", "dev", "--storage-password", "secret"]
    with caplog.at_level("INFO"):
        assert main(args) == 0
    command = execute.call_args.args[0]
    assert "/ConfigurationRepositoryUnbindCfg" in command
    assert str(ib) in command
    assert "secret" not in caplog.text


# repo-delete


def _delete(storage, *extra, platform=None):
    args = []
    if platform is not None:
        args += ["--platform", str(platform)]
    return main([*args, "repo-delete", "--storage", str(storage), *extra])


def test_delete_with_yes_removes_directory(storage, execute):
    assert _delete(storage, "--yes") == 0
    assert not storage.exists()
    execute.assert_not_called()


def test_delete_dry_run_keeps_directory(storage, execute):
    assert main(["--dry-run", "repo-delete", "--storage", str(storage)]) == 0
    assert storage.is_dir()
    execute.assert_not_called()


def test_delete_without_platform_config(storage, mocker):
    resolve = mocker.patch("onec_ops.cli.resolve_platform")
    assert _delete(storage, "--yes") == 0
    resolve.assert_not_called()


def test_delete_non_interactive_without_yes(storage, mocker):
    mocker.patch("sys.stdin.isatty", return_value=False)
    assert _delete(storage) == 1
    assert storage.is_dir()


@pytest.mark.parametrize(("answer", "deleted"), [("y\n", True), ("Yes\n", True), ("n\n", False)])
def test_delete_interactive_confirmation(storage, mocker, answer, deleted):
    mocker.patch("sys.stdin.isatty", return_value=True)
    mocker.patch("sys.stdin.readline", return_value=answer)
    assert _delete(storage) == (0 if deleted else 1)
    assert storage.exists() is not deleted


def test_delete_relative_path(storage, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["repo-delete", "--storage", "storage", "--yes"]) == 0
    assert not storage.exists()


@pytest.mark.parametrize("url", ["tcp://localhost:1542/main", "http://h/repo.1ccr/main"])
def test_delete_rejects_server_storage(url):
    ns = build_parser().parse_args(["repo-delete", "--storage", url, "--yes"])
    with pytest.raises(OneCOpsError, match="только файловое"):
        RepoDeleteAction().validate(ns)


def test_delete_rejects_missing(tmp_path):
    with pytest.raises(OneCOpsError, match="не существует"):
        RepoDeleteAction().validate(
            build_parser().parse_args(["repo-delete", "--storage", str(tmp_path / "none")])
        )


def test_delete_rejects_file(tmp_path):
    file = tmp_path / "file"
    file.touch()
    with pytest.raises(OneCOpsError, match="каталогом"):
        RepoDeleteAction().validate(
            build_parser().parse_args(["repo-delete", "--storage", str(file)])
        )


def test_delete_rejects_symlink(storage, tmp_path):
    link = tmp_path / "link"
    link.symlink_to(storage)
    with pytest.raises(OneCOpsError, match="каталогом"):
        RepoDeleteAction().validate(
            build_parser().parse_args(["repo-delete", "--storage", str(link)])
        )
    assert storage.is_dir()


def test_delete_rejects_non_repository(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (other / "important.txt").touch()
    assert main(["repo-delete", "--storage", str(other), "--yes"]) == 1
    assert (other / "important.txt").exists()


def test_delete_rmtree_error(storage, mocker):
    mocker.patch("onec_ops.actions.repo_delete.shutil.rmtree", side_effect=OSError("busy"))
    assert _delete(storage, "--yes") == 1


def test_delete_build_1c_args_empty(storage):
    ns = build_parser().parse_args(["repo-delete", "--storage", str(storage)])
    assert RepoDeleteAction().build_1c_args(ns, RunContext(storage / "1cv8")) == []
