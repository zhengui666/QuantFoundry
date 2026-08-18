from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CanonicalContractBuildHook(BuildHookInterface):
    PLUGIN_NAME = "canonical-contract"

    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        source = (
            Path(self.root).parent
            / "docs"
            / "后端系统技术方案"
            / "contracts"
            / "openapi-v1.yaml"
        )
        destination = (
            Path(self.root)
            / "src"
            / "quantfoundry"
            / "contracts"
            / "openapi"
            / "openapi-v1.yaml"
        )
        if not source.is_file() and destination.is_file():
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
