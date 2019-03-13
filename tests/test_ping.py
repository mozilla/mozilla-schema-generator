import pytest

from .test_utils import LocalMainPing, env, probes, schema
from mozilla_schema_creator.schema import Schema, SchemaException
from mozilla_schema_creator.config import Config
    
class TestPing(object):

    def test_env_max_size(self, schema, env, probes):
        ping = LocalMainPing(schema, env, probes)

        with pytest.raises(SchemaException):
            ping.generate_schema(Config({}), max_size=1)
