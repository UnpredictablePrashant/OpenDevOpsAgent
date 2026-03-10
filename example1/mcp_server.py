from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Example1MCP", json_response=True)


@mcp.tool()
def calculate_invoice(usage_units: int, unit_price: float, discount_pct: float) -> dict:
    """Calculate monthly invoice details for a customer."""
    subtotal = usage_units * unit_price
    discount_amount = subtotal * (discount_pct / 100.0)
    total = round(subtotal - discount_amount, 2)
    return {
        "usage_units": usage_units,
        "unit_price": unit_price,
        "discount_pct": discount_pct,
        "subtotal": round(subtotal, 2),
        "discount_amount": round(discount_amount, 2),
        "total": total,
    }


@mcp.tool()
def assess_support_priority(open_tickets: int, sla_breaches: int) -> dict:
    """Classify support priority from ticket backlog and SLA breaches."""
    score = (open_tickets * 2) + (sla_breaches * 5)
    if score >= 16:
        priority = "P1"
    elif score >= 8:
        priority = "P2"
    else:
        priority = "P3"
    return {"priority": priority, "risk_score": score}


@mcp.resource("customer://{name}")
def customer(name: str) -> str:
    normalized = name.strip().lower()
    if normalized in {"acme", "alice", "globex"}:
        tier = "enterprise"
        owner = "csm-enterprise@company.com"
    elif normalized in {"initech", "bob"}:
        tier = "mid-market"
        owner = "csm-midmarket@company.com"
    else:
        tier = "smb"
        owner = "csm-smb@company.com"
    return f"customer={name};tier={tier};owner={owner};billing_cycle=monthly"


@mcp.resource("playbook://{priority}")
def playbook(priority: str) -> str:
    p = priority.strip().upper()
    if p == "P1":
        return "Escalate to on-call immediately; open incident bridge; notify account owner."
    if p == "P2":
        return "Assign senior support engineer within 4h; update customer status page."
    return "Handle in normal queue; send routine update in next support cycle."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
