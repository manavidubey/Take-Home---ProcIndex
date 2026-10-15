# Cedar Lane Auto Detailing - AI Receptionist

AI receptionist system for Cedar Lane Auto Detailing, an auto detailing shop in Mill Valley, CA handling ~30 inbound calls a day.

The system is split into two phases:
- **Phase 1 (Core Agent & Web UI):** Handles booking, rescheduling, cancellations, late notifications, price/hours checks, prep questions, vehicle compatibility, and billing disputes with direct Google Calendar and Google Sheets synchronization.
- **Phase 2 (Voice Integration):** Low-latency voice agent built on Vapi with Deepgram Nova-2 transcription and Cartesia Sonic TTS.

---

## Architecture Overview

```
                          Inbound Call / Web Chat
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
           Phase 1: Web Chat UI              Phase 2: Vapi Voice
        (FastAPI + Inspector Panel)         (Webhooks + Function Calling)
                    │                                 │
                    └────────────────┬────────────────┘
                                     │
                                     ▼
                            Receptionist Agent
                         (OpenAI / Groq LLM Loop)
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
             Google Calendar                    Google Sheets
          (Appointments & Slots)               ("Contacts" Tab)
```

### Handled Call Flows

| Scenario | Handled By | System Action | Calendar / Sheets Impact |
| :--- | :--- | :--- | :--- |
| **Book appointment** | Agent | Checks slot availability. If booked, proposes next open slot (e.g. 4:30 PM). Collects customer name, phone, and vehicle. | Creates event in Google Calendar; adds caller row in Sheets `Contacts` tab. |
| **Reschedule booking** | Agent | Finds existing booking by name or phone, checks new requested slot, and moves event. | Updates Google Calendar start/end times; logs status in Sheets as `Rescheduled`. |
| **Pricing & hours inquiry** | Agent | Returns shop hours (Mon-Sat 8:00 AM - 6:00 PM, closed Sun) and exact package rates ($60-$275). | Read-only. |
| **Billing dispute** | **Human Escalation** | Agent never argues or debates charges. Apologizes, collects charge amount, vehicle, and date, then guarantees callback from owner Mike Henderson today. | Logs row with status `ESCALATED: Owner Review Required` in Sheets. |
| **Prep requirements** | Agent | Details checklist: remove valuables, remove child seats if shampooing underneath, 1/4 tank fuel. | Read-only. |
| **Vehicle type inquiry** | Agent | Confirms cars/SUVs/trucks/vans/EVs. Explains that RVs, motorhomes, and boats cannot fit in bays (10ft height limit). | Read-only. |
| **Running late notice** | Agent | Informs caller of 15-minute grace period; holds bay up to 30 mins. | Adds late note to Calendar event description and updates bay status. |

---

## Google Calendar & Sheets Setup

### Google Calendar
- Target calendar: `545554d58631fde9dfc44723a1e860e0f49970ac99055e66992666a0ddeb478f@group.calendar.google.com`
- Event format: `[Service Name] - Customer Name (Phone)`
- Slot duration: Calculated dynamically per service (45 min to 150 min).

### Google Sheets ("Contacts" Tab)
Each caller has a tracked record logged with:
1. `Caller ID` (e.g. `CL-1001`)
2. `Customer Name`
3. `Phone Number`
4. `Last Call Date/Time`
5. `Call Intent / Category`
6. `Service Requested`
7. `Appointment Scheduled`
8. `Status` (`Confirmed Booking`, `Rescheduled`, `ESCALATED: Owner Review Required`, etc.)
9. `Follow-up / Action Required`
10. `Call Summary & Notes`

*Note on offline fallback:* If `service_account.json` or sheet ID is not provided, the services smoothly fall back to local disk storage (`data/contacts.json` and `data/contacts.csv`) so full end-to-end functionality and testing works offline out-of-the-box.

---

## Project Setup & Running Locally

### 1. Requirements & Virtualenv
Python 3.10+ is recommended.

```bash
git clone https://github.com/manavidubey/Take-Home---ProcIndex.git
cd Take-Home---ProcIndex

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables
Create `.env` from the provided example:
```bash
cp .env.example .env
```

Set your LLM credentials:
```ini
LLM_PROVIDER=openai          # or 'groq'
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini     # or gpt-4o

GOOGLE_SERVICE_ACCOUNT_PATH=./service_account.json
GOOGLE_CALENDAR_ID=545554d58631fde9dfc44723a1e860e0f49970ac99055e66992666a0ddeb478f@group.calendar.google.com
GOOGLE_SHEET_ID=
```

### 3. Seed Calendar Events (Test Conflict)
To populate the calendar with initial appointments (including the Thursday 3:30 PM conflict slot):
```bash
python scripts/seed_calendar.py
```

### 4. Run the Dev Server & UI
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open `http://localhost:8000` to interact with:
- The conversational chat interface
- Live Google Calendar appointments inspector
- Live Google Sheets Contacts tab inspector
- Phase 2 Vapi payload export & webhook tester

---

## Testing & Quality Assurance

### Run Unit & Integration Tests
```bash
PYTHONPATH=. pytest tests/test_flows.py -v
```

### Run Full Conversation Flow Verifier
```bash
python scripts/test_agent.py
```

### Linting
The codebase is validated against pylint with a score of 10.00/10:
```bash
pylint app/
pylint tests/test_flows.py
```

---

## Phase 2: Vapi Voice Integration

The voice assistant payload and webhook handlers are fully implemented:
1. Start your local server and tunnel it:
   ```bash
   ngrok http 8000
   ```
2. In the web UI (`http://localhost:8000`), switch to the **Phase 2: Vapi Voice Setup** tab.
3. Paste the generated payload into the Vapi dashboard under **Create Assistant -> Advanced JSON**, or run:
   ```bash
   python scripts/setup_vapi.py
   ```
4. Webhooks route to `/api/vapi/webhook` with sub-1.2s roundtrip latency optimizations (Nova-2 255ms endpointing + Cartesia Sonic voice).

---

## Repository Structure

```
procindex/
├── .pylintrc                  # Pylint configuration
├── .env.example               # Template environment configuration
├── requirements.txt           # Python dependencies
├── service_account.example.json # Service account template
├── README.md                  # Project documentation
├── app/
│   ├── config.py              # Configuration & environment loading
│   ├── agent.py               # Receptionist agent loop & tool dispatcher
│   ├── prompts.py             # System prompt & tool JSON schema definitions
│   ├── main.py                # FastAPI web server & endpoints
│   ├── tools/
│   │   ├── calendar_service.py # Google Calendar API integration
│   │   ├── sheets_service.py   # Google Sheets API integration
│   │   └── shop_knowledge.py   # Business logic, pricing, prep & vehicle rules
│   ├── vapi/
│   │   ├── router.py          # Vapi webhook handlers
│   │   └── assistant_config.py # Voice assistant configuration generator
│   └── web/
│       ├── index.html         # Test chat UI & live inspector tabs
│       └── static/            # CSS & JS assets
├── data/
│   ├── contacts.csv           # Local mirror of Contacts tab
│   └── contacts.json          # Local mirror of Contacts tab (JSON)
├── scripts/
│   ├── seed_calendar.py       # Seeds test appointments on Google Calendar
│   ├── setup_vapi.py          # Automated Vapi assistant provisioning
│   └── test_agent.py          # Script verifying 7 core conversational scenarios
└── tests/
    └── test_flows.py          # Automated unit & integration tests
```
