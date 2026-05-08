"""GEPA optimization package for the SDTM domain generator example."""

from .project import SdtmGepaProject


def build_project() -> SdtmGepaProject:
    return SdtmGepaProject()


__all__ = ["SdtmGepaProject", "build_project"]
