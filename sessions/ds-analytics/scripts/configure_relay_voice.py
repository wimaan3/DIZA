"""Preview or create a dedicated RelayLA Retell agent after the web service is deployed.

Dry run is the default. Apply creates new resources and writes only a local receipt.
It does not change existing phone agents, buy numbers, or initiate conversations.
"""

import argparse
import json
import os
from pathlib import Path

import httpx

from diza_analysis.relay.voice_config import configuration

SESSION = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--voice-id", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    config = configuration(args.base_url, args.voice_id)
    if not args.apply:
        print(json.dumps(config, ensure_ascii=False, indent=2))
        return
    key = os.environ.get("RETELL_API_KEY")
    if not key:
        parser.error("Export RETELL_API_KEY first; API keys are never read from browser input.")
    receipt = SESSION / "artifacts/relay-retell.json"
    if receipt.exists():
        parser.error("A local creation receipt already exists. Reuse that dedicated agent ID.")
    # A legacy SPA fallback returning 200 is not a successful RelayLA deployment.
    health = httpx.get(args.base_url.rstrip("/") + "/health/relay", timeout=10)
    try:
        ready = health.status_code == 200 and health.json().get("product") == "RelayLA"
    except ValueError:
        ready = False
    if not ready:
        parser.error("Deploy RelayLA first: /health/relay must identify the RelayLA service.")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(
        base_url="https://api.retellai.com",
        headers={"Authorization": "Bearer " + key},
        timeout=25,
    ) as client:
        llm = client.post("/create-retell-llm", json=config["llm"])
        if llm.status_code != 201 and llm.status_code != 200:
            parser.error(f"Retell could not create the dedicated LLM (HTTP {llm.status_code}).")
        llm_id = llm.json()["llm_id"]
        receipt.write_text(json.dumps({"llm_id": llm_id, "status": "llm_created"}, indent=2))
        agent = client.post(
            "/create-agent",
            json={
                **config["agent"],
                "response_engine": {"type": "retell-llm", "llm_id": llm_id},
            },
        )
        if agent.status_code != 201 and agent.status_code != 200:
            parser.error(
                f"Retell could not create the agent (HTTP {agent.status_code}). "
                "The LLM ID is saved in the local receipt for recovery."
            )
        agent_id = agent.json()["agent_id"]
        receipt.write_text(
            json.dumps({"llm_id": llm_id, "agent_id": agent_id, "status": "created"}, indent=2)
        )
        print("Dedicated agent created. Set this private deployment variable:")
        print("RELAY_RETELL_AGENT_ID=" + agent_id)


if __name__ == "__main__":
    main()
