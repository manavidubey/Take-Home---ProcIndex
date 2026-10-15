"""Pytest Unit & Integration Tests for Cedar Lane Auto Detailing AI Receptionist."""

from app.tools.calendar_service import calendar_service
from app.tools.sheets_service import sheets_service
from app.tools.shop_knowledge import check_vehicle_support, get_pricing_summary, get_prep_summary
from app.agent import agent


def test_shop_knowledge_pricing():
    """Verify that pricing summary includes all core services and operating hours."""
    pricing = get_pricing_summary()
    assert "Interior Detail" in pricing
    assert "Exterior Detail" in pricing
    assert "Full Signature Detail" in pricing
    assert "8:00 AM" in pricing


def test_shop_knowledge_prep():
    """Verify prep requirements include key customer drop-off instructions."""
    prep = get_prep_summary()
    assert "Personal belongings" in prep
    assert "Child car seats" in prep
    assert "Fuel level" in prep


def test_vehicle_support():
    """Verify vehicle acceptance rules for sedans, SUVs, and unsupported RVs/boats."""
    res_sedan = check_vehicle_support("Toyota Camry Sedan")
    assert res_sedan["supported"] is True

    res_suv = check_vehicle_support("Ford Explorer SUV")
    assert res_suv["supported"] is True

    res_rv = check_vehicle_support("Fleetwood RV Motorhome")
    assert res_rv["supported"] is False
    assert "bay height" in res_rv["reason"].lower() or "limitations" in res_rv["reason"].lower()

    res_boat = check_vehicle_support("Ski Boat")
    assert res_boat["supported"] is False


def test_calendar_availability_conflict():
    """Verify slot conflict detection or alternative slot suggestion."""
    res = calendar_service.check_availability("Interior Detail", "Thursday", "3:30 PM")
    assert "alternative_slots" in res or res.get("available") is False


def test_booking_and_sheets_logging():
    """Verify booking an appointment adds calendar confirmation and sheets log entry."""
    res = calendar_service.book_appointment(
        customer_name="Test Customer",
        customer_phone="415-555-9999",
        service_name="Express Wash",
        date_str="2026-10-23",
        time_str="11:00 AM",
        vehicle_info="Honda Civic",
    )
    assert res["success"] is True
    assert "Booked" in res["confirmation"]

    sheets_service.log_call(
        caller_name="Test Customer",
        phone_number="415-555-9999",
        intent="Booking",
        summary="Booked express wash",
        status="Confirmed Booking",
    )
    contacts = sheets_service.get_contacts()
    entry = next((c for c in contacts if c.get("phone") == "415-555-9999"), None)
    assert entry is not None
    assert entry["name"] == "Test Customer"


def test_billing_dispute_escalation_flow():
    """Verify billing disputes trigger escalation tool call or mention owner review."""
    conv = [
        {
            "role": "user",
            "content": (
                "I was overcharged $45 on my bill yesterday! My name is Arthur Pendelton, "
                "phone 415-555-0777. I need this fixed."
            ),
        }
    ]
    reply, actions = agent.chat(conv)
    has_tool = any(a["tool"] == "log_escalation_or_inquiry" for a in actions)
    has_mention = "mike" in reply.lower() or "owner" in reply.lower() or "manager" in reply.lower()
    assert has_tool or has_mention, f"Expected escalation log or owner mention, got: {reply}"
