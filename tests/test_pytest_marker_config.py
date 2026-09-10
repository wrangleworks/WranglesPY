from scripts import check_pytest_markers


def test_pytest_marker_configuration_is_consistent():
    assert check_pytest_markers.validate() == []
