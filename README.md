# Autonomous Daily News Digest Agent

An autonomous news digest agent built with the Google Cloud Agent Development Kit (ADK) and Gemini 2.5.

## Architecture & Exam Criteria

- **Tool & Interface Design:** `tools.py` defines strongly typed inputs (`Pydantic`) and RSS fetching / email dispatch interfaces.
- **Context & Memory:** `memory.py` separates short-term turn state from long-term user preferences (`UserPreferenceMemory`).
- **Orchestration & Logic:** `agent.py` uses an ADK ReAct loop guided by system instructions.
- **Observability & Tracing:** Integrated logging for tool invocation trajectories, payloads, and timing.
- **Infrastructure & CI/CD:** `.github/workflows/ci.yml` runs unit tests and ADK trajectory evaluations on every push.

## Quickstart

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests & trajectory evaluations
pytest test_agent.py

# Run agent locally
python agent.py