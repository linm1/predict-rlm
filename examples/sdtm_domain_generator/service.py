"""SDTMDomainGenerator — RLM service for generating SDTM domain SAS scripts.

Usage::

    generator = SDTMDomainGenerator(sub_lm=sub_lm)
    prediction = await generator.aforward(
        sdtm_spec_path="/data/sdtm_spec.xlsx",
        source_data_path="/data/source/",
        template_sas_path="/data/template.sas",
    )
    # prediction.result — GeneratedScript with sas_code, mappings, warnings
"""

import dspy

from predict_rlm import PredictRLM

from .signature import GenerateSDTMDomain
from .skills import sas_codegen_skill, sas_schema_skill, sdtm_spec_skill


class SDTMDomainGenerator(dspy.Module):
    """DSPy Module that wraps GenerateSDTMDomain + PredictRLM."""

    def __init__(
        self,
        sub_lm: dspy.LM | str | None = None,
        max_iterations: int = 40,
        verbose: bool = False,
        debug: bool = False,
    ):
        self.sub_lm = sub_lm
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.debug = debug

    async def aforward(
        self,
        sdtm_spec_path: str,
        source_data_path: str,
        template_sas_path: str,
    ):
        """Run the domain generator and return the prediction.

        Returns a dspy.Prediction with:
        - result: GeneratedScript with sas_code, mappings, selection, warnings
        """
        predictor = PredictRLM(
            GenerateSDTMDomain,
            sub_lm=self.sub_lm,
            skills=[sas_schema_skill, sdtm_spec_skill, sas_codegen_skill],
            max_iterations=self.max_iterations,
            verbose=self.verbose,
            debug=self.debug,
        )
        return await predictor.acall(
            sdtm_spec_path=sdtm_spec_path,
            source_data_path=source_data_path,
            template_sas_path=template_sas_path,
        )
