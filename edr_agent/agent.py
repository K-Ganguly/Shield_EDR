from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
from typing import Callable
import asyncio
import httpx

# Environment variables
from decouple import config

SERVER_URL = config("SERVER_URL", default="http://localhost:5000/report")


# **Event Model**
class Event(BaseModel):
    """Schema for reporting events."""
    event_type: str
    timestamp: datetime


# **Event Reporter Service**
class EventReporterService:
    """Handles logic for reporting events to a server."""

    def __init__(self, server_url: str):
        self.server_url = server_url

    async def report_event(self, event_type: str):
        """Reports an event asynchronously."""
        event_data = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.server_url, json=event_data)
            if response.status_code != 201:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to report event: {response.text}",
                )
            return response.json()


# **Event Monitoring Service**
class EventMonitor:
    """Simulates monitoring events and sends reports periodically."""

    def __init__(self, event_reporter: EventReporterService, interval: int = 10):
        self.event_reporter = event_reporter
        self.interval = interval

    async def monitor(self, event_type: str):
        """Simulates monitoring and reporting events at intervals."""
        while True:
            print(f"Reporting event: {event_type} at {datetime.now()}")
            await self.event_reporter.report_event(event_type)
            await asyncio.sleep(self.interval)


# **FastAPI Application Setup**
class EventApp:
    """Sets up the FastAPI application."""

    def __init__(self, server_url: str):
        self.app = FastAPI()
        self.event_reporter = EventReporterService(server_url)
        self.monitor = EventMonitor(self.event_reporter)
        self._setup_routes()

    def _setup_routes(self):
        @self.app.post("/start_monitoring", status_code=200)
        async def start_monitoring(event: Event, background_tasks: BackgroundTasks):
            """Starts the event monitoring process."""
            background_tasks.add_task(self.monitor.monitor, event.event_type)
            return {"message": "Monitoring started"}

        @self.app.post("/report", status_code=201)
        async def report_event(event: Event):
            """Manually report an event."""
            return await self.event_reporter.report_event(event.event_type)


# Main Method
if __name__ == "__main__":
    import uvicorn

    # Environment variables for the host and port
    HOST = config("HOST", default="127.0.0.1")
    PORT = int(config("PORT", default=8000))

    # Create the FastAPI app instance and run
    app_instance = EventApp(SERVER_URL)
    app = app_instance.app

    uvicorn.run(app, host=HOST, port=PORT)
