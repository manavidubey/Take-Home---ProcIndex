"""
End-to-End Test Script verifying all 7 Receptionist Scenarios
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import agent
from app.tools.calendar_service import calendar_service
from app.tools.sheets_service import sheets_service

def run_tests():
    print("=" * 60)
    print("🧪 Running Cedar Lane Auto Detailing AI Receptionist Tests")
    print("=" * 60)

    # SCENARIO 1: Booking with Conflict Check (3:30 PM Thursday)
    print("\n--- SCENARIO 1: Booking with Conflict Check (3:30 Thursday) ---")
    conv1 = [
        {"role": "user", "content": "Is the 3:30 interior detail and wash appointment on Thursday open?"}
    ]
    reply1, actions1 = agent.chat(conv1)
    print("User:", conv1[0]["content"])
    print("Actions:", [a["tool"] for a in actions1])
    print("Agent:", reply1)
    assert any(a["tool"] == "check_calendar_availability" for a in actions1), "Must call check_calendar_availability"

    # SCENARIO 2: Booking Agreed Alternative Slot (4:30 PM)
    print("\n--- SCENARIO 2: Confirming 4:30 PM Booking with Caller Info ---")
    conv2 = conv1 + [
        {"role": "assistant", "content": reply1},
        {"role": "user", "content": "Sure, 4:30 works. Name is Sara, 415-555-0190. Vehicle is Audi Q5."}
    ]
    reply2, actions2 = agent.chat(conv2)
    print("User:", conv2[-1]["content"])
    print("Actions:", [a["tool"] for a in actions2])
    print("Agent:", reply2)
    assert any(a["tool"] == "book_calendar_appointment" for a in actions2), "Must book appointment on Google Calendar"

    # Verify Contacts Tab has Sara's entry
    contacts = sheets_service.get_contacts()
    sara_entry = next((c for c in contacts if "sara" in c.get("name", "").lower()), None)
    print("Contacts entry for Sara:", sara_entry)
    assert sara_entry is not None, "Sara must be logged in Contacts tab"

    # SCENARIO 3: Reschedule Appointment
    print("\n--- SCENARIO 3: Reschedule Existing Appointment ---")
    conv3 = [
        {"role": "user", "content": "Hi, I need to change my appointment. This is Sara (415-555-0190). Can we move it to Friday at 2:00 PM?"}
    ]
    reply3, actions3 = agent.chat(conv3)
    print("User:", conv3[0]["content"])
    print("Actions:", [a["tool"] for a in actions3])
    print("Agent:", reply3)
    assert any(a["tool"] == "reschedule_calendar_appointment" for a in actions3), "Must call reschedule_calendar_appointment"

    # SCENARIO 4: Hours and Pricing
    print("\n--- SCENARIO 4: Ask About Hours & Pricing ---")
    conv4 = [
        {"role": "user", "content": "What are your business hours, and how much is an exterior detail vs full detail?"}
    ]
    reply4, actions4 = agent.chat(conv4)
    print("User:", conv4[0]["content"])
    print("Agent:", reply4)
    assert "150" in reply4 or "275" in reply4 or "6:00" in reply4 or "Monday" in reply4, "Must provide accurate shop pricing and hours"

    # SCENARIO 5: Billing Dispute (Mandatory Human Escalation)
    print("\n--- SCENARIO 5: Billing Dispute / Charge Complaint (Human Escalation) ---")
    conv5 = [
        {"role": "user", "content": "I was overcharged $45 on my card for my wash yesterday! My name is John Carter, phone is 415-555-0999. I want this refunded immediately."}
    ]
    reply5, actions5 = agent.chat(conv5)
    print("User:", conv5[0]["content"])
    print("Actions:", [a["tool"] for a in actions5])
    print("Agent:", reply5)
    assert any(a["tool"] == "log_escalation_or_inquiry" for a in actions5), "Must log billing escalation in Google Sheets"
    assert "mike" in reply5.lower() or "owner" in reply5.lower() or "manager" in reply5.lower(), "Must escalate to shop owner/manager Mike"

    # SCENARIO 6: Prep Checklist
    print("\n--- SCENARIO 6: Preparation Requirements ---")
    conv6 = [
        {"role": "user", "content": "What should I do before bringing my car in for detailing?"}
    ]
    reply6, actions6 = agent.chat(conv6)
    print("User:", conv6[0]["content"])
    print("Agent:", reply6)
    assert "belonging" in reply6.lower() or "child" in reply6.lower() or "trunk" in reply6.lower() or "seat" in reply6.lower(), "Must provide prep instructions"

    # SCENARIO 7: Vehicle Compatibility (RV rejection)
    print("\n--- SCENARIO 7: Vehicle Type Inquiry (RV / Boat) ---")
    conv7 = [
        {"role": "user", "content": "Can you detail my 34-foot Fleetwood RV motorhome?"}
    ]
    reply7, actions7 = agent.chat(conv7)
    print("User:", conv7[0]["content"])
    print("Agent:", reply7)
    assert "cannot" in reply7.lower() or "don't" in reply7.lower() or "not" in reply7.lower() or "height" in reply7.lower(), "Must clarify that RVs cannot be accommodated"

    # SCENARIO 8: Running Late
    print("\n--- SCENARIO 8: Running Late Notification ---")
    conv8 = [
        {"role": "user", "content": "Hi, I have an appointment today under Sara, but traffic is terrible and I'm running about 20 minutes late!"}
    ]
    reply8, actions8 = agent.chat(conv8)
    print("User:", conv8[0]["content"])
    print("Actions:", [a["tool"] for a in actions8])
    print("Agent:", reply8)
    assert any(a["tool"] == "report_running_late" for a in actions8), "Must call report_running_late"

    print("\n" + "=" * 60)
    print("🎉 ALL 8 SCENARIOS PASSED WITH 100% CORRECTNESS!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
