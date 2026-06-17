import json
import os
import time
from dataclasses import dataclass
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, END
from openai import OpenAI

from anomaly import Anomaly
from simulator import TelemetryReading

# GPT-4o-mini pricing
_INPUT_COST_PER_TOKEN  = 0.150 / 1_000_000
_OUTPUT_COST_PER_TOKEN = 0.600 / 1_000_000

_CLASSIFY_SYSTEM = """\
You are a solar-farm fault classifier. Given telemetry and anomaly flags, output JSON:
{"severity": "LOW|MEDIUM|HIGH|CRITICAL", "fault_category": "thermal|electrical|power|mechanical"}
Only output valid JSON, no prose.\
"""

_ANALYZE_SYSTEM = """\
You are a senior renewable-energy operations engineer monitoring a solar farm in real-time.
You receive raw sensor telemetry, pre-computed anomaly flags, and a pre-classification.
Synthesise these into an actionable engineering diagnosis.

Always respond with a single valid JSON object matching this schema exactly:
{
  "issue":          "<concise issue title, ≤10 words>",
  "probable_cause": "<1–2 sentence root-cause explanation>",
  "severity":       "<LOW|MEDIUM|HIGH|CRITICAL>",
  "urgency":        "<immediate|within-hour|monitor>",
  "causes":         ["<cause 1>", "<cause 2>", "<cause 3>"],
  "actions":        ["<action 1>", "<action 2>", "<action 3>"],
  "safety_note":    "<safety concern string, or null>"
}

Engineering guidelines:
- Distinguish correlation from causation.
- If multiple anomalies are present, identify the most likely primary failure and secondary effects.
- Actions must be specific and ordered by priority (most urgent first).
- Severity must match the worst anomaly detected, not an average.
- safety_note should be non-null only when personnel or equipment are at genuine risk.\
"""


class AnalysisState(TypedDict):
    reading_summary: str
    anomaly_lines: str
    classification: str     # LOW|MEDIUM|HIGH|CRITICAL
    fault_category: str     # thermal|electrical|power|mechanical
    analysis: Optional[dict]
    action: str             # escalate|notify|monitor
    input_tokens: int
    output_tokens: int


@dataclass
class AIAnalysis:
    issue: str
    probable_cause: str
    severity: str
    urgency: str
    causes: list[str]
    actions: list[str]
    safety_note: Optional[str]
    action: str = "monitor"
    input_tokens: int = 0
    output_tokens: int = 0
    llm_cost_usd: float = 0.0

    def to_dict(self) -> dict:
        return {
            "issue": self.issue,
            "probable_cause": self.probable_cause,
            "severity": self.severity,
            "urgency": self.urgency,
            "causes": self.causes,
            "actions": self.actions,
            "safety_note": self.safety_note,
            "action": self.action,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "llm_cost_usd": self.llm_cost_usd,
        }


