# A2A + MCP End-to-End Demo Documentation

## 0. Complete Objective of This Setup and Exercise

The objective of this project is to implement and understand a complete distributed-agent workflow where:

1. A client sends a request to **Agent A**.
2. **Agent A (orchestrator)** delegates the task to **Agent B** using A2A JSON-RPC.
3. **Agent B (tool agent)** uses **MCP** to call:
   - an MCP tool (`add`)
   - an MCP resource (`greeting://{name}`)
4. Agent B returns a structured A2A response to Agent A.
5. Agent A returns a final composed response to the client.

This exercise validates:

1. A2A communication between independent agents.
2. MCP capability access from an agent.
3. End-to-end interoperability with JSON-RPC payloads and artifact-based responses.

---

## 1. What the Current Project Now Does

This repo now runs a full chain: **Client -> Agent A -> Agent B -> MCP Server -> Agent B -> Agent A -> Client**.

If you send text like:

`compute 12 30 and greet Shashank`

the system should produce a response shaped like:

`[AgentA:orchestrator] Delegated to AgentB. Result: [AgentB:tool-agent] MCP says: 12+30=42. Also: Hello, Shashank! (from MCP)`

---

## 2. Core Concept: How A2A Works

A2A (Agent-to-Agent) is an interaction model where agents communicate over explicit protocol messages rather than direct function calls.

In this project, A2A characteristics are:

1. **Protocol boundary**: communication happens over HTTP using JSON-RPC `message/send`.
2. **Agent isolation**: Agent A and Agent B are separate services with separate ports.
3. **Structured exchange**: results are returned as A2A artifacts (`result.artifacts[].parts[]`).
4. **Delegation model**: Agent A does orchestration, Agent B does execution.

Why this matters:

1. You can swap Agent B implementation without changing Agent A business flow.
2. You can scale specialized agents independently.
3. You keep orchestration and execution concerns separated.

---

## 3. Core Concept: How MCP Works

MCP (Model Context Protocol) standardizes how an agent accesses external capabilities.

In MCP, the key abstractions are:

1. **Tools**: callable functions with typed parameters (`add(a, b)`).
2. **Resources**: URI-addressable data (`greeting://{name}`).
3. **Client session + transport**: the agent opens a connection (here streamable HTTP) and interacts through a session API.

In this project:

1. `mcp_server.py` hosts MCP capabilities at `http://127.0.0.1:8000/mcp`.
2. Agent B uses `ClientSession` + `streamable_http_client` to:
   - initialize session
   - call tool `add`
   - read resource `greeting://<name>`
3. Agent B transforms MCP results into an A2A text artifact.

Why this matters:

1. A2A solves **agent orchestration**.
2. MCP solves **capability/tool integration**.
3. Together they provide a clean layered architecture.

---

## 4. Architecture

```text
run_demo.py (client)
        |
        | POST JSON-RPC message/send
        v
Agent A (agent_a.py, port 8001)
        |
        | POST JSON-RPC message/send
        v
Agent B (agent_b.py, port 8002)
        |
        | MCP client session (streamable HTTP)
        v
MCP Server (mcp_server.py, port 8000, /mcp)
        |
        | tool/resource output
        v
Agent B -> Agent A -> run_demo.py
```

---

## 5. File Responsibilities

- `run_demo.py`: sends a JSON-RPC message to Agent A and prints final text artifact.
- `agent_a.py`: orchestrator; forwards user text to Agent B and returns composed output.
- `agent_b.py`: worker/tool-agent; parses request, calls MCP tool+resource, returns computed answer.
- `mcp_server.py`: MCP service with:
  - tool: `add(a, b)`
  - resource: `greeting://{name}`
- `requirements.txt`: dependency list.
- `older/`: reference/legacy files, not used by the root workflow.

---

## 6. Setup

## Prerequisites

1. Python 3.10+ (3.11 recommended)
2. `pip`
3. Four terminals/tabs (MCP, Agent B, Agent A, client)

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 7. Run Order (Important)

Start services in this order.

## Terminal 1: MCP Server

```bash
source .venv/bin/activate
python mcp_server.py
```

## Terminal 2: Agent B

```bash
source .venv/bin/activate
uvicorn agent_b:app --host 127.0.0.1 --port 8002 --reload
```

## Terminal 3: Agent A

```bash
source .venv/bin/activate
uvicorn agent_a:app --host 127.0.0.1 --port 8001 --reload
```

## Terminal 4: Demo Client

```bash
source .venv/bin/activate
python run_demo.py
```

---

## 8. Environment Variables

## `run_demo.py`

- `AGENT_A_URL` (default: `http://127.0.0.1:8001/a2a/orchestrator`)
- `DEMO_TEXT` (default: `compute 12 30 and greet Shashank`)

Example:

```bash
AGENT_A_URL=http://127.0.0.1:8001/a2a/orchestrator \
DEMO_TEXT="compute 7 9 and greet Alex" \
python run_demo.py
```

## `agent_a.py`

- `AGENT_B_BASE_URL` (default: `http://127.0.0.1:8002`)
- `AGENT_B_RPC_PATH` (default: empty)

