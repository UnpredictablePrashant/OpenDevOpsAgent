# Example1: Customer Ops Automation (Multi-Agent + MCP)

This is a meaningful automation scenario, not a toy math demo.

## Scenario

A Customer Operations team wants one automated workflow that:

1. Computes a monthly invoice draft from usage and pricing inputs.
2. Assesses support risk from ticket backlog and SLA breaches.
3. Produces a unified action plan for Billing + Support + CSM.

This is implemented with multiple agents:

1. `agent_a_orchestrator.py` (Agent A): orchestrates workflow and merges results.
2. `agent_b_finance.py` (Agent B): billing specialist agent.
3. `agent_c_support.py` (Agent C): support triage specialist agent.
4. `mcp_server.py`: shared capability layer (tools/resources).

## MCP Capabilities Used

Tools:

1. `calculate_invoice(usage_units, unit_price, discount_pct)`
2. `assess_support_priority(open_tickets, sla_breaches)`

Resources:

1. `customer://{name}` (tier, owner, billing cycle)
2. `playbook://{priority}` (recommended escalation runbook)

## Input Contract

Send text in key-value form:

`customer=<name> usage=<int> unit_price=<float> discount=<float> tickets=<int> breaches=<int>`

Example:

`customer=Acme usage=120 unit_price=2.5 discount=10 tickets=4 breaches=1`

## Services and Ports

1. MCP Server: `127.0.0.1:8000` (`/mcp`)
2. Agent B (Finance): `127.0.0.1:9102` (`/a2a/finance`)
3. Agent C (Support): `127.0.0.1:9103` (`/a2a/support`)
4. Agent A (Orchestrator): `127.0.0.1:9101` (`/a2a/orchestrator`)

## Run Steps

From repo root, activate your virtualenv first.

1. Start MCP:

```bash
python example1/mcp_server.py
```

2. Start Agent B:

```bash
uvicorn example1.agent_b_finance:app --host 127.0.0.1 --port 9102 --reload
```

3. Start Agent C:

```bash
uvicorn example1.agent_c_support:app --host 127.0.0.1 --port 9103 --reload
```

4. Start Agent A:

```bash
uvicorn example1.agent_a_orchestrator:app --host 127.0.0.1 --port 9101 --reload
```

5. Run demo request:

```bash
python example1/run_demo.py
```

## Example Output (Shape)

```text
[AgentA-Orchestrator] Customer Ops Automation Plan
automation_steps:
1) Run billing computation and draft invoice
2) Run support triage and escalation policy
3) Produce unified account action summary

billing_output: [AgentB-Finance] Invoice ready for Acme: total=270.0, discount_amount=30.0. profile=customer=Acme;tier=enterprise;owner=csm-enterprise@company.com;billing_cycle=monthly. action=Create invoice draft + send for finance approval.
support_output: [AgentC-Support] Support triage for Acme: priority=P2, risk_score=13. profile=customer=Acme;tier=enterprise;owner=csm-enterprise@company.com;billing_cycle=monthly. playbook=Assign senior support engineer within 4h; update customer status page.
```

## Practical Use

This pattern maps directly to real automation:

1. Pull account telemetry and support metrics.
2. Let specialist agents process their domain logic.
3. Use MCP as a shared capability layer.
4. Return one decision-ready summary for ops teams.
