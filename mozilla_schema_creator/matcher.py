
from .probes import Probe
from typing import Any

class Matcher(object):

    table_group_key = "table_group"
    type_key = "type"
    contains_key = "contains"

    def __init__(self, match_obj: dict):
        """
        table_group: required, which table that group belongs in
        type: optional, the type of the metrics

        All other fields are matched as exact matches,
        except for `contains` which checks that that value
        is in the associated array.
        """
        self.table_group = match_obj[self.table_group_key]
        self.type = match_obj.get(self.type_key)

        self.matcher = {k: v for k, v in match_obj.items() if k not in
                        {self.table_group_key, self.type_key}}

    def get_table_group(self):
        return self.table_group

    def matches(self, probe: Probe) -> bool:
        # Not a match if the types don't match
        if self.type and self.type != probe.get_type():
            return False

        for k, v in self.matcher.items():
            probe_value = probe.get(k)

            if not self._matches(v, probe_value):
                return False

            # Definitions are nested, check sub-fields (e.g. details)
            if isinstance(v, dict) and not v.keys() == {self.contains_key}:
                for sub_k, sub_v in v.items():
                    if not self._matches(sub_v, probe_value[sub_k]):
                        return False

        return True

    @staticmethod
    def _matches(match_v: Any, probe_v: Any) -> bool:
        if probe_v is None:
            return False

        # Not a match if this key isn't in the probe definition
        if probe_v is None:
            return False

        # Not a match if not an exact match of values (e.g. type=scalar vs. histogram)
        if not isinstance(match_v, dict):
            if match_v != probe_v:
                return False

        # Not a match if probe_v doesn't contain expected value
        elif isinstance(match_v, dict):
            if Matcher.contains_key in match_v:
                if match_v[Matcher.contains_key] not in probe_v:
                    return False

        return True
