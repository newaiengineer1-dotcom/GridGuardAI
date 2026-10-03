# GridGuard AI — v11 Validation Report

## CrewAI/Groq correction

- Removed the failing `groq/...` CrewAI LiteLLM model route.
- CrewAI now uses the native OpenAI-compatible integration with Groq:
  - model: `openai/gpt-oss-120b`
  - base URL: `https://api.groq.com/openai/v1`
  - `custom_openai=True`
  - API key: `GROQ_API_KEY`
- Existing stale Llama-style model overrides are normalized to the current production model.
- Bill OCR text model updated to `openai/gpt-oss-120b`.
- Bill OCR vision model updated to `qwen/qwen3.8-27b`.
- CrewAI pinned to `1.15.22`; OpenAI SDK dependency added.

## Automated validation

- Fresh-source pytest: **32 passed**
- Python compileall: **PASS**
- Model-configuration regression tests: **PASS**
- CrewAI stub execution: **PASS**
- Fallback behavior: **PASS**
- Existing bill/dashboard/report tests: **PASS**

## External-runtime limitation

The build environment could not reach PyPI, so installing the actual CrewAI wheel for a live constructor smoke test was not possible here. The configuration was checked against current CrewAI documentation for `custom_openai=True` and current Groq documentation for the model IDs. A real Groq API call and browser/Streamlit runtime test still require the user's deployment environment and API key.

## v12 validation
37 offline tests passed; app.py and ui_components.py compile. Live CrewAI, Streamlit and Groq were not available in the build sandbox; use the in-app Test LLM connection.
