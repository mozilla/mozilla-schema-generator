# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
from mozilla_schema_generator.probes import GleanProbe, MainProbe


@pytest.fixture
def glean_probe_defn():
    return {
        "history": [
            {
                "dates": {
                    "first": "2019-04-12 13:44:13",
                    "last": "2019-08-08 15:34:03",
                },
                "send_in_pings": [
                    "metrics",
                ],
            },
            {
                "dates": {
                    "first": "2019-08-08 15:34:14",
                    "last": "2019-08-08 15:45:14",
                },
                "send_in_pings": [
                    "all-pings",
                ],
            }
        ],
        "name": "glean.error.invalid_value",
        "type": "labeled_counter",
    }


@pytest.fixture
def glean_probe_defn_subset_pings():
    return {
        "history": [
            {
                "dates": {
                    "first": "2019-04-12 13:44:13",
                    "last": "2019-08-08 15:34:03",
                },
                "send_in_pings": [
                    "metrics",
                ],
            },
            {
                "dates": {
                    "first": "2019-08-08 15:34:14",
                    "last": "2019-08-08 15:45:14",
                },
                "send_in_pings": [
                    "baseline",
                ],
            }
        ],
        "name": "glean.error.invalid_value",
        "type": "labeled_counter",
    }


@pytest.fixture
def main_probe_defn():
    return {
        "first_added": {
            "beta": "2017-08-07 23:34:15",
            "nightly": "2017-06-21 11:42:18",
            "release": "2017-09-19 01:26:22"
        },
        "history": {
            "beta": [
                {
                    "details": {
                        "keyed": False,
                        "kind": "string",
                        "record_in_processes": ["main"],
                    },
                    "versions": {
                        "first": "66",
                        "last": "69"
                    }
                },
                {
                    "details": {
                        "keyed": False,
                        "kind": "string",
                        "record_in_processes": ["main"],
                    },
                    "versions": {
                        "first": "61",
                        "last": "65"
                    }
                },
                {
                    "details": {
                        "keyed": False,
                        "kind": "string",
                        "record_in_processes": ["main"],
                    },
                    "versions": {
                        "first": "55",
                        "last": "60"
                    }
                }
            ],
            "nightly": [
                {
                    "details": {
                        "keyed": False,
                        "kind": "string",
                        "record_in_processes": ["main"],
                    },
                    "versions": {
                        "first": "62",
                        "last": "66"
                    }
                },
                {
                    "details": {
                        "keyed": False,
                        "kind": "string",
                        "record_in_processes": ["main"]
                    },
                    "versions": {
                        "first": "67",
                        "last": "70"
                    }
                },
                {
                    "details": {
                        "keyed": False,
                        "kind": "string",
                        "record_in_processes": ["main"],
                    },
                    "versions": {
                        "first": "56",
                        "last": "61"
                    }
                }
            ],
            "release": [
                {
                    "details": {
                        "keyed": False,
                        "kind": "string",
                        "record_in_processes": ["main", "content"]
                    },
                    "versions": {
                        "first": "65",
                        "last": "68"
                    }
                },
                {
                    "details": {
                        "keyed": False,
                        "kind": "string",
                    },
                    "versions": {
                        "first": "61",
                        "last": "64"
                    }
                },
                {
                    "details": {
                        "keyed": False,
                        "kind": "string",
                    },
                    "versions": {
                        "first": "55",
                        "last": "60"
                    }
                }
            ]
        },
        "name": "a11y.instantiators",
        "type": "scalar"
    }


@pytest.fixture
def main_probe_all_childs_defn():
    return {
        "first_added": {
            "release": "2017-09-19 01:26:22"
        },
        "history": {
            "nightly": [
                {
                    "details": {
                        "keyed": False,
                        "kind": "string",
                        "record_in_processes": ["all_childs"]
                    },
                    "versions": {
                        "first": "67",
                        "last": "70"
                    }
                }
            ],
        },
        "name": "a11y.instantiators",
        "type": "scalar"
    }


