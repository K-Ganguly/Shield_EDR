from fastapi import FastAPI, Depends
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from abc import ABC, abstractmethod
from decouple import config
import uvicorn

# Load environment variables
DATABASE_URL = config("DATABASE_URL")
HOST = config("HOST", default="0.0.0.0")
PORT = int(config("PORT", default=5000))

# SQLAlchemy setup
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Database:
    """Manages database connection and session lifecycle."""
    def __init__(self, db_sessionmaker):
        self.SessionLocal = db_sessionmaker

    def get_session(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def create_tables(self):
        Base.metadata.create_all(bind=engine)


class Event(Base):
    """Defines the Event entity."""
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False)


class EventCreate(BaseModel):
    """Defines the schema for creating an event."""
    event_type: str
    timestamp: datetime


class IEventRepository(ABC):
    """Interface for event repository."""
    @abstractmethod
    def add_event(self, event_type: str, timestamp: datetime):
        pass


class EventRepository(IEventRepository):
    """Concrete implementation of IEventRepository using SQLAlchemy."""
    def __init__(self, db: Session):
        self.db = db

    def add_event(self, event_type: str, timestamp: datetime):
        new_event = Event(event_type=event_type, timestamp=timestamp)
        self.db.add(new_event)
        self.db.commit()
        self.db.refresh(new_event)
        return new_event


class EventService:
    """Handles event-related business logic."""
    def __init__(self, event_repository: IEventRepository):
        self.event_repository = event_repository

    def create_event(self, event_type: str, timestamp: datetime):
        return self.event_repository.add_event(event_type, timestamp)


class EventController:
    """Handles API endpoints for events."""
    def __init__(self, db: Database):
        self.db = db

    def create_event_endpoint(self, event_data: EventCreate, db: Session = Depends(SessionLocal)):
        repository = EventRepository(db)
        service = EventService(repository)
        service.create_event(event_data.event_type, event_data.timestamp)
        return {"message": "Event recorded"}


class EventApp:
    """Sets up the FastAPI application."""
    def __init__(self, database: Database):
        self.app = FastAPI()
        self.database = database
        self.controller = EventController(self.database)
        self._setup_routes()

    def _setup_routes(self):
        @self.app.post("/report", status_code=201)
        def create_event(event_data: EventCreate, db: Session = Depends(self.database.get_session)):
            return self.controller.create_event_endpoint(event_data, db)


# Main method
if __name__ == "__main__":
    # Initialize the database
    database = Database(SessionLocal)
    database.create_tables()

    # Create FastAPI application instance
    event_app = EventApp(database)

    # Start the FastAPI application using uvicorn
    uvicorn.run(event_app.app, host=HOST, port=PORT)