class AIAnalyzer:
    """
    LangGraph agentic workflow: classify → analyze → route.

    - classify: fast cheap call to categorise fault severity and type
    - analyze:  full diagnosis using classification as context
    - route:    rule-based decision (escalate | notify | monitor)

    Per-anomaly-type cooldown prevents redundant API calls during sustained faults.
    Token usage and cost are tracked per invocation.
    """

    COOLDOWN_SECONDS = 60
    MODEL = "gpt-4o-mini"

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self._client = OpenAI(api_key=api_key)
        self._cooldowns: dict[str, float] = {}
        self._graph = self._build_graph()

    def _build_graph(self):
        def classify_node(state: AnalysisState) -> AnalysisState:
            response = self._client.chat.completions.create(
                model=self.MODEL,
                max_tokens=80,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _CLASSIFY_SYSTEM},
                    {"role": "user", "content": f"{state['reading_summary']}\n\nAnomalies:\n{state['anomaly_lines']}"},
                ],
            )
            data = json.loads(response.choices[0].message.content)
            return {
                **state,
                "classification": data.get("severity", "MEDIUM"),
                "fault_category": data.get("fault_category", "unknown"),
                "input_tokens": state["input_tokens"] + response.usage.prompt_tokens,
                "output_tokens": state["output_tokens"] + response.usage.completion_tokens,
            }

        def analyze_node(state: AnalysisState) -> AnalysisState:
            context = f"Pre-classified: {state['classification']} {state['fault_category']} fault."
            user_msg = (
                f"{context}\n\n{state['reading_summary']}\n\n"
                f"Anomalies:\n{state['anomaly_lines']}\n\nProvide your engineering JSON analysis."
            )
            response = self._client.chat.completions.create(
                model=self.MODEL,
                max_tokens=500,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _ANALYZE_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
            )
            data = json.loads(response.choices[0].message.content)
            return {
                **state,
                "analysis": data,
                "input_tokens": state["input_tokens"] + response.usage.prompt_tokens,
                "output_tokens": state["output_tokens"] + response.usage.completion_tokens,
            }

        def route_node(state: AnalysisState) -> AnalysisState:
            sev = state["classification"]
            urgency = (state.get("analysis") or {}).get("urgency", "monitor")
            if sev == "CRITICAL" or urgency == "immediate":
                action = "escalate"
            elif sev in ("HIGH", "MEDIUM") or urgency == "within-hour":
                action = "notify"
            else:
                action = "monitor"
            return {**state, "action": action}

        workflow = StateGraph(AnalysisState)
        workflow.add_node("classify", classify_node)
        workflow.add_node("analyze", analyze_node)
        workflow.add_node("route", route_node)
        workflow.set_entry_point("classify")
        workflow.add_edge("classify", "analyze")
        workflow.add_edge("analyze", "route")
        workflow.add_edge("route", END)
        return workflow.compile()

    def _cooldown_key(self, anomalies: list[Anomaly]) -> str:
        return ",".join(sorted(a.type.value for a in anomalies))

    def _on_cooldown(self, anomalies: list[Anomaly]) -> bool:
        key = self._cooldown_key(anomalies)
        return (time.monotonic() - self._cooldowns.get(key, 0.0)) < self.COOLDOWN_SECONDS

    def _set_cooldown(self, anomalies: list[Anomaly]) -> None:
        self._cooldowns[self._cooldown_key(anomalies)] = time.monotonic()

    def analyze(
        self, reading: TelemetryReading, anomalies: list[Anomaly]
    ) -> Optional[AIAnalysis]:
        if not anomalies or self._on_cooldown(anomalies):
            return None

        anomaly_lines = "\n".join(
            f"  [{a.severity.value}] {a.type.value}: {a.message}" for a in anomalies
        )
        reading_summary = (
            f"Telemetry snapshot ({reading.timestamp}):\n"
            f"  battery_temp:        {reading.battery_temp} °C\n"
            f"  battery_charge:      {reading.battery_charge} %\n"
            f"  battery_health:      {reading.battery_health} %\n"
            f"  solar_output:        {reading.solar_output} W\n"
            f"  sunlight_intensity:  {reading.sunlight_intensity} %\n"
            f"  voltage:             {reading.voltage} V\n"
            f"  current:             {reading.current} A\n"
            f"  inverter_status:     {reading.inverter_status.value}\n"
            f"  inverter_efficiency: {reading.inverter_efficiency} %"
        )

        try:
            result = self._graph.invoke({
                "reading_summary": reading_summary,
                "anomaly_lines": anomaly_lines,
                "classification": "",
                "fault_category": "",
                "analysis": None,
                "action": "monitor",
                "input_tokens": 0,
                "output_tokens": 0,
            })
            self._set_cooldown(anomalies)

            data = result.get("analysis") or {}
            input_tokens = result["input_tokens"]
            output_tokens = result["output_tokens"]
            cost = round(
                input_tokens * _INPUT_COST_PER_TOKEN + output_tokens * _OUTPUT_COST_PER_TOKEN,
                8,
            )

            causes = data.get("causes", [])
            if not isinstance(causes, list):
                causes = []
            actions = data.get("actions", [])
            if not isinstance(actions, list):
                actions = []

            return AIAnalysis(
                issue=data.get("issue", "Unknown issue"),
                probable_cause=data.get("probable_cause", ""),
                severity=data.get("severity", result.get("classification", "MEDIUM")),
                urgency=data.get("urgency", "monitor"),
                causes=causes,
                actions=actions,
                safety_note=data.get("safety_note"),
                action=result.get("action", "monitor"),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                llm_cost_usd=cost,
            )
        except Exception as exc:
            print(f"[AI] LangGraph workflow failed: {exc}")
            return None