@pytest.fixture
def main_probe_all_childs_and_main_defn():
    return {
        "first_added": {
            "release": "2017-09-19 01:26:22"
        },
        "history": {
            "nightly": [
                {
                    "details": {
                        "keyed": False,
                        "kind": "string",
                        "record_in_processes": ["all_childs"]
                    },
                    "versions": {
                        "first": "67",
                        "last": "70"
                    }
                },
                {
                    "details": {
                        "keyed": False,
                        "kind": "string",
                        "record_in_processes": ["main"]
                    },
                    "versions": {
                        "first": "62",
                        "last": "66"
                    }
                }
            ],
        },
        "name": "a11y.instantiators",
        "type": "scalar"
    }


@pytest.fixture
def main_probe_all_defn():
    return {
        "first_added": {
            "release": "2017-09-19 01:26:22"
        },
        "history": {
            "nightly": [
                {
                    "details": {
                        "keyed": False,
                        "kind": "string",
                        "record_in_processes": ["all"]
                    },
                    "versions": {
                        "first": "67",
                        "last": "70"
                    }
                }
            ],
        },
        "name": "a11y.instantiators",
        "type": "scalar"
    }


@pytest.fixture
def main_probe_description():
    return {
        "first_added": {
            "release": "2017-09-19 01:26:22"
        },
        "history": {
            "nightly": [
                {
                    "description": "Test description",
                    "details": {
                        "keyed": False,
                        "kind": "string",
                        "record_in_processes": ["all"]
                    },
                    "versions": {
                        "first": "67",
                        "last": "70"
                    }
                }
            ],
        },
        "name": "a11y.instantiators",
        "type": "scalar"
    }


class TestProbe(object):

    def test_glean_sort(self, glean_probe_defn):
        probe = GleanProbe("scalar/test_probe", glean_probe_defn, pings=["aping"])
        assert probe.definition == glean_probe_defn["history"][1]

    def test_glean_all_pings(self, glean_probe_defn):
        pings = ["ping1", "ping2", "ping3"]
        probe = GleanProbe("scalar/test_probe", glean_probe_defn, pings=pings)
        assert probe.definition["send_in_pings"] == set(pings)

    def test_glean_subset_of_pings(self, glean_probe_defn_subset_pings):
        pings = ["ping1", "ping2", "ping3"]
        probe = GleanProbe("scalar/test_probe", glean_probe_defn_subset_pings, pings=pings)
        assert probe.definition["send_in_pings"] == {"baseline", "metrics"}

    def test_main_sort(self, main_probe_defn):
        probe = MainProbe("scalar/test_probe", main_probe_defn)
        assert probe.definition['versions'] == main_probe_defn["history"]["nightly"][1]['versions']

    def test_main_probe_processes(self, main_probe_defn):
        probe = MainProbe("scalar/test_probe", main_probe_defn)
        assert probe.definition['details']['record_in_processes'] == {"main", "content"}

    def test_main_probe_all_childs(self, main_probe_all_childs_defn):
        probe = MainProbe("scalar/test_probe", main_probe_all_childs_defn)
        assert probe.definition['details']['record_in_processes'] == \
            {"content", "gpu", "extension", "dynamic", "socket"}

    def test_main_probe_all_childs_and_main(self, main_probe_all_childs_and_main_defn):
        probe = MainProbe("scalar/test_probe", main_probe_all_childs_and_main_defn)
        assert probe.definition['details']['record_in_processes'] == \
            {"main", "content", "gpu", "extension", "dynamic", "socket"}

    def test_main_probe_all(self, main_probe_all_defn):
        probe = MainProbe("scalar/test_probe", main_probe_all_defn)
        assert probe.definition['details']['record_in_processes'] == \
            {"main", "content", "gpu", "extension", "dynamic", "socket"}

    def test_main_probe_description(self, main_probe_description):
        probe = MainProbe("scalar/test_probe", main_probe_description)
        assert probe.description == "Test description"
