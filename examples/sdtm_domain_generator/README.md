# SDTM Domain Generator

Generate a complete SAS script for an SDTM domain by combining:

- An **SDTM specification Excel file** (domain variables, codelists, derivation rules)
- **Source SAS datasets** (`.sas7bdat` or `.xpt`) whose schema is extracted automatically
- A **SAS template script** whose structure and macro style is adapted

The RLM picks the best-fit domain from the spec, maps source columns to SDTM
variables, and generates a production-ready SAS DATA step.

## Architecture

```
Outer LLM (GPT-5.4 via Copilot)        — orchestrates pipeline, writes Python in sandbox
  └─ Sub-LM (GPT-5-mini via Copilot)   — handles predict() calls for structured extraction

Skills (host-side tools):
  sas-schema   → SasSchemaAnalyzer   (analyze_sas_folder, analyze_sas_file, list_sas_files)
  sdtm-spec    → SDTMSpecAnalyzer    (list_sdtm_domains, analyze_sdtm_domain)
  sas-codegen  →                     (read_sas_template)
```

## Setup

### 1. Install dependencies

```bash
uv sync
uv pip install "sas-schema-analyzer @ git+https://github.com/linm1/sas-schema-analyzer.git@refactor/3.8-cli-decouple"
uv pip install "copilot-dspy @ git+https://github.com/linm1/copilot-dspy@main"
```

### 2. Verify Copilot model names

```bash
uv run python examples/sdtm_domain_generator/check_models.py
```

`check_models.py` now does two things:

1. Lists model IDs from Copilot's `/models` endpoint.
2. Probes `/chat/completions` with the same request shape this example uses.

Latest live probe in this repo succeeded with:

- `gpt-5.4`
- `gpt-5-mini`
- `gpt-4o`
- `gpt-4o-mini`

The example now defaults to the GPT-5-class pair `gpt-5.4` and `gpt-5-mini`.

### 3. Add your input files

Place in `sample/input/`:

| File | Description |
|------|-------------|
| `sdtm_spec.xlsx` | SDTM specification with sheets: Variables, Datasets, Codelists, Methods, Comments |
| `source_data/*.sas7bdat` or `source_data/*.xpt` | Raw source SAS datasets |
| `template.sas` | Sample SAS script defining macro style and DATA step structure |

A starter `template.sas` (DM domain pattern) is provided — replace with your own.

## Usage

```bash
uv run python examples/sdtm_domain_generator/run.py \
    --spec     examples/sdtm_domain_generator/sample/input/sdtm_spec.xlsx \
    --source   examples/sdtm_domain_generator/sample/input/source_data/ \
    --template examples/sdtm_domain_generator/sample/input/template.sas
```

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--spec` | `sample/input/sdtm_spec.xlsx` | SDTM spec Excel file |
| `--source` | `sample/input/source_data/` | Folder of `.sas7bdat` or `.xpt` files |
| `--template` | `sample/input/template.sas` | SAS template to adapt |
| `--model` | `gpt-5.4` | Outer LLM model (Copilot) |
| `--sub-lm-model` | `gpt-5-mini` | Sub-LM model for `predict()` calls |
| `--max-iterations` | `40` | REPL iteration limit |
| `--output` | `sample/output/<timestamp>/` | Output directory |
| `--debug` | off | Print REPL code and tool calls |

## Output

```
sample/output/<timestamp>/
└── DM.sas    ← generated SAS script (domain chosen by RLM from spec)
```

Console output includes domain selection rationale, variable mapping table,
warnings for unmapped variables, and token usage per LM.

## GEPA Optimization

The GEPA example under `examples/sdtm_domain_generator/gepa/` now defaults to the
same Copilot OAuth backend, using `gpt-5.4` for executor/proposer LMs and
`gpt-5-mini` for sub-LM calls.

Project-shape check:

```bash
uv run python -m examples.sdtm_domain_generator.gepa --check
```

Tiny optimize smoke test with a one-eval budget:

```bash
uv run python -m examples.sdtm_domain_generator.gepa --smoke
```

Note: this example now uses a repo-local adaptive Copilot wrapper that keeps the
usual `max_tokens` field for GPT-4-class models and switches to
`max_completion_tokens` for GPT-5-class models on `/chat/completions`.

Latest verified chat-completions-compatible models for this example:

| Model | Probe result | Token field |
|------|--------------|-------------|
| `gpt-5.4` | 200 | `max_completion_tokens` |
| `gpt-5-mini` | 200 | `max_completion_tokens` |
| `gpt-4o` | 200 | `max_tokens` |
| `gpt-4o-mini` | 200 | `max_tokens` |

Latest GPT-5 GEPA smoke artifact:

- `runs/sdtm_gepa_gpt5_smoke_20260508_173232/optimization_summary.json`

## How it works

1. `list_sdtm_domains(spec)` — discover all domains in the Excel spec
2. `analyze_sas_folder(source)` — extract column schemas from source datasets
3. Score column overlap vs each domain's required variables → select best fit
4. `analyze_sdtm_domain(spec, domain)` — fetch variables, codelists, derivations
5. `read_sas_template(template)` — load structural and style reference
6. Map source columns → SDTM variables; derive what cannot be mapped directly
7. Generate SAS DATA step following template conventions
8. Return `GeneratedScript` with `sas_code`, `mappings`, `selection`, `warnings`
