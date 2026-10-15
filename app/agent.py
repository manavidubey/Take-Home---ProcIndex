"""Agent core — drives the conversation loop with tool calling."""

import json
import os
from typing import Any, Dict, List, Tuple

from openai import OpenAI

from app.config import settings
from app.prompts import get_system_prompt, TOOLS_SPEC
from app.tools.calendar_service import calendar_service
from app.tools.sheets_service import sheets_service
from app.tools.shop_knowledge import get_pricing_summary, get_prep_summary


class ReceptionistAgent:
    """Wraps the LLM client and dispatches tool calls for the receptionist."""

    def __init__(self):
        self.client, self.model = self._build_client()

    def _build_client(self) -> Tuple[OpenAI, str]:
        """Pick Groq or OpenAI based on env config."""
        if settings.LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY,
            )
            return client, settings.GROQ_MODEL

        if settings.OPENAI_API_KEY:
            return OpenAI(api_key=settings.OPENAI_API_KEY), settings.OPENAI_MODEL

        # last resort — try groq with whatever key is in the env
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY", ""),
        )
        return client, "openai/gpt-oss-120b"

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run the named tool and return its result dict."""
        if tool_name == "check_calendar_availability":
            return calendar_service.check_availability(
                service_name=args.get("service_name", "Detailing"),
                date_str=args.get("date_str", "today"),
                time_str=args.get("time_str", "12:00"),
            )

        if tool_name == "book_calendar_appointment":
            res = calendar_service.book_appointment(
                customer_name=args.get("customer_name", "Anonymous"),
                customer_phone=args.get("customer_phone", "Not Provided"),
                service_name=args.get("service_name", "Detailing"),
                date_str=args.get("date_str", "today"),
                time_str=args.get("time_str", "12:00"),
                vehicle_info=args.get("vehicle_info"),
                notes=args.get("notes"),
            )
            sheets_service.log_call(
                caller_name=args.get("customer_name", "Anonymous"),
                phone_number=args.get("customer_phone", "Not Provided"),
                intent="New Appointment Booking",
                summary=(
                    f"Booked {res.get('service')} for {res.get('date')} at "
                    f"{res.get('time')}. Vehicle: {args.get('vehicle_info', 'N/A')}"
                ),
                service=res.get("service"),
                appointment=f"{res.get('date')} @ {res.get('time')}",
                status="Confirmed Booking",
                action_required="None",
            )
            return res

        if tool_name == "reschedule_calendar_appointment":
            res = calendar_service.reschedule_appointment(
                customer_name_or_phone=args.get("customer_name_or_phone", ""),
                new_date_str=args.get("new_date_str", "tomorrow"),
                new_time_str=args.get("new_time_str", "12:00"),
            )
            sheets_service.log_call(
                caller_name=args.get("customer_name_or_phone", "Customer"),
                phone_number="",
                intent="Reschedule Appointment",
                summary=f"Rescheduled to {res.get('new_date')} at {res.get('new_time')}",
                appointment=f"{res.get('new_date')} @ {res.get('new_time')}",
                status="Rescheduled",
                action_required="None",
            )
            return res

        if tool_name == "report_running_late":
            res = calendar_service.add_running_late_note(
                customer_name_or_phone=args.get("customer_name_or_phone", ""),
                delay_minutes=args.get("delay_minutes", 15),
            )
            sheets_service.log_call(
                caller_name=args.get("customer_name_or_phone", "Customer"),
                phone_number="",
                intent="Running Late Notice",
                summary=f"Caller said {args.get('delay_minutes')} mins late. Grace period applied.",
                status="Running Late Notified",
                action_required="Technicians alerted to hold bay",
            )
            return res

        if tool_name == "log_escalation_or_inquiry":
            is_dispute = "dispute" in args.get("intent", "").lower()
            return sheets_service.log_call(
                caller_name=args.get("caller_name", "Anonymous"),
                phone_number=args.get("phone_number", "Not Provided"),
                intent=args.get("intent", "Inquiry"),
                summary=args.get("summary", ""),
                status="ESCALATED: Owner Review Required" if is_dispute else "Inquiry Logged",
                action_required=args.get("action_required", "Follow-up required"),
            )

        if tool_name == "get_pricing_and_hours":
            return {"pricing_and_hours": get_pricing_summary()}

        if tool_name == "get_vehicle_prep_checklist":
            return {"prep_checklist": get_prep_summary()}

        return {"error": f"Unknown tool: {tool_name}"}

    def chat(
        self, messages: List[Dict[str, str]], is_voice: bool = False
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Run one conversation turn, executing any tool calls the model requests."""
        system_prompt = get_system_prompt(is_voice=is_voice)
        payload: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for m in messages:
            if m.get("role") in ("user", "assistant", "system", "tool"):
                payload.append(m)

        executed: List[Dict[str, Any]] = []

        for _ in range(4):  # cap at 4 tool-call rounds
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=payload,
                    tools=TOOLS_SPEC,
                    tool_choice="auto",
                    temperature=0.3,
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                print(f"[agent] LLM error: {exc}")
                return "I'm having a quick connection issue. Could you repeat that?", executed

            msg = response.choices[0].message

            if not msg.tool_calls:
                return msg.content or "", executed

            payload.append(msg)
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                    if isinstance(fn_args, dict):
                        fn_args = {k: ("" if v is None else v) for k, v in fn_args.items()}
                except Exception:  # pylint: disable=broad-exception-caught
                    fn_args = {}

                result = self.execute_tool(fn_name, fn_args)
                executed.append({"tool": fn_name, "args": fn_args, "result": result})
                payload.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        return "Let me check that for you. Anything else I can help with?", executed


agent = ReceptionistAgent()
