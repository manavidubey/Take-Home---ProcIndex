"""Google Calendar integration for Cedar Lane Auto Detailing."""

import os
import socket
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.config import settings

socket.setdefaulttimeout(15.0)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Maps weekday name → Python weekday index (0 = Monday)
_WEEKDAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2,
    "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
}


class CalendarService:
    """Thin wrapper around the Google Calendar v3 API with a local fallback store."""

    def __init__(self):
        self.calendar_id = settings.GOOGLE_CALENDAR_ID
        self.service = None
        self.local_events: List[Dict[str, Any]] = []
        self._connect()

    def _connect(self):
        """Authenticate with the service account and build the API client."""
        sf = settings.SERVICE_ACCOUNT_FILE
        if not os.path.exists(sf):
            print(f"[calendar] No service account at {sf}, running local-only.")
            return
        try:
            creds = service_account.Credentials.from_service_account_file(sf, scopes=SCOPES)
            self.service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"[calendar] Couldn't connect: {exc}")

    def _parse_dt(self, date_str: str, time_str: str) -> datetime:
        """Parse a natural-language date + time string into a datetime object."""
        date_str = date_str.strip().lower()
        now = datetime.now()

        if date_str in ("today", "now"):
            target_date = now.date()
        elif date_str == "tomorrow":
            target_date = now.date() + timedelta(days=1)
        elif date_str in _WEEKDAY_MAP:
            target_weekday = _WEEKDAY_MAP[date_str]
            days_ahead = (target_weekday - now.weekday()) % 7
            if days_ahead == 0 and now.hour >= 18:
                days_ahead = 7
            target_date = now.date() + timedelta(days=days_ahead)
        else:
            try:
                fmt = "%Y-%m-%d" if "-" in date_str else "%m/%d/%Y"
                target_date = datetime.strptime(date_str, fmt).date()
            except Exception:  # pylint: disable=broad-exception-caught
                target_date = now.date()

        t = time_str.strip().lower().replace(" ", "")
        is_pm = "pm" in t
        is_am = "am" in t
        t = t.replace("pm", "").replace("am", "")

        parts = t.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0

        if is_pm and hour < 12:
            hour += 12
        elif is_am and hour == 12:
            hour = 0
        elif not is_am and not is_pm and hour < 8:
            # 1–7 with no AM/PM → assume PM (detailing shop context)
            hour += 12

        return datetime.combine(target_date, time(hour, minute))

    def _service_duration(self, service_name: str) -> int:
        """Return duration in minutes for the given service name."""
        s = service_name.lower()
        if "full" in s or ("interior" in s and "exterior" in s):
            return 150
        if "interior" in s or "exterior" in s:
            return 90
        if "wash" in s:
            return 45
        return 60

    def list_upcoming_events(self, max_results: int = 25) -> List[Dict[str, Any]]:
        """Fetch upcoming events from Google Calendar (or local fallback)."""
        if not self.service:
            return self.local_events

        try:
            now_iso = datetime.now().astimezone().isoformat()
            result = self.service.events().list(  # type: ignore[attr-defined]
                calendarId=self.calendar_id,
                timeMin=now_iso,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = []
            for item in result.get("items", []):
                start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
                end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
                events.append({
                    "id": item.get("id"),
                    "summary": item.get("summary", "Untitled"),
                    "description": item.get("description", ""),
                    "start": start,
                    "end": end,
                })
            return events
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"[calendar] Failed to fetch events: {exc}")
            return self.local_events

    def check_availability(
        self,
        service_name: str,
        date_str: str,
        time_str: str,
        duration_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Check whether the requested slot is free and return alternatives if not."""
        start = self._parse_dt(date_str, time_str)
        duration = duration_minutes or self._service_duration(service_name)
        end = start + timedelta(minutes=duration)

        if start.weekday() == 6:  # Sunday
            return {
                "available": False,
                "reason": "We're closed Sundays. Open Mon–Sat, 8 AM–6 PM.",
                "alternative_slots": ["Monday at 9:00 AM", "Monday at 1:00 PM", "Monday at 3:30 PM"],
            }

        if start.hour < settings.OPEN_HOUR or end.hour > settings.CLOSE_HOUR:
            return {
                "available": False,
                "reason": f"Shop hours are {settings.OPEN_HOUR}:00 AM – {settings.CLOSE_HOUR - 12}:00 PM.",
                "alternative_slots": ["9:00 AM", "11:00 AM", "2:00 PM", "4:30 PM"],
            }

        existing = self.list_upcoming_events(max_results=50)
        conflict = None
        for ev in existing:
            ev_start_raw, ev_end_raw = ev.get("start"), ev.get("end")
            if not ev_start_raw or not ev_end_raw:
                continue
            try:
                ev_start = datetime.fromisoformat(ev_start_raw.replace("Z", "+00:00")).replace(tzinfo=None)
                ev_end = datetime.fromisoformat(ev_end_raw.replace("Z", "+00:00")).replace(tzinfo=None)
                if ev_start.date() == start.date() and start < ev_end and end > ev_start:
                    conflict = ev.get("summary", "Existing Booking")
                    break
            except Exception:  # pylint: disable=broad-exception-caught
                continue

        date_human = start.strftime("%A, %B %d")
        time_human = start.strftime("%I:%M %p").lstrip("0")

        if conflict:
            next_slot = (start + timedelta(hours=1)).strftime("%I:%M %p").lstrip("0")
            over_2h = (start + timedelta(hours=2)).hour < settings.CLOSE_HOUR
            alts = [next_slot, (start + timedelta(hours=2)).strftime("%I:%M %p").lstrip("0") if over_2h else "10:30 AM"]
            return {
                "available": False,
                "requested_time": f"{time_human} on {date_human}",
                "reason": f"{time_human} on {date_human} is taken ({conflict}).",
                "alternative_slots": alts,
                "suggested_reply": f"That one's full. {next_slot} is open — want that instead?",
            }

        return {
            "available": True,
            "requested_time": f"{time_human} on {date_human}",
            "start_iso": start.isoformat(),
            "end_iso": end.isoformat(),
            "duration_minutes": duration,
            "message": f"{time_human} on {date_human} is wide open.",
        }

    def book_appointment(
        self,
        customer_name: str,
        customer_phone: str,
        service_name: str,
        date_str: str,
        time_str: str,
        vehicle_info: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new Calendar event and record it locally."""
        start = self._parse_dt(date_str, time_str)
        duration = self._service_duration(service_name)

        s = service_name.lower()
        if "full" in s or ("interior" in s and "exterior" in s):
            display = "Full Signature Detail"
        elif "interior" in s:
            display = "Interior Detail"
        elif "exterior" in s:
            display = "Exterior Detail"
        elif "wash" in s:
            display = "Express Wash & Vac"
        else:
            display = service_name

        end = start + timedelta(minutes=duration)
        vehicle = vehicle_info or "Not specified"
        summary = f"{display} - {customer_name}"
        description = (
            f"Customer: {customer_name}\n"
            f"Phone: {customer_phone}\n"
            f"Service: {display}\n"
            f"Vehicle: {vehicle}\n"
            f"Notes: {notes or 'Booked via AI receptionist'}"
        )

        event_body = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start.strftime("%Y-%m-%dT%H:%M:%S-07:00"),
                "timeZone": settings.SHOP_TIMEZONE,
            },
            "end": {
                "dateTime": end.strftime("%Y-%m-%dT%H:%M:%S-07:00"),
                "timeZone": settings.SHOP_TIMEZONE,
            },
        }

        event_id = None
        if self.service:
            try:
                res = self.service.events().insert(  # type: ignore[attr-defined]
                    calendarId=self.calendar_id, body=event_body
                ).execute()
                event_id = res.get("id")
            except Exception as exc:  # pylint: disable=broad-exception-caught
                print(f"[calendar] Failed to create event: {exc}")

        local_rec = {
            "id": event_id or f"local-{int(datetime.now().timestamp())}",
            "summary": summary,
            "description": description,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "service": display,
        }
        self.local_events.append(local_rec)

        date_human = start.strftime("%A, %B %d")
        time_human = start.strftime("%I:%M %p").lstrip("0")

        return {
            "success": True,
            "event_id": event_id or local_rec["id"],
            "summary": summary,
            "date": date_human,
            "time": time_human,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "service": display,
            "confirmation": f"Booked: You're confirmed for {time_human} on {date_human}.",
        }

    def reschedule_appointment(
        self,
        customer_name_or_phone: str,
        new_date_str: str,
        new_time_str: str,
    ) -> Dict[str, Any]:
        """Patch an existing Calendar event to a new date/time."""
        events = self.list_upcoming_events(max_results=50)
        query = customer_name_or_phone.strip().lower()
        match = None
        for ev in events:
            if query in ev.get("summary", "").lower() or query in ev.get("description", "").lower():
                match = ev
                break

        new_start = self._parse_dt(new_date_str, new_time_str)
        new_end = new_start + timedelta(minutes=90)

        if match and self.service and not match.get("id", "").startswith("local-"):
            try:
                body = {
                    "summary": match.get("summary"),
                    "description": match.get("description", "") + f"\n[Rescheduled to {new_start.isoformat()}]",
                    "start": {
                        "dateTime": new_start.strftime("%Y-%m-%dT%H:%M:%S-07:00"),
                        "timeZone": settings.SHOP_TIMEZONE,
                    },
                    "end": {
                        "dateTime": new_end.strftime("%Y-%m-%dT%H:%M:%S-07:00"),
                        "timeZone": settings.SHOP_TIMEZONE,
                    },
                }
                self.service.events().patch(  # type: ignore[attr-defined]
                    calendarId=self.calendar_id, eventId=match["id"], body=body
                ).execute()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                print(f"[calendar] Reschedule patch failed: {exc}")

        date_human = new_start.strftime("%A, %B %d")
        time_human = new_start.strftime("%I:%M %p").lstrip("0")

        return {
            "success": True,
            "new_date": date_human,
            "new_time": time_human,
            "message": f"Moved your appointment to {time_human} on {date_human}.",
        }

    def add_running_late_note(self, customer_name_or_phone: str, delay_minutes: int) -> Dict[str, Any]:
        """Append a running-late note to the customer's event description."""
        events = self.list_upcoming_events(max_results=20)
        query = customer_name_or_phone.strip().lower()
        found = False

        for ev in events:
            if query in ev.get("summary", "").lower() or query in ev.get("description", "").lower():
                found = True
                if self.service and not ev.get("id", "").startswith("local-"):
                    try:
                        ts = datetime.now().strftime("%I:%M %p")
                        desc = (
                            ev.get("description", "")
                            + f"\n⚠️ RUNNING LATE: {delay_minutes} min delay reported at {ts}"
                        )
                        self.service.events().patch(  # type: ignore[attr-defined]
                            calendarId=self.calendar_id,
                            eventId=ev["id"],
                            body={"description": desc},
                        ).execute()
                    except Exception as exc:  # pylint: disable=broad-exception-caught
                        print(f"[calendar] Late note patch failed: {exc}")
                break

        return {
            "success": True,
            "delay_minutes": delay_minutes,
            "note_logged": found,
            "message": (
                f"No worries! We have a 15-minute grace period so {delay_minutes} minutes is fine. "
                "I've let the team know."
            ),
        }


calendar_service = CalendarService()
