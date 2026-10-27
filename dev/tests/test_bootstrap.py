import pytest

from git_companion.bootstrap import install_plan


def available(*names):
    return lambda name: f"/bin/{name}" if name in names else None


def test_windows_uses_exact_ids_and_silent_installs():
    plan = install_plan("Windows", ["git", "git-lfs"], available("winget"))
    assert "Git.Git" in plan[0] and "GitHub.GitLFS" in plan[1]
    assert all("--silent" in step and "--disable-interactivity" in step for step in plan)


def test_mac_and_linux_install_plans():
    assert install_plan("Darwin", ["git-lfs"], available("brew")) == [["brew", "install", "git-lfs"]]
    apt = install_plan("Linux", ["git", "git-lfs"], available("sudo", "apt-get"))
    assert apt[0] == ["sudo", "-n", "apt-get", "update"]
    assert apt[1][-2:] == ["git", "git-lfs"]
    assert install_plan("Linux", ["git"], available("dnf"), root=True) == [["dnf", "install", "-y", "git"]]


def test_unsupported_manager_has_actionable_error():
    with pytest.raises(RuntimeError, match="Homebrew"):
        install_plan("Darwin", ["git"], available())
    with pytest.raises(RuntimeError, match="administrator"):
        install_plan("Linux", ["git"], available())
    assert install_plan("Windows", [], available()) == []
