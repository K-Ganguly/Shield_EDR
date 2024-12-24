from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
from typing import Callable
import asyncio
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt

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

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(5))
    async def report_event(self, event_type: str):
        """Reports an event asynchronously."""
        event_data = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.server_url, json=event_data)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to connect to server: {e}"
            )


# **Event Monitoring Service**
class EventMonitor:
    """Simulates monitoring events and sends reports periodically."""
    def __init__(self, event_reporter: EventReporterService, interval: int = 10):
        self.event_reporter = event_reporter
        self.interval = interval

    async def monitor(self, event_type: str):
        """Simulates monitoring and reporting events at intervals."""
        while True:
            try:
                print(f"Reporting event: {event_type} at {datetime.now()}")
                await self.event_reporter.report_event(event_type)
            except Exception as e:
                print(f"Error while reporting event: {e}")
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
    HOST = config("HOST", default="0.0.0.0")
    PORT = int(config("PORT", default=8000))

    # Create the FastAPI app instance and run
    app_instance = EventApp(SERVER_URL)
    app = app_instance.app

    uvicorn.run(app, host=HOST, port=PORT)
