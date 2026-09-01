from collections import Counter
from typing import Dict, List, Optional

from app.services.llm_service import get_llm_service


class ChatResponseComposerAgent:
    """Compose grounded assistant responses.

    Every answer - including counts, breakdowns, and comparisons - is produced by an
    actual LLM call reasoning over the ingested data provided as context. There is no
    Python if/else branch logic that decides the final answer text; the aggregate
    counters below are only precomputed *grounding facts* handed to the LLM so it
    doesn't have to (and shouldn't) recompute totals from scratch, not a substitute
    for the LLM itself answering the question.
    """

    # Keep the full per-incident listing bounded so the prompt doesn't explode at scale.
    MAX_INCIDENTS_IN_CONTEXT = 300

    def __init__(self):
        self.llm = get_llm_service()

    def _fmt_counts(self, counter: Counter) -> str:
        return ", ".join(f"{name} ({count})" for name, count in counter.most_common()) or "none"

    def _split_lobs(self, lob_value: Optional[str]) -> List[str]:
        """Incidents can list multiple comma-separated LOBs (e.g. 'Retail Banking, Personal Loans')."""
        if not lob_value or not lob_value.strip():
            return ["Unspecified"]
        return [p.strip() for p in lob_value.split(",") if p.strip()]

    def _build_stats_summary(self, all_incidents: List[Dict]) -> Dict:
        lob_counts = Counter()
        for i in all_incidents:
            for lob in self._split_lobs(i.get("lob")):
                lob_counts[lob] += 1
        severity_counts = Counter((i.get("severity") or "UNKNOWN") for i in all_incidents)
        app_counts = Counter((i.get("application") or "Unknown") for i in all_incidents)
        status_counts = Counter((i.get("status") or "UNKNOWN") for i in all_incidents)
        return {
            "total": len(all_incidents),
            "lob_counts": lob_counts,
            "severity_counts": severity_counts,
            "app_counts": app_counts,
            "status_counts": status_counts,
        }

    def _format_history(self, conversation_history: Optional[List[dict]]) -> str:
        if not conversation_history:
            return ""
        recent = conversation_history[-6:]
        return "\nConversation history:\n" + "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in recent
        )

    def _format_full_dataset(self, all_incidents: List[Dict]) -> str:
        """Row-per-incident listing so the LLM can filter/count/compare itself for any
        question shape, instead of the backend guessing which filter combination to apply."""
        if not all_incidents:
            return "(no incidents ingested yet)"
        rows = ["incident_id | application | lob | severity | status"]
        for i in all_incidents[: self.MAX_INCIDENTS_IN_CONTEXT]:
            rows.append(
                f"{i.get('incident_id')} | {i.get('application') or 'Unknown'} | "
                f"{i.get('lob') or 'Unspecified'} | {i.get('severity') or 'UNKNOWN'} | "
                f"{i.get('status') or 'UNKNOWN'}"
            )
        return "\n".join(rows)

    def _format_top_matches(self, top_matches: List[Dict]) -> str:
        if not top_matches:
            return "(no closely matching incident was retrieved for this query)"
        parts = []
        for idx, row in enumerate(top_matches, 1):
            inc = row["incident"]
            parts.append(
                f"\n[{idx}] Incident ID: {inc['incident_id']} | Reason: {row['reason']} | Score: {row['score']}\n"
                f"Application: {inc.get('application')} | LOB: {inc.get('lob') or 'Unspecified'} | Severity: {inc.get('severity')}\n"
                f"Issue: {inc.get('issue') or inc.get('problem_summary')}\n"
                f"Root Cause: {inc.get('root_cause') or 'Unknown'}\n"
                f"Resolution: {'; '.join(inc.get('resolution') or [])}\n"
                f"Source Thread: {inc.get('source_thread_id') or 'N/A'}\n"
            )
        return "".join(parts)

    def _fallback_answer(self, top_matches: List[Dict], stats: Dict) -> str:
        """Last resort only - used if the LLM call itself fails/returns nothing, not a
        normal code path. Real answers always come from the LLM above."""
        if not top_matches:
            return (
                "I could not reach the language model and no close incident match was found "
                "in the ingested data for that query.\n\n"
                f"Available LOBs: {self._fmt_counts(stats['lob_counts'])}\n"
                f"Available applications: {self._fmt_counts(stats['app_counts'])}"
            )
        best = top_matches[0]["incident"]
        return (
            "I could not reach the language model, so here is the closest matching incident "
            f"on record: **{best['incident_id']}** - {best.get('problem_summary') or 'No summary'}."
        )

    def compose(self, query_analysis: Dict, retrieval_result: Dict, conversation_history: Optional[List[dict]] = None) -> Dict:
        message = query_analysis.get("message", "")
        top_matches = retrieval_result.get("top_matches") or []
        all_incidents = retrieval_result.get("all_incidents") or []
        low_confidence = retrieval_result.get("low_confidence", False)
        stats = self._build_stats_summary(all_incidents)

        history_context = self._format_history(conversation_history)

        # Aggregate/count questions answer from the full dataset, not a single "matched"
        # incident, so the low-confidence disclaimer (which talks about a closest-match
        # incident) would be misleading noise there - only show it for lookup-style intents.
        low_confidence_note = (
            "\n\n_No strong match was found in the ingested incidents for this query; "
            "the closest available incident below is shown for reference only and may not be relevant._"
        ) if low_confidence and query_analysis.get("intent") != "stats" else ""

        stats_context = (
            "AGGREGATE SUMMARY (precomputed for accuracy - reuse these totals verbatim, don't recompute them):\n"
            f"Total incidents: {stats['total']}\n"
            f"By LOB: {self._fmt_counts(stats['lob_counts'])}\n"
            f"By Severity: {self._fmt_counts(stats['severity_counts'])}\n"
            f"By Application: {self._fmt_counts(stats['app_counts'])}\n"
            f"By Status: {self._fmt_counts(stats['status_counts'])}\n"
        )

        full_dataset = self._format_full_dataset(all_incidents)
        match_context = self._format_top_matches(top_matches)

        prompt = f"""You are an incident assistant for internal use. Answer the user's question yourself,
reasoning directly over the data below - do not use outside knowledge and do not invent numbers.

For counting/aggregate questions (e.g. "how many X", "which LOB has the most"), count directly from the
FULL INCIDENT LIST below - one incident per row - rather than guessing. Some incidents list multiple
comma-separated LOBs (e.g. "ML, PL"); count that incident toward every LOB it lists. Use the AGGREGATE
SUMMARY only as a sanity check for the overall total and per-category counts, and prefer counting from
the FULL INCIDENT LIST when the question needs a filtered/combined count (e.g. severity + LOB together).

Always cite incident IDs in square brackets, e.g. [3028742], when referencing a specific incident.
If nothing in the data below answers the question, say so plainly instead of guessing.

Formatting rules: use plain Markdown only (headings, bullet lists, bold) - no raw HTML tags like <br>.
If a Markdown table is useful, keep each table cell to a short phrase; put any multi-sentence detail
(root cause, resolution steps, etc.) as bullet points or paragraphs below the table instead of packing
them into one cell.

{stats_context}

FULL INCIDENT LIST:
{full_dataset}

MOST RELEVANT INCIDENTS FOR THIS QUESTION:
{match_context}
{history_context}

User question: {message}
"""

        text = self.llm.generate(prompt)
        if not text or text.strip() in {"{}", "[]"}:
            text = self._fallback_answer(top_matches, stats)

        if low_confidence and low_confidence_note.strip() not in text:
            text = text + low_confidence_note

        return {
            "response": text,
            "sources": [m["incident"]["incident_id"] for m in top_matches],
        }

