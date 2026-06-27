from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re

from loguru import logger

from .models import ServiceTriageReport, SupportDeskContext


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "service"


def render_markdown_report(report: ServiceTriageReport, context: SupportDeskContext) -> str:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    return "\n".join(
        [
            f"# Service Triage Report: {report.service}",
            "",
            f"- Generated: {generated_at}",
            f"- Customer: {context.customer_name}",
            f"- Contract tier: {context.contract_tier}",
            f"- Region: {context.region}",
            f"- Service: {report.service}",
            f"- Status: {report.status}",
            f"- Confidence: {report.confidence:.2f}",
            f"- Email action: {report.email_action}",
            "",
            "## Summary",
            "",
            report.summary,
            "",
            "## Next Action",
            "",
            report.next_action,
            "",
            "## Customer Message",
            "",
            report.customer_message,
            "",
        ]
    )


def write_markdown_report(
    report: ServiceTriageReport,
    context: SupportDeskContext,
    *,
    reports_dir: Path = Path("incident_report"),
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    path = reports_dir / f"{timestamp}-{slugify(report.service)}-{report.status}.md"
    path.write_text(render_markdown_report(report, context), encoding="utf-8")
    logger.debug("wrote markdown report path={}", path)
    return path
