"""
Seed Google Calendar with realistic appointments for Cedar Lane Auto Detailing.
Includes test conflict at 3:30 PM Thursday.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# pylint: disable=wrong-import-position
from app.tools.calendar_service import calendar_service
from app.tools.sheets_service import sheets_service


def seed():
    """Seed test conflict appointment and sample caller."""
    print("Seeding Cedar Lane Auto Detailing Calendar & Contacts...")

    # Calculate upcoming Thursday
    now = datetime.now()
    days_to_thursday = (3 - now.weekday()) % 7
    if days_to_thursday == 0 and now.hour >= 16:
        days_to_thursday = 7
    thursday = now + timedelta(days=days_to_thursday)
    thursday_str = thursday.strftime("%Y-%m-%d")

    # 1. Thursday 3:30 PM Conflict Event
    print(f"Creating 3:30 PM conflict event on Thursday ({thursday_str})...")
    res1 = calendar_service.book_appointment(
        customer_name="Marcus Vance",
        customer_phone="(415) 555-0821",
        service_name="Interior Detail & Wash",
        date_str=thursday_str,
        time_str="3:30 PM",
        vehicle_info="Porsche Cayenne SUV",
        notes="Pre-existing appointment booked yesterday",
    )
    print("-> Result:", res1.get("confirmation", res1))

    # 2. Thursday 10:00 AM Appointment
    print(f"Creating 10:00 AM morning event on Thursday ({thursday_str})...")
    res2 = calendar_service.book_appointment(
        customer_name="David Miller",
        customer_phone="(415) 555-0419",
        service_name="Express Wash & Vac",
        date_str=thursday_str,
        time_str="10:00 AM",
        vehicle_info="Tesla Model 3",
        notes="Child car seat removed by customer",
    )
    print("-> Result:", res2.get("confirmation", res2))

    # 3. Seed Marcus Vance in Google Sheets Contacts tab
    print("Seeding initial caller contact in Contacts tab...")
    sheets_service.log_call(
        caller_name="Marcus Vance",
        phone_number="(415) 555-0821",
        intent="Appointment Booking",
        summary="Booked Interior Detail & Wash for Porsche Cayenne on Thursday 3:30 PM",
        service="Interior Detail & Wash",
        appointment=f"Thursday {thursday_str} @ 3:30 PM",
        status="Confirmed Booking",
        action_required="None",
    )

    print("\nSeeding complete! 3:30 PM Thursday is booked and ready for conflict testing.")


if __name__ == "__main__":
    seed()
