# 02. Service Catalog and Build List

## 1. Agent Services to Build (A2A)

1. **main-agent-orchestrator**
   - Purpose: global planner, dependency resolver, aggregator.
   - Inputs: alerts, tickets, deployment events, manual requests.
   - Outputs: unified execution plan + final status report.

2. **marketplace-fe-agent**
   - Purpose: FE diagnostics (bundle/perf/errors/release regressions).
   - MCP dependencies: Monitoring, GitHub, Application MCP, Notification.

3. **marketplace-be-agent**
   - Purpose: BE diagnostics (API latency/errors/scaling/db pressure).
   - MCP dependencies: EKS, Monitoring, CloudWatch, AWS, GitHub.

4. **individual-service-agent**
   - Purpose: team/service-specific rules and remediation.
   - MCP dependencies: Application MCP, Compliance, JIRA.

5. **sre-incident-agent**
   - Purpose: incident triage, root-cause evidence graph, remediation proposal.
   - MCP dependencies: EKS, CloudWatch, Monitoring, AWS.

6. **security-agent**
   - Purpose: OWASP scan orchestration, compliance check and enforcement.
   - MCP dependencies: OWASP, Compliance (RAG), GitHub.

7. **delivery-agent**
   - Purpose: PR/issue/ticket/docs automation.
   - MCP dependencies: GitHub, JIRA, Confluence, Notification.

8. **finops-agent**
   - Purpose: detect cost spikes and recommend right-sizing actions.
   - MCP dependencies: Costing, AWS, CloudWatch.

9. **reporting-agent**
   - Purpose: produce stakeholder-ready incident/change/compliance reports.
   - MCP dependencies: Report Template, Confluence, Notification.

## 2. MCP Servers to Build

1. **eks-mcp-server**
   - Actions: pod diagnostics, rollout inspection, restart/rollback suggestions.
   - Optional execution: controlled remediation with approval gates.

2. **notification-mcp-server**
   - Providers: Slack, Teams, Gmail.
   - Features: incident channel fan-out, summary formatting, recipient policies.

3. **report-mcp-server**
   - Generates templates: incident report, RCA, weekly ops summary, compliance pack.

4. **monitoring-mcp-server**
   - Integrations: Dynatrace, Prometheus.
   - Functions: anomaly query, SLO impact summary, incident timeline signals.

5. **owasp-scan-mcp-server**
   - Scans: SAST/DAST/dependency/container/image checks.
   - Maps results to standard severity and remediation guidance.

6. **compliance-mcp-server (RAG)**
   - Retrieval over standards and internal controls.
   - Produces evidence-linked compliance decisions.

7. **github-mcp-server**
   - PR automation, issue triage, workflow status, release notes extraction.

8. **costing-mcp-server**
   - Cost and usage analytics, anomaly detection, recommendations.

9. **cloudwatch-eks-mcp-server**
   - CloudWatch logs/metrics/events correlation for EKS workloads.
   - Include AWS Labs EKS MCP integration approach as reference.

10. **application-mcp-server**
   - App repo/runtime metadata adapter.
   - Exposes domain signals (feature flags, release metadata, ownership maps).

11. **confluence-mcp-server**
   - Knowledge publishing: postmortems, runbook updates, change docs.

12. **jira-mcp-server**
   - Incident/task lifecycle automation; priority and assignment policies.

13. **aws-mcp-server**
   - Guardrailed cloud actions: ECS/EKS/ASG/RDS/S3/IAM read-heavy + approved write paths.

## 3. Platform Components to Build

1. EKS cluster modules (dev/stage/prod).
2. Kubernetes ingress + external DNS + certificate management.
3. Secret management (External Secrets + AWS Secrets Manager).
4. Service-to-service auth (mTLS/service mesh or signed service tokens).
5. Shared event bus/queue (for async workflows and retries).
6. Vector database and embedding pipeline for RAG.
7. Model gateway and model registry for baseline + fine-tuned models.
8. Observability stack:
   - Prometheus/Grafana
   - OpenTelemetry collector
   - log aggregation and traces
9. Policy engine:
   - OPA/Gatekeeper or equivalent
   - action approval policies for production changes.

## 4. API and Contract Standards

1. A2A message schema versioning.
2. MCP tool/resource naming convention.
3. Correlation IDs across all services.
4. Typed response envelope:
   - recommendation
   - confidence
   - evidence links
   - risk level
   - requires_approval flag

## 5. Definition of Done (Per Service)

1. API contract tests pass.
2. Security baseline passed (authn/authz, secret scanning, SBOM/image scan).
3. Dashboards and alerts shipped.
4. Runbook and failure-mode tests complete.
5. SLOs and on-call ownership assigned.
