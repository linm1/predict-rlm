import dspy

from .schema import GeneratedScript


class GenerateSDTMDomain(dspy.Signature):
    """Generate a SAS script that maps source data to an SDTM domain.

    1. Call list_sdtm_domains(sdtm_spec_path) to see all domains in the spec.
    2. Call analyze_sas_folder(source_data_path) to get schemas for source datasets.
    3. Compare source column names and labels against each domain's required
       variables — score overlap and pick the domain with the best fit.
    4. Call analyze_sdtm_domain(sdtm_spec_path, domain) to get the full
       variable spec, codelists, and derivation instructions for that domain.
    5. Call read_sas_template(template_sas_path) to load the SAS template.
    6. Map every source column to an SDTM variable where possible.
       For variables without a direct source, write a derivation.
    7. Generate a complete SAS DATA step that mirrors the template structure
       and macro style, covers all Required variables, and includes controlled
       terminology assignments and derivation comments.
    8. Return the script along with full mapping details and any warnings for
       variables that require manual review.
    """

    sdtm_spec_path: str = dspy.InputField(
        desc="Absolute path to the SDTM specification Excel file (.xlsx)"
    )
    source_data_path: str = dspy.InputField(
        desc="Absolute path to the folder containing source .sas7bdat files"
    )
    template_sas_path: str = dspy.InputField(
        desc="Absolute path to the sample SAS script to use as a structural template"
    )
    result: GeneratedScript = dspy.OutputField(
        desc="Generated SAS script with domain selection, variable mappings, and warnings"
    )
