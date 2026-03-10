# Detailed SRE Project: EKS-Native Multi-Agent A2A + MCP Platform

## 1. Project Objective

Design and build a production-grade DevOps and Cloud automation platform on AWS EKS where:

1. A **Main Agent** orchestrates workflows using A2A.
2. Domain agents (Marketplace FE/BE/Individual and SRE agents) collaborate over A2A.
3. Specialized **MCP servers** execute actions for debugging, observability, security, compliance, reporting, ticketing, and cloud operations.
4. The platform uses **RAG** for policy/runbook intelligence and introduces **fine-tuning** for domain-specific reasoning at scale.

This is the blueprint documentation for what must be created.

## 2. Mandatory Capabilities (Your Requested Scope)

1. Main Agent -> Marketplace Agent (FE, BE, Individual Agent)
2. EKS MCP Server (debugging, issue identification, recommendation, fixing)
3. Notification MCP Server (Slack, Teams, Gmail)
4. Report Generation MCP Server (template development)
5. Monitoring MCP Server (Dynatrace, Prometheus)
6. OWASP Security Scanning MCP Server
7. Compliance MCP Server (RAG-backed)
8. GitHub MCP Server
9. Costing MCP Server
10. CloudWatch with EKS MCP Server (reference: AWSlabs EKS MCP)
11. Application-Level MCP Server (reads app repo + signals)
12. Confluence MCP Server
13. JIRA MCP Server
14. AWS MCP Server

## 3. High-Level Architecture

```text
User/Platform Trigger
       |
       v
Main Agent (A2A Orchestrator)
       |
       +--> Marketplace FE Agent  ----+
       +--> Marketplace BE Agent  ----+--> Domain MCP Servers
       +--> Individual Service Agent -+
       |
       +--> SRE Incident Agent ----> EKS MCP / CloudWatch MCP / Monitoring MCP
       +--> Security Agent -------> OWASP MCP / Compliance MCP (RAG)
       +--> Delivery Agent -------> GitHub MCP / JIRA MCP / Confluence MCP
       +--> FinOps Agent ---------> Costing MCP / AWS MCP
       +--> Reporting Agent ------> Report MCP / Notification MCP
```

All runtime services are deployed on EKS with secure network boundaries, centralized observability, and policy guardrails.

## 4. Documentation Set

1. [Architecture Blueprint](./01_ARCHITECTURE_BLUEPRINT.md)
2. [Service Catalog and Build List](./02_SERVICE_CATALOG_AND_BUILD_LIST.md)
3. [Implementation Roadmap (Phases)](./03_IMPLEMENTATION_ROADMAP.md)
4. [SRE, Security, and Operations Model](./04_SRE_SECURITY_OPERATIONS.md)

## 5. Success Criteria

1. Mean time to detect and triage incidents is reduced with agent-assisted diagnosis.
2. Incident workflows trigger end-to-end automation: detect -> analyze -> propose -> execute -> validate -> notify -> document.
3. Compliance and security checks are continuously enforced via RAG policies and MCP scanners.
4. FinOps insights are integrated into deployment and scaling decisions.
5. The platform can scale agents and MCP servers independently on EKS.
