from pydantic import BaseModel, Field


class VariableMapping(BaseModel):
    sdtm_variable: str = Field(description="SDTM variable name, e.g. USUBJID")
    source_column: str | None = Field(
        default=None,
        description="Matched source dataset column; None if the variable is derived",
    )
    derivation: str | None = Field(
        default=None,
        description="Derivation rule or expression when not a direct column map",
    )
    codelist: str | None = Field(
        default=None,
        description="Controlled terminology codelist name if applicable, e.g. SEX, RACE",
    )


class DomainSelection(BaseModel):
    domain: str = Field(description="Selected SDTM domain code, e.g. DM, AE, LB")
    confidence: str = Field(description="Confidence level: high | medium | low")
    rationale: str = Field(
        description="Why this domain best fits the source dataset schema"
    )


class GeneratedScript(BaseModel):
    domain: str = Field(description="SDTM domain code this script generates")
    sas_code: str = Field(description="Complete SAS DATA step script for the domain")
    mappings: list[VariableMapping] = Field(
        default_factory=list,
        description="Variable-level mapping details for every SDTM variable in the domain",
    )
    selection: DomainSelection = Field(
        description="Domain selection decision with rationale"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Variables that could not be mapped and require manual review",
    )
