import yaml
import pytest
from mozilla_schema_generator import main_ping
from mozilla_schema_generator.config import Config


@pytest.fixture
def main():
    return main_ping.MainPing()


@pytest.fixture
def config():
    config_file = "./configs/main.yaml"
    with open(config_file) as f:
        return Config(yaml.load(f))


class TestMainPing(object):

    def test_env_size(self, main):
        assert main.get_env().get_size() > 0

    def test_single_schema(self, main, config):
        schema = main.generate_schema(config)["full"][0].schema

        assert "environment" in schema["properties"]
        assert "payload" in schema["properties"]

    def test_split_schema(self, main, config):
        schema = main.generate_schema(config, split=True)

        expected = {"histograms", "scalars", "keyed_histograms", "keyed_scalars", "extra"}
        assert set(schema.keys()) == expected

        for k, schemas in schema.items():
            for s in schemas:
                assert "environment" in s.schema["properties"]
                assert "payload" in s.schema["properties"]
