import os

from core.system.path_utils import is_subpath_or_equal, normalize_path_cross_platform, paths_are_equivalent


def test_normalize_path_cross_platform(tmp_path):
    # Empty inputs
    assert normalize_path_cross_platform("") == ""
    assert normalize_path_cross_platform(None) == ""

    # Real directory
    norm = normalize_path_cross_platform(str(tmp_path))
    assert norm != ""
    if os.name == "nt":
        assert "/" not in norm


def test_paths_are_equivalent_case_and_slashes():
    if os.name == "nt":
        p1 = "C:\\Projects\\Bots\\Iris"
        p2 = "c:/projects/bots/iris"
        p3 = "C:\\Projects\\Bots\\Iris\\"
        assert paths_are_equivalent(p1, p2)
        assert paths_are_equivalent(p1, p3)
    else:
        p1 = "/srv/bots/iris"
        p2 = "/srv/bots/iris/"
        assert paths_are_equivalent(p1, p2)


def test_is_subpath_or_equal_exact_and_nested(tmp_path):
    subfolder = tmp_path / "src" / "modules"
    subfolder.mkdir(parents=True)

    # Exact match
    assert is_subpath_or_equal(str(tmp_path), str(tmp_path))

    # Subdirectory match
    assert is_subpath_or_equal(str(subfolder), str(tmp_path))

    # Reverse is NOT subpath
    assert not is_subpath_or_equal(str(tmp_path), str(subfolder))

    # Sibling with similar name is NOT subpath
    sibling = str(tmp_path) + "_other"
    assert not is_subpath_or_equal(sibling, str(tmp_path))


def test_is_subpath_or_equal_unc_paths():
    unc_parent = r"\\storage.local\bots\iris"
    unc_child = r"\\storage.local\bots\iris\logs"
    unc_sibling = r"\\storage.local\bots\iris_test"

    assert is_subpath_or_equal(unc_child, unc_parent)
    assert not is_subpath_or_equal(unc_sibling, unc_parent)


def test_is_subpath_or_equal_handles_none_and_empty():
    assert not is_subpath_or_equal(None, "/some/path")
    assert not is_subpath_or_equal("/some/path", None)
    assert not is_subpath_or_equal("", "/some/path")
    assert not is_subpath_or_equal("/some/path", "")
