# 01. Architecture Blueprint

## 1. Design Principles

1. EKS-first, cloud-native, horizontally scalable.
2. A2A as the control plane between agents.
3. MCP servers as the execution plane for domain integrations.
4. Strong guardrails: RBAC, policy-as-code, change approval gates.
5. Observability by default: metrics, logs, traces, audit events.
6. Cost-aware and security-first architecture.

## 2. Logical Layers

## Layer A: Experience and Triggering

1. ChatOps (Slack/Teams)
2. Web Portal / Ops Console
3. Scheduled and event triggers (CloudWatch, GitHub, Jira webhooks)

## Layer B: Agent Orchestration (A2A)

1. **Main Agent**: decomposes tasks, routes to sub-agents, aggregates results.
2. **Marketplace FE Agent**: frontend release, UI issue diagnostics, performance checks.
3. **Marketplace BE Agent**: API/service diagnostics, backend release safety.
4. **Individual Agent**: service-specific logic for each bounded context.
5. **SRE Incident Agent**: incident triage and remediation planning.
6. **Security Agent**: OWASP/compliance triage and actions.
7. **Delivery Agent**: GitHub/JIRA/Confluence automation.
8. **FinOps Agent**: cost anomaly and optimization recommendations.
9. **Reporting Agent**: incident/report assembly and stakeholder updates.

## Layer C: MCP Integration Plane

1. EKS MCP Server
2. Notification MCP Server
3. Report MCP Server
4. Monitoring MCP Server (Dynatrace, Prometheus)
5. OWASP Scanning MCP Server
6. Compliance MCP Server (RAG)
7. GitHub MCP Server
8. Costing MCP Server
9. CloudWatch + EKS MCP Server
10. Application-Level MCP Server
11. Confluence MCP Server
12. JIRA MCP Server
13. AWS MCP Server

## Layer D: Data and Intelligence

1. Vector DB for RAG (compliance docs, runbooks, postmortems, RFCs).
2. Object storage for reports/artifacts.
3. Metadata store for incident timelines and decisions.
4. Feature store/training datasets for fine-tuning.

## Layer E: Platform and Ops

1. EKS clusters (dev/stage/prod).
2. Service mesh (optional but recommended for mTLS and traffic policy).
3. API gateway/ingress.
4. CI/CD and GitOps deployment.

## 3. Reference Runtime Topology on AWS

1. One shared EKS control plane per environment.
2. Namespaces:
   - `agents-system`
   - `mcp-system`
   - `rag-system`
   - `observability`
   - `security`
3. Node groups:
   - General workloads
   - Memory-optimized for RAG retrieval/indexing
   - GPU/accelerator group (optional for fine-tuning/inference)
4. Core AWS services:
   - ECR, IAM, KMS, S3, CloudWatch, OpenSearch/Aurora/ElastiCache (as needed)

## 4. End-to-End Incident Flow (Example)

1. Alert from Prometheus/Dynatrace enters Main Agent.
2. Main Agent requests:
   - SRE Incident Agent -> EKS MCP + CloudWatch MCP
   - Security Agent -> OWASP MCP + Compliance MCP
   - Delivery Agent -> GitHub MCP + Jira MCP
3. Main Agent aggregates confidence-scored recommendations.
4. If policy permits, automated remediation is executed via AWS/EKS MCP.
5. Reporting Agent generates summary via Report MCP.
6. Notification MCP sends updates to Slack/Teams/Gmail.
7. Delivery Agent updates JIRA incident + Confluence postmortem draft.

## 5. RAG and Fine-Tuning Placement

## RAG

1. Compliance MCP and SRE agents query RAG indexes:
   - internal standards
   - OWASP guidelines
   - historical incidents
   - operational playbooks
2. Retrieval grounding is attached to each recommendation.

## Fine-Tuning

1. Phase after baseline reliability is proven.
2. Fine-tune domain-specific models for:
   - incident classification
   - remediation suggestion ranking
   - noisy alert deduplication
3. Fine-tuned models are served behind a model gateway with fallback to base models.

## 6. Optimization Strategy

1. Cache repeated retrieval queries (RAG cache).
2. Async fan-out/fan-in orchestration for parallel agent tasks.
3. Priority-based queues for incident-critical tasks.
4. Dynamic model routing:
   - low-cost model for routine triage
   - high-quality model for complex incidents
5. Progressive automation:
   - recommend mode -> assisted execute -> fully automated for low-risk paths.
