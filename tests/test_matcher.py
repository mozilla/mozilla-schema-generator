# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mozilla_schema_generator.matcher import Matcher
from mozilla_schema_generator.probes import GleanProbe, MainProbe


class TestMatcher(object):
    def test_matches(self):
        match_obj = {
            "details": {"record_in_processes": {"contains": "main"}, "keyed": True},
            "table_group": "keyed_scalars",
            "type": "scalar",
        }

        probe_defn = {
            "name": "temp_name",
            "type": "scalar",
            "first_added": {"nightly": "2019-01-01 00:00:00"},
            "history": {
                "nightly": [
                    {
                        "bug_numbers": [1522843],
                        "cpp_guard": None,
                        "description": "Number of times any text content from the Changes panel is "
                        "copied to the clipboard.\n",
                        "details": {
                            "keyed": True,
                            "kind": "uint",
                            "record_in_processes": ["main"],
                        },
                        "expiry_version": "69",
                        "notification_emails": [
                            "dev-developer-tools@lists.mozilla.org"
                        ],
                        "optout": True,
                        "revisions": {
                            "first": "4ab143dde4dc3424cfedc74b3648fbf2e47fb7bf",
                            "last": "4ab143dde4dc3424cfedc74b3648fbf2e47fb7bf",
                        },
                        "versions": {"first": "67", "last": "67"},
                    }
                ]
            },
        }

        matcher = Matcher(match_obj)
        probe = MainProbe("scalar/temp_name", probe_defn)
        assert matcher.matches(probe)

    def test_histogram_matches(self):
        match_obj = {
            "details": {"keyed": False, "record_in_processes": {"contains": "main"}},
            "table_group": "histograms",
            "type": "histogram",
        }

        probe_defn = {
            "name": "test-name",
            "type": "histogram",
            "first_added": {"nightly": "2019-02-02 02:02:00"},
            "history": {
                "nightly": [
                    {
                        "bug_numbers": [1351383],
                        "cpp_guard": None,
                        "description": "Whether we have layed out any display:block "
                        "containers with not-yet-supported properties from CSS Box Align.",
                        "details": {
                            "high": 2,
                            "keyed": False,
                            "kind": "boolean",
                            "low": 1,
                            "n_buckets": 3,
                            "record_in_processes": ["main", "content"],
                        },
                        "expiry_version": "57",
                        "notification_emails": ["bwerth@mozilla.com"],
                        "optout": True,
                        "revisions": {
                            "first": "f9605772a0c9098ed1bcaa98089b2c944ed69e9b",
                            "last": "8e818b5e9b6bef0fc1a5c527ecf30b0d56a02f14",
                        },
                        "versions": {"first": "55", "last": "57"},
                    }
                ]
            },
        }

        matcher = Matcher(match_obj)
        probe = MainProbe("histogram/name", probe_defn)

        assert matcher.matches(probe)

    def test_not_match(self):
        match_obj = {
            "expiry_version": {"not": "57"},
            "table_group": "histograms",
            "type": "histogram",
        }

        probe_defn = {
            "name": "test-name",
            "type": "histogram",
            "first_added": {"nightly": "2019-02-02 02:02:00"},
            "history": {
                "nightly": [
                    {
                        "bug_numbers": [1351383],
                        "cpp_guard": None,
                        "description": "Whether we have layed out any display:block "
                        "containers with not-yet-supported properties from CSS Box Align.",
                        "details": {
                            "high": 2,
                            "keyed": False,
                            "kind": "boolean",
                            "low": 1,
                            "n_buckets": 3,
                            "record_in_processes": ["main", "content"],
                        },
                        "expiry_version": "57",
                        "notification_emails": ["bwerth@mozilla.com"],
                        "optout": True,
                        "revisions": {
                            "first": "f9605772a0c9098ed1bcaa98089b2c944ed69e9b",
                            "last": "8e818b5e9b6bef0fc1a5c527ecf30b0d56a02f14",
                        },
                        "versions": {"first": "55", "last": "57"},
                    }
                ]
            },
        }

        matcher = Matcher(match_obj)
        probe = MainProbe("histogram/name", probe_defn)

        assert not matcher.matches(probe)

        probe_defn["history"]["nightly"][0]["expiry_version"] = "58"
        assert matcher.matches(probe)

    def test_not_and_contains(self):
        match_obj = {
            "send_in_pings": {"not": ["baseline"], "contains": "baseline"},
            "table_group": "histograms",
            "type": "histogram",
        }

        probe_defn = {
            "name": "test-name",
            "type": "histogram",
            "first_added": {"nightly": "2019-02-02 02:02:00"},
            "history": [
                {
                    "bug_numbers": [1351383],
                    "cpp_guard": None,
                    "description": "Whether we have layed out any display:block containers with "
                    "not-yet-supported properties from CSS Box Align.",
                    "send_in_pings": ["baseline", "event"],
                    "details": {
                        "high": 2,
                        "keyed": False,
                        "kind": "boolean",
                        "low": 1,
                        "n_buckets": 3,
                        "record_in_processes": ["main", "content"],
                    },
                    "expiry_version": "57",
                    "notification_emails": ["bwerth@mozilla.com"],
                    "optout": True,
                    "commits": {
                        "first": "f9605772a0c9098ed1bcaa98089b2c944ed69e9b",
                        "last": "8e818b5e9b6bef0fc1a5c527ecf30b0d56a02f14",
                    },
                    "dates": {
                        "first": "2018-01-01 00:00:00",
                        "last": "2019-01-01 00:00:00",
                    },
                }
            ],
        }

        matcher = Matcher(match_obj)
        probe = GleanProbe("histogram/name", probe_defn)

        assert matcher.matches(probe)

        probe_defn["history"][0]["send_in_pings"] = ["baseline"]
        probe = GleanProbe("histogram/name", probe_defn)
        assert not matcher.matches(probe)

    def test_any_match(self):
        match_obj = {
            "table_group": "histograms",
            "type": "histogram",
            "name": {"any": ["foo", "bar"]},
        }

        probe_defn = {
            "name": "not-matching-name",
            "type": "histogram",
            "first_added": {"nightly": "2019-02-02 02:02:00"},
            "history": {
                "nightly": [
                    {
                        "bug_numbers": [1351383],
                        "cpp_guard": None,
                        "description": "Whether we have layed out any display:block "
                        "containers with not-yet-supported properties from CSS Box Align.",
                        "details": {
                            "high": 2,
                            "keyed": False,
                            "kind": "boolean",
                            "low": 1,
                            "n_buckets": 3,
                            "record_in_processes": ["main", "content"],
                        },
                        "expiry_version": "57",
                        "notification_emails": ["bwerth@mozilla.com"],
                        "optout": True,
                        "revisions": {
                            "first": "f9605772a0c9098ed1bcaa98089b2c944ed69e9b",
                            "last": "8e818b5e9b6bef0fc1a5c527ecf30b0d56a02f14",
                        },
                        "versions": {"first": "55", "last": "57"},
                    }
                ]
            },
        }

        matcher = Matcher(match_obj)
        probe = MainProbe("histogram/name", probe_defn)

        assert not matcher.matches(probe)

        probe_defn["name"] = "foo"
        probe = MainProbe("histogram/name", probe_defn)
        assert matcher.matches(probe)

        probe_defn["name"] = "bar"
        probe = MainProbe("histogram/name", probe_defn)
        assert matcher.matches(probe)