When `AGENT_B_RPC_PATH` is empty, Agent A tries:

1. `/`
2. `/a2a`
3. `/a2a/tool-agent`

It caches the first successful URL for subsequent calls (optimization).

## `agent_b.py`

- `MCP_URL` (default: `http://127.0.0.1:8000/mcp`)

## 8.1 Agent Card URL and How to Find It

In the root project code, Agent Card base URLs are explicitly set in `build_agent_card(...)`:

1. Agent A card URL: `http://127.0.0.1:8001`
2. Agent B card URL: `http://127.0.0.1:8002`

Important:

1. Agent Card URL is the agent's base URL metadata.
2. JSON-RPC request path for this demo is the compatibility route:
   - Agent A RPC: `http://127.0.0.1:8001/a2a/orchestrator`
   - Agent B RPC: `http://127.0.0.1:8002/a2a/tool-agent`

How to discover runtime paths quickly:

```bash
# Inspect FastAPI OpenAPI for available paths
curl -s http://127.0.0.1:8001/openapi.json | jq '.paths | keys'
curl -s http://127.0.0.1:8002/openapi.json | jq '.paths | keys'
```

If `jq` is not installed:

```bash
curl -s http://127.0.0.1:8001/openapi.json
curl -s http://127.0.0.1:8002/openapi.json
```

---

## 9. Request Lifecycle (Detailed)

1. `run_demo.py` sends JSON-RPC `message/send` to Agent A.
2. Agent A extracts user text and calls Agent B over A2A JSON-RPC.
3. Agent B parses two numbers and a name from user text.
4. Agent B opens MCP session via `streamable_http_client`.
5. Agent B calls MCP tool `add(a, b)`.
6. Agent B reads MCP resource `greeting://{name}`.
7. Agent B composes text result and returns A2A artifact.
8. Agent A wraps the result and returns final artifact to client.
9. `run_demo.py` prints the final text.

---

## 10. Code Deep Dive

## `mcp_server.py`

1. Creates `FastMCP("DemoMCP", json_response=True)`.
2. Defines tool:
   - `add(a: int, b: int) -> int`
3. Defines resource:
   - `greeting://{name}` returning `Hello, <name>! (from MCP)`.
4. Runs MCP server with streamable HTTP transport when executed as main.

## `agent_b.py`

1. **Input parsing**:
   - `_extract_text_from_parts(...)` handles both dict and model-style parts.
   - `_extract_numbers_and_name(...)` parses integers and greeting target.
2. **MCP execution**:
   - `_call_mcp_add_and_greet(...)` initializes MCP session.
   - calls `add` tool.
   - reads `greeting://name` resource.
3. **Response composition**:
   - `_build_reply(...)` returns either:
     - MCP result text, or
     - guidance text if inputs are missing.
4. **A2A surfaces**:
   - `ToolAgent.execute(...)` for SDK request pipeline.
   - compatibility route `POST /a2a/{assistant_id}` for direct JSON-RPC demo calls.
5. **Agent card**:
   - advertises `compute_greet` skill and examples.

## `agent_a.py`

1. **Delegation helpers**:
   - `_candidate_b_rpc_urls()` builds route fallback list.
   - `_extract_text_from_response()` parses artifact text from Agent B response.
2. **Optimization**:
   - `self._resolved_b_url` caches first successful B endpoint.
3. **Delegation call**:
   - `_call_agent_b(...)` posts JSON-RPC payload to B.
   - retries candidate routes until success.
   - returns first text artifact or raises detailed error.
4. **A2A surfaces**:
   - `OrchestratorAgent.execute(...)` for SDK flow.
   - compatibility route `POST /a2a/{assistant_id}` for demo client route.
5. **Agent card**:
   - documents Agent A as orchestrator that delegates to MCP-enabled Agent B.

## `run_demo.py`

1. Builds JSON-RPC user message payload.
2. Sends request to Agent A URL.
3. Validates HTTP and JSON-RPC response.
4. Extracts first text artifact and prints it.

---

## 11. Example Input / Output

Input:

`compute 12 30 and greet Shashank`

Possible output:

`[AgentA:orchestrator] Delegated to AgentB. Result: [AgentB:tool-agent] MCP says: 12+30=42. Also: Hello, Shashank! (from MCP)`

Input with missing numbers:

`hello there`

Possible output:

`[AgentA:orchestrator] Delegated to AgentB. Result: [AgentB:tool-agent] I am MCP-enabled. Send two numbers and a name, e.g. 'compute 12 30 and greet Shashank'.`

---

## 12. Sample DevOps + AWS Cloud Implementation Scenario

This section shows how to implement the same architecture in a production-style AWS setup.

## Target Outcome

Deploy these services as containers:

1. `agent-a` service (public entry)
2. `agent-b` service (private internal service)
3. `mcp-server` service (private internal service)

With:

1. CI/CD pipeline from GitHub
2. secure service-to-service communication
3. centralized logs/metrics
4. scalable runtime

## Recommended AWS Architecture (Reference)

