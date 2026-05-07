"""Skills for the SDTM domain generator example.

Three host-side tool skills:
- sas_schema_skill  — wraps SasSchemaAnalyzer as async tools
- sdtm_spec_skill   — wraps SDTMSpecAnalyzer as async tools
- sas_codegen_skill — reads the SAS template file + SAS/SDTM coding guidance
"""

from pathlib import Path

from predict_rlm import Skill
from sas_schema_analyzer.core.schema_analyzer import SasSchemaAnalyzer
from sas_schema_analyzer.core.sdtm_analyzer import SDTMSpecAnalyzer

_schema_analyzer = SasSchemaAnalyzer()
_sdtm_analyzer = SDTMSpecAnalyzer()

# ---------------------------------------------------------------------------
# SAS schema tools
# ---------------------------------------------------------------------------


async def analyze_sas_file(file_path: str) -> dict:
    """Analyze a single .sas7bdat file and return its schema.

    Returns row_count, column_count, and per-column metadata including
    name, label, type (numeric/character), unique_count, and code_list
    (when fewer than 15% of values are unique).
    """
    return _schema_analyzer.analyze_file(file_path)


async def analyze_sas_folder(folder_path: str, recursive: bool = False) -> dict:
    """Analyze all .sas7bdat files in a folder and return their schemas.

    Returns a summary with success/failure counts and per-file schema dicts.
    Use recursive=True to search subdirectories.
    """
    return _schema_analyzer.analyze_folder(folder_path, recursive=recursive)


async def list_sas_files(directory: str, recursive: bool = False) -> dict:
    """List .sas7bdat files in a directory with file sizes.

    Call this first to discover available source datasets before analyzing them.
    """
    return _schema_analyzer.list_sas_files(directory, recursive=recursive)


sas_schema_skill = Skill(
    name="sas-schema",
    instructions="""Tools for reading SAS dataset schemas.

## Tools
- `list_sas_files(directory)` — discover .sas7bdat files and their sizes
- `analyze_sas_file(path)` — get schema for a single dataset
- `analyze_sas_folder(path)` — get schema for all datasets in a folder

## Schema output structure
Each analyzed dataset returns:
    {
      "file_path": "...",
      "row_count": 1234,
      "column_count": 45,
      "columns": [
        {
          "name": "SUBJECTID",
          "label": "Subject Identifier",
          "type": "character",       # "numeric" or "character"
          "unique_count": 100,
          "code_list": ["M", "F"]    # present when unique_count / row_count < 0.15
        }
      ]
    }

## Mapping strategy
- Match column labels (not just names) against SDTM variable labels
- `code_list` values reveal categorical variables — check against SDTM codelists
- Numeric columns with small unique_count may map to SDTM categorical variables
- Date columns are typically numeric in SAS with a SAS date format label
""",
    packages=[],
    tools={
        "list_sas_files": list_sas_files,
        "analyze_sas_file": analyze_sas_file,
        "analyze_sas_folder": analyze_sas_folder,
    },
)

# ---------------------------------------------------------------------------
# SDTM spec tools
# ---------------------------------------------------------------------------


async def list_sdtm_domains(spec_path: str) -> dict:
    """List all SDTM domains defined in the specification Excel file.

    Returns domain codes, names, classes, and descriptions.
    Call this first to identify which domains are available before analyzing one.
    """
    return await _sdtm_analyzer.list_domains(spec_path)


async def analyze_sdtm_domain(spec_path: str, domain: str) -> dict:
    """Extract the full specification for a single SDTM domain.

    Returns variables with required/expected/permissible status, labels,
    types, controlled terminology codelists, and derivation instructions.
    """
    return await _sdtm_analyzer.analyze_sdtm_spec(spec_path, domain)


sdtm_spec_skill = Skill(
    name="sdtm-spec",
    instructions="""Tools for reading SDTM specification Excel files.

## Tools
- `list_sdtm_domains(spec_path)` — list all domains with metadata
- `analyze_sdtm_domain(spec_path, domain)` — get full variable spec for one domain

## Domain selection workflow
1. Call list_sdtm_domains() to see all available domains
2. Read source dataset schema (via sas-schema tools)
3. Compare source column names/labels against each domain's required variables
4. Pick the domain with the highest overlap of required variables

## Domain spec output structure
    {
      "domain": "DM",
      "specification": {
        "variables": [
          {
            "variable": "USUBJID",
            "label": "Unique Subject Identifier",
            "type": "Char",
            "core": "Req",             # Req = Required, Exp = Expected, Perm = Permissible
            "codelist": null,
            "derivation": "Concatenation of STUDYID, SITEID, SUBJID"
          }
        ],
        "codelists": { "SEX": ["M", "F", "U"], "RACE": [...] }
      }
    }

## Mapping rules
- **Req** variables must be present in the generated script
- **Exp** variables should be included when source data supports them
- **Perm** variables are optional — include only if source data has a clear match
- Variables with a codelist must be mapped to controlled terminology values
- Variables with a derivation instruction must be derived as specified
""",
    packages=[],
    tools={
        "list_sdtm_domains": list_sdtm_domains,
        "analyze_sdtm_domain": analyze_sdtm_domain,
    },
)

# ---------------------------------------------------------------------------
# SAS codegen tools
# ---------------------------------------------------------------------------


async def read_sas_template(path: str) -> str:
    """Read a SAS script file and return its full content as a string.

    Use this to load the template SAS script that defines the structural
    pattern and macro style to follow when generating the new domain script.
    """
    return Path(path).read_text(encoding="utf-8", errors="replace")


sas_codegen_skill = Skill(
    name="sas-codegen",
    instructions="""Tool for loading the SAS template and guidance for generating SDTM scripts.

## Tool
- `read_sas_template(path)` — load the template .sas file content

## How to use the template
1. Read the template with read_sas_template(template_sas_path)
2. Observe its structure: macro definitions, DATA step patterns, PROC steps
3. Mirror that structure for the new domain — same macro style, same formatting

## SDTM SAS DATA step requirements

### Mandatory variables (every SDTM domain)
    STUDYID   = "&STUDYID";       /* Study identifier */
    DOMAIN    = "XX";             /* 2-letter domain code, e.g. DM, AE */
    USUBJID   = TRIM(STUDYID) || "." || TRIM(SITEID) || "." || TRIM(SUBJID);

### Variable ordering
Follow SDTM IG order: identifier variables first, then topic, then qualifiers.

### Controlled terminology
Use explicit character assignment for codelist variables:
    if SEX_RAW = "Male"   then SEX = "M";
    else if SEX_RAW = "Female" then SEX = "F";
    else SEX = "U";

### Derivation comments
Add inline comments for every derived variable:
    /* DERIVED: concatenate STUDYID + SITEID + SUBJID */
    USUBJID = TRIM(STUDYID) || "." || TRIM(SITEID) || "." || TRIM(SUBJID);

### Dataset attributes
End the DATA step with LABEL and FORMAT statements:
    LABEL USUBJID = "Unique Subject Identifier"
          AGE     = "Age";
    FORMAT RFSTDTC RFENDTC date9.;

### Output
Save to: data SDTM.&DOMAIN; (following template convention)
""",
    packages=[],
    tools={"read_sas_template": read_sas_template},
)
