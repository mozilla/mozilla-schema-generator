from unittest.mock import patch

from click.testing import CliRunner

from mozilla_schema_generator.__main__ import generate_glean_pings


@patch("mozilla_schema_generator.__main__.GleanPing")
def test_unmatched_metric_type(MockGleanPing):
    MockGleanPing.get_repos.return_value = ["test"]
    MockGleanPing.return_value.get_schema.return_value.get.return_value = {
        "url": {},
        "new_type_1": {},
        "new_type_2": {},
    }
    # command must fail before this is called
    MockGleanPing.return_value.generate_schema.side_effect = Exception(
        "method should not be called"
    )
    res = CliRunner(mix_stderr=False).invoke(
        generate_glean_pings, [], catch_exceptions=False
    )
    assert res.exit_code > 0
    assert res.stderr.startswith(
        "Error: Unknown metric types in Glean Schema:"
        " new_type_1, new_type_2. Please add them to"
    )