1. **Networking**
   - One VPC across 2-3 AZs.
   - Public subnets for ALB only.
   - Private subnets for ECS tasks (`agent-a`, `agent-b`, `mcp-server`).
2. **Compute**
   - Amazon ECS on Fargate (3 services, one task definition each).
3. **Ingress**
   - Application Load Balancer (ALB) -> target group -> `agent-a`.
4. **Internal discovery**
   - ECS Service Connect or AWS Cloud Map so `agent-a` can call `agent-b`, and `agent-b` can call `mcp-server`.
5. **Container registry**
   - Amazon ECR repositories for each service image.
6. **Secrets/config**
   - AWS Secrets Manager + SSM Parameter Store for env config.
7. **Observability**
   - CloudWatch Logs for all containers.
   - CloudWatch Alarms on error rate/latency.
   - X-Ray/OpenTelemetry optional for traces.

## Service Mapping for This Project

1. `agent-a`
   - Container port: `8001`
   - Env:
     - `AGENT_B_BASE_URL=http://agent-b.internal` (example Service Connect DNS)
     - `AGENT_B_RPC_PATH=/a2a/tool-agent`
2. `agent-b`
   - Container port: `8002`
   - Env:
     - `MCP_URL=http://mcp-server.internal/mcp`
3. `mcp-server`
   - Container port: `8000`

## CI/CD Flow (GitHub Actions Example)

1. On push to `main`:
   - run lint/tests
   - build 3 Docker images
   - push images to ECR with commit SHA tags
2. Deploy:
   - update ECS task definitions with new image tags
   - trigger rolling deployment for each ECS service
3. Post-deploy checks:
   - health check `agent-a` endpoint via ALB
   - smoke test JSON-RPC call (same shape as `run_demo.py`)

## Deployment Sequence in Cloud

1. Deploy `mcp-server` first.
2. Deploy `agent-b` and verify it reaches MCP.
3. Deploy `agent-a` and verify it reaches `agent-b`.
4. Run smoke test through ALB endpoint.

## Security Baseline

1. TLS at ALB (ACM certificate).
2. Keep `agent-b` and `mcp-server` private (no public ingress).
3. Restrict Security Groups:
   - ALB -> Agent A only.
   - Agent A -> Agent B only.
   - Agent B -> MCP only.
4. Use task IAM roles with least privilege.
5. Store secrets in Secrets Manager, not in code or task definition plaintext.

## Observability and SRE Checks

1. Structured JSON logs from all services.
2. Metrics:
   - request count
   - p95/p99 latency
   - 4xx/5xx rates
3. Alarms:
   - Agent A 5xx > threshold
   - Agent B MCP failures > threshold
4. Synthetic canary job every 5 minutes:
   - send `compute 12 30 and greet Ops`
   - assert response contains sum and greeting.

## Example Production Request Path

1. Client calls `https://agents.yourdomain.com/a2a/orchestrator`.
2. ALB routes to `agent-a` ECS task.
3. Agent A forwards JSON-RPC to `http://agent-b.internal/a2a/tool-agent`.
4. Agent B calls `http://mcp-server.internal/mcp`:
   - tool `add(12, 30)` -> `42`
   - resource `greeting://Ops` -> `Hello, Ops! (from MCP)`
5. Agent B returns A2A artifact to Agent A.
6. Agent A returns final response to client.

## Minimal IaC Direction

You can implement this in:

1. AWS CDK (Python/TypeScript), or
2. Terraform (AWS provider).

Recommended stacks/modules:

1. `network` (VPC/subnets/route tables)
2. `security` (SG/IAM/KMS)
3. `platform` (ECS cluster/ALB/Cloud Map/ECR)
4. `services` (`agent-a`, `agent-b`, `mcp-server`)
5. `observability` (log groups/alarms/dashboards)

---

## 13. Troubleshooting

## `ModuleNotFoundError` for `a2a` or `mcp`

1. Activate virtualenv.
2. Reinstall dependencies:

```bash
pip install -r requirements.txt
```

## Agent B says MCP call failed / connection refused

1. Ensure MCP server is running on `127.0.0.1:8000`.
2. Verify `MCP_URL` if using non-default port/path.

## Agent A cannot reach Agent B

1. Ensure Agent B is running on `127.0.0.1:8002`.
2. Set explicit endpoint if required:

```bash
AGENT_B_BASE_URL=http://127.0.0.1:8002 AGENT_B_RPC_PATH=/a2a/tool-agent uvicorn agent_a:app --port 8001
```

## Non-JSON or method errors

1. Use JSON-RPC payload with method `message/send`.
2. Call compatibility endpoints like `/a2a/orchestrator` and `/a2a/tool-agent` for the demo style.

---

## 14. Quick Commands

Install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run all:

```bash
# Terminal 1
python mcp_server.py

# Terminal 2
uvicorn agent_b:app --host 127.0.0.1 --port 8002 --reload

# Terminal 3
uvicorn agent_a:app --host 127.0.0.1 --port 8001 --reload

# Terminal 4
python run_demo.py
```
