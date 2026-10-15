"""Google Sheets Contacts log for Cedar Lane Auto Detailing."""

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.config import settings

SHEET_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CONTACTS_HEADER = [
    "Caller ID",
    "Customer Name",
    "Phone Number",
    "Last Call Date/Time",
    "Call Intent / Category",
    "Service Requested",
    "Appointment Scheduled",
    "Status",
    "Follow-up / Action Required",
    "Call Summary & Notes",
]


class SheetsService:
    """Syncs caller records to a Google Sheets 'Contacts' tab with a local JSON/CSV fallback."""

    def __init__(self):
        self.sheet_id = settings.GOOGLE_SHEET_ID
        self.service = None
        self.json_file = settings.CONTACTS_FILE
        self.csv_file = settings.CONTACTS_CSV
        self.contacts: List[Dict[str, Any]] = []
        self._load_local()
        self._connect()

    def _load_local(self):
        """Read contacts from local JSON store (or start fresh)."""
        self.json_file.parent.mkdir(parents=True, exist_ok=True)
        if self.json_file.exists():
            try:
                with open(self.json_file, "r", encoding="utf-8") as f:
                    self.contacts = json.load(f)
            except Exception:  # pylint: disable=broad-exception-caught
                self.contacts = []
        else:
            self.contacts = []
            self._save_local()

    def _connect(self):
        """Authenticate with the service account and initialise the Sheets client."""
        sf = settings.SERVICE_ACCOUNT_FILE
        if not os.path.exists(sf) or not self.sheet_id:
            return
        try:
            creds = service_account.Credentials.from_service_account_file(sf, scopes=SHEET_SCOPES)
            self.service = build("sheets", "v4", credentials=creds, cache_discovery=False)
            self._ensure_contacts_tab()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"[sheets] Couldn't connect: {exc}")

    def _ensure_contacts_tab(self):
        """Create the Contacts tab with headers if it doesn't already exist."""
        if not self.service or not self.sheet_id:
            return
        try:
            meta = self.service.spreadsheets().get(spreadsheetId=self.sheet_id).execute()  # type: ignore[attr-defined]
            tabs = [s["properties"]["title"] for s in meta.get("sheets", [])]

            if "Contacts" not in tabs:
                self.service.spreadsheets().batchUpdate(  # type: ignore[attr-defined]
                    spreadsheetId=self.sheet_id,
                    body={"requests": [{"addSheet": {"properties": {"title": "Contacts"}}}]},
                ).execute()

            header_check = self.service.spreadsheets().values().get(  # type: ignore[attr-defined]
                spreadsheetId=self.sheet_id, range="Contacts!A1:J1"
            ).execute()

            if not header_check.get("values"):
                self.service.spreadsheets().values().update(  # type: ignore[attr-defined]
                    spreadsheetId=self.sheet_id,
                    range="Contacts!A1:J1",
                    valueInputOption="RAW",
                    body={"values": [CONTACTS_HEADER]},
                ).execute()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"[sheets] Tab setup issue: {exc}")

    def _save_local(self):
        """Persist contacts to JSON and CSV files."""
        try:
            with open(self.json_file, "w", encoding="utf-8") as f:
                json.dump(self.contacts, f, indent=2)

            with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(CONTACTS_HEADER)
                for c in self.contacts:
                    writer.writerow([
                        c.get("caller_id", ""), c.get("name", ""), c.get("phone", ""),
                        c.get("timestamp", ""), c.get("intent", ""), c.get("service", ""),
                        c.get("appointment", ""), c.get("status", ""),
                        c.get("action_required", ""), c.get("notes", ""),
                    ])
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"[sheets] Couldn't save locally: {exc}")

    def log_call(
        self,
        caller_name: str,
        phone_number: str,
        intent: str,
        summary: str,
        service: Optional[str] = None,
        appointment: Optional[str] = None,
        status: Optional[str] = None,
        action_required: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert a caller record and sync it to Google Sheets."""
        now_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        name = caller_name.strip() if caller_name else "Anonymous Caller"
        phone = phone_number.strip() if phone_number else "Not Provided"

        # Find existing record by phone or name
        existing_idx = None
        for i, c in enumerate(self.contacts):
            phone_match = phone != "Not Provided" and c.get("phone") == phone
            name_match = name != "Anonymous Caller" and c.get("name", "").lower() == name.lower()
            if phone_match or name_match:
                existing_idx = i
                break

        if existing_idx is not None:
            rec = self.contacts[existing_idx]
            caller_id = rec["caller_id"]
            if name != "Anonymous Caller":
                rec["name"] = name
            if phone != "Not Provided":
                rec["phone"] = phone
            rec["timestamp"] = now_str
            rec["intent"] = intent
            if service:
                rec["service"] = service
            if appointment:
                rec["appointment"] = appointment
            if status:
                rec["status"] = status
            if action_required:
                rec["action_required"] = action_required
            prev = rec.get("notes", "")
            rec["notes"] = f"{summary} (updated {now_str}) | {prev}"[:400]
        else:
            caller_id = f"CL-{1000 + len(self.contacts) + 1}"
            rec = {
                "caller_id": caller_id,
                "name": name,
                "phone": phone,
                "timestamp": now_str,
                "intent": intent,
                "service": service or "N/A",
                "appointment": appointment or "None",
                "status": status or "Logged",
                "action_required": action_required or "None",
                "notes": summary,
            }
            self.contacts.append(rec)

        self._save_local()

        if self.service and self.sheet_id:
            try:
                row = [
                    rec["caller_id"], rec["name"], rec["phone"], rec["timestamp"],
                    rec["intent"], rec["service"], rec["appointment"],
                    rec["status"], rec["action_required"], rec["notes"],
                ]
                self.service.spreadsheets().values().append(  # type: ignore[attr-defined]
                    spreadsheetId=self.sheet_id,
                    range="Contacts!A:J",
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={"values": [row]},
                ).execute()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                print(f"[sheets] Sync failed: {exc}")

        return {
            "success": True,
            "caller_id": caller_id,
            "record": rec,
            "sheet_synced": bool(self.service and self.sheet_id),
        }

    def get_contacts(self) -> List[Dict[str, Any]]:
        """Return all logged contacts."""
        return self.contacts


sheets_service = SheetsService()
