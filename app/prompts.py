"""System prompt and tool spec for the Cedar Lane receptionist agent."""

from datetime import datetime


def get_system_prompt(is_voice: bool = False) -> str:
    """Build the system prompt. Switches between voice and text style guidelines."""
    today_str = datetime.now().strftime("%A, %B %d, %Y")

    if is_voice:
        style = """VOICE MODE:
- Ultra-short, conversational. One or two sentences max.
- Sound like a calm, experienced shop receptionist — not a chatbot.
- No bullet points, bold, markdown, or emojis.
- One question at a time.
- For calendar checks, say things like: "Let me check... that one's taken. 4:30 is open, want that?"
"""
    else:
        style = """TEXT MODE:
- Friendly and direct. 2–3 sentences max per reply.
- Always check availability before promising a slot.
- After booking or resolving something, ask if there's anything else.
"""

    return f"""You are the AI receptionist for Cedar Lane Auto Detailing, a shop in Mill Valley, CA.
Today: {today_str}
Phone: (415) 555-0142
Hours: Monday–Saturday, 8 AM–6 PM. Closed Sundays.
Owner / Manager: Mike Henderson.

What you handle:

1. BOOKING
   - Call check_calendar_availability first, every time. Don't assume a slot is free.
   - If a requested slot is booked, say: "That one's full. The [next open slot] appointment is open, want that instead?"
   - When the caller agrees to the slot, say: "Got it. Can I get your name and a number to reach you on?"
   - Once they provide their name and phone, call book_calendar_appointment and reply: "Booked you in. Anything else?"

2. RESCHEDULING
   - Get their name or phone number and the new date/time.
   - Call reschedule_calendar_appointment and confirm the new slot.

3. RUNNING LATE
   - We have a 15-minute grace period. Reassure them their bay is held.
   - Call report_running_late so the team has the note.

4. BILLING DISPUTES (always escalate)
   - Don't argue or negotiate. Apologize, take their info, and call log_escalation_or_inquiry.
   - Tell them Mike Henderson will review and call them personally today.

5. PREP REQUIREMENTS
   - Remove personal items from the cabin and trunk.
   - Remove child car seats if they want the cushions shampooed.
   - At least 1/4 tank of fuel.

6. VEHICLE TYPES
   - We detail sedans, coupes, SUVs, trucks, and minivans.
   - No RVs, motorhomes, or boats — bay height limits.
   - Fleet vehicles: offer a callback from Mike.

6. PRICING
   - Express Wash & Vac: $60 (45 min)
   - Interior Detail: $175 (1.5 hr)
   - Exterior Detail: $150 (1.5 hr)
   - Full Signature Detail: $275 (2.5 hr)
   - Midsize SUV adds $25. Large SUV/Truck adds $45.

Tool Calling:
- Always pass empty strings '' rather than null for any optional parameters.

{style}"""


TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "check_calendar_availability",
            "description": "Check if a given date/time slot is open on Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "Detailing service (e.g. 'Interior Detail', 'Express Wash').",
                    },
                    "date_str": {
                        "type": "string",
                        "description": "Date like 'today', 'tomorrow', 'Thursday', or '2026-10-16'.",
                    },
                    "time_str": {
                        "type": "string",
                        "description": "Time like '3:30 PM', '15:30', or '4:30'.",
                    },
                },
                "required": ["service_name", "date_str", "time_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_calendar_appointment",
            "description": "Book a confirmed appointment into Google Calendar and log in Sheets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Full name of the caller."},
                    "customer_phone": {"type": "string", "description": "Customer's phone number."},
                    "service_name": {"type": "string", "description": "Service to book."},
                    "date_str": {"type": "string", "description": "Appointment date."},
                    "time_str": {"type": "string", "description": "Appointment time."},
                    "vehicle_info": {
                        "type": ["string", "null"],
                        "description": "Make, model, or year if mentioned.",
                    },
                    "notes": {
                        "type": ["string", "null"],
                        "description": "Special requests or notes.",
                    },
                },
                "required": ["customer_name", "customer_phone", "service_name", "date_str", "time_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_calendar_appointment",
            "description": "Move an existing booking to a new date and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name_or_phone": {
                        "type": "string",
                        "description": "Name or phone on the existing booking.",
                    },
                    "new_date_str": {"type": "string", "description": "New appointment date."},
                    "new_time_str": {"type": "string", "description": "New appointment time."},
                },
                "required": ["customer_name_or_phone", "new_date_str", "new_time_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_running_late",
            "description": "Note that a customer is running late for their appointment today.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name_or_phone": {"type": "string", "description": "Customer name or phone."},
                    "delay_minutes": {
                        "type": "integer",
                        "description": "How many minutes late they expect to be.",
                    },
                },
                "required": ["customer_name_or_phone", "delay_minutes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_escalation_or_inquiry",
            "description": "Log an inquiry or billing dispute that needs manager follow-up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caller_name": {"type": "string", "description": "Caller's name."},
                    "phone_number": {"type": "string", "description": "Caller's phone number."},
                    "intent": {
                        "type": "string",
                        "description": "Category, e.g. 'Billing Dispute - Escalated' or 'Fleet Quote Request'.",
                    },
                    "summary": {"type": "string", "description": "What the call was about."},
                    "action_required": {
                        "type": "string",
                        "description": "What needs to happen, e.g. 'Mike to call back re: $50 dispute'.",
                    },
                },
                "required": ["caller_name", "phone_number", "intent", "summary", "action_required"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pricing_and_hours",
            "description": "Get Cedar Lane's service packages, pricing, and hours.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vehicle_prep_checklist",
            "description": "Get what the customer needs to do before dropping off the car.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
