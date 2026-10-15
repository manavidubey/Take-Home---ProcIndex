"""Shop business rules, service catalogue, and pricing for Cedar Lane Auto Detailing."""

SHOP_INFO = {
    "name": "Cedar Lane Auto Detailing",
    "phone": "(415) 555-0142",
    "address": "1204 Cedar Lane, Mill Valley, CA 94941",
    "timezone": "America/Los_Angeles",
    "hours": {
        "monday_to_saturday": "8:00 AM - 6:00 PM",
        "sunday": "Closed",
    },
    "owner": "Mike Henderson",
    "manager_phone": "(415) 555-0143",
}

SERVICES = {
    "express_wash": {
        "name": "Express Wash & Vac",
        "duration_minutes": 45,
        "price": 60,
        "description": (
            "Hand wash, foam bath, wheel & tire shine, interior vacuum, "
            "window cleaning, dashboard wipe."
        ),
    },
    "interior_detail": {
        "name": "Interior Detail",
        "duration_minutes": 90,
        "price": 175,
        "description": (
            "Steam clean all surfaces, hot water extraction on carpets & upholstery, "
            "leather conditioning, vents sanitized, trunk vacuumed, odor treatment."
        ),
    },
    "exterior_detail": {
        "name": "Exterior Detail",
        "duration_minutes": 90,
        "price": 150,
        "description": (
            "Two-bucket hand wash, iron removal, clay bar, machine polish, "
            "ceramic sealant (6-month protection), tire dressing."
        ),
    },
    "full_detail": {
        "name": "Full Signature Detail",
        "duration_minutes": 150,
        "price": 275,
        "description": (
            "Complete interior + exterior detail, engine bay wipe down, "
            "premium ceramic spray coating."
        ),
    },
}

ADD_ONS = {
    "headlight_restoration": {"name": "Headlight Restoration (pair)", "price": 50, "duration_minutes": 30},
    "engine_bay_detail": {"name": "Engine Bay Deep Cleaning", "price": 60, "duration_minutes": 30},
    "pet_hair_removal": {"name": "Excessive Pet Hair Removal", "price": 40, "duration_minutes": 30},
    "child_seat_sanitization": {"name": "Child Car Seat Sanitization", "price": 25, "duration_minutes": 15},
}

VEHICLE_SIZING = {
    "standard": {"name": "Sedan, Coupe, Hatchback", "surcharge": 0},
    "midsize": {"name": "Small/Midsize SUV, Crossover, Light Truck", "surcharge": 25},
    "oversized": {"name": "Full-size SUV, 3-Row SUV, Van, Heavy Truck", "surcharge": 45},
}

VEHICLE_ACCEPTANCE = {
    "accepted": [
        "Sedans", "Coupes", "Hatchbacks", "Station Wagons",
        "Crossovers", "SUVs (compact to full-size)", "Pickup Trucks",
        "Minivans", "Electric Vehicles (Tesla, Rivian, etc.)",
    ],
    "not_accepted": [
        "RVs / Motorhomes (exceed bay height limit of 10 ft)",
        "Boats and Marine Watercraft",
        "Commercial Semi-Trucks and Large Box Vans",
        "Motorcycles",
    ],
    "commercial_fleet": "Fleet vehicles by custom arrangement — manager calls back with corporate pricing.",
}

PREP_REQUIREMENTS = [
    "Personal belongings: Remove all personal items, valuables, and loose change from the cabin, console, and trunk.",
    "Child car seats: Remove if you want the upholstery underneath shampooed.",
    "Fuel level: At least a quarter tank of fuel so we can reposition the car in the bays.",
    "Let us know at drop-off if the vehicle has vinyl wrap, matte paint, or delicate leather.",
]

RUNNING_LATE_POLICY = {
    "grace_period_minutes": 15,
    "up_to_30_mins": "Fine — we'll hold the bay, but completion time may shift a bit.",
    "over_45_mins": "If more than 45 minutes late we may need to reschedule or trim the scope.",
    "action": "Agent notes the delay and informs bay technicians.",
}

BILLING_DISPUTE_POLICY = {
    "human_handoff_mandatory": True,
    "instructions": (
        "Never argue or dispute charges. Express empathy, apologize for confusion. "
        "Get name, phone, vehicle info, service date, and disputed amount. "
        "Tell them Mike Henderson will personally review the ticket and call them back today."
    ),
}


def get_pricing_summary() -> str:
    """Return a plain-text pricing overview for all services."""
    lines = ["Cedar Lane Auto Detailing — Services & Rates:\n"]
    for svc in SERVICES.values():
        lines.append(f"• {svc['name']}: ${svc['price']} (~{svc['duration_minutes']} min)")
        lines.append(f"  {svc['description']}")
    lines.append("\nVehicle size surcharges:")
    for size in VEHICLE_SIZING.values():
        if size["surcharge"] > 0:
            lines.append(f"• {size['name']}: +${size['surcharge']}")
    lines.append("\nHours: Mon–Sat 8:00 AM–6:00 PM, closed Sundays.")
    return "\n".join(lines)


def get_prep_summary() -> str:
    """Return the customer prep checklist as plain text."""
    lines = ["Before you drop off:\n"]
    for item in PREP_REQUIREMENTS:
        lines.append(f"• {item}")
    return "\n".join(lines)


def check_vehicle_support(vehicle_type: str) -> dict:
    """Return whether we can detail the given vehicle type."""
    v = vehicle_type.lower()
    blocked = ["rv", "motorhome", "boat", "marine", "semi", "commercial box", "motorcycle"]
    if any(b in v for b in blocked):
        return {
            "supported": False,
            "reason": f"We can't accommodate {vehicle_type} due to bay height and equipment limits.",
        }
    return {
        "supported": True,
        "reason": f"Yes, we detail {vehicle_type}. Standard pricing applies.",
    }
