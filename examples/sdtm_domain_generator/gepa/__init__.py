"""GEPA optimization package for the SDTM domain generator example."""

from .config import SdtmGepaConfig
from .project import SdtmGepaProject


def build_project(config: SdtmGepaConfig | None = None) -> SdtmGepaProject:
    return SdtmGepaProject(config)


__all__ = ["SdtmGepaProject", "build_project"]
