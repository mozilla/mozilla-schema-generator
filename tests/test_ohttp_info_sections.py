from unittest.mock import patch

import pytest
from click.testing import CliRunner

from mozilla_schema_generator.__main__ import check_ohttp_info_sections


@pytest.fixture
def mock_glean_ping():
    with patch("mozilla_schema_generator.__main__.GleanPing") as MockGleanPing:
        MockGleanPing.get_repos.return_value = [{"name": "app", "app_id": "org-app"}]
        yield MockGleanPing


def run(tmp_path, allowlist, *args):
    path = tmp_path / "allowlist.yaml"
    path.write_text(allowlist)
    return CliRunner(mix_stderr=False).invoke(
        check_ohttp_info_sections,
        ["--allowlist", str(path), *args],
        catch_exceptions=False,
    )


def test_no_flagged_pings(tmp_path, mock_glean_ping):
    mock_glean_ping.return_value.get_ohttp_pings_with_info_sections.return_value = []
    res = run(tmp_path, "")
    assert res.exit_code == 0


def test_flagged_ping_not_allowlisted(tmp_path, mock_glean_ping):
    mock_glean_ping.return_value.get_ohttp_pings_with_info_sections.return_value = [
        "my_ping"
    ]
    res = run(tmp_path, "")
    assert res.exit_code > 0
    assert "org-app.my-ping: declares the ohttp uploader capability" in res.stderr


def test_flagged_ping_allowlisted(tmp_path, mock_glean_ping):
    mock_glean_ping.return_value.get_ohttp_pings_with_info_sections.return_value = [
        "my-ping"
    ]
    res = run(
        tmp_path,
        "org-app.my-ping:\n  reason: transitioning\n",
    )
    assert res.exit_code == 0


def test_allowlist_entry_missing_fields(tmp_path, mock_glean_ping):
    mock_glean_ping.return_value.get_ohttp_pings_with_info_sections.return_value = [
        "my-ping"
    ]
    res = run(tmp_path, "org-app.my-ping:\n  bug: 1234567\n")
    assert res.exit_code > 0
    assert "org-app.my-ping: allowlist entry must have a `reason`" in (res.stderr)


def test_stale_allowlist_entry_does_not_fail(tmp_path, mock_glean_ping):
    mock_glean_ping.return_value.get_ohttp_pings_with_info_sections.return_value = []
    res = run(
        tmp_path,
        "org-app.old-ping:\n  reason: transitioning\n",
    )
    assert res.exit_code == 0
