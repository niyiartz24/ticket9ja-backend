from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import os
import shutil

from database import get_db, init_db
from models import User, Event, Ticket
from auth import authenticate_user, create_access_token, get_current_user, create_default_user
from ticket_utils import generate_ticket_id, generate_qr_code, render_ticket_image, UPLOAD_DIR
from email_service import send_ticket_email

app = FastAPI(title="Ticket9ja API", version="2.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

uploads_path = os.path.join(os.path.dirname(__file__), "..", "uploads")
tickets_path = os.path.join(os.path.dirname(__file__), "..", "tickets")
os.makedirs(uploads_path, exist_ok=True)
os.makedirs(tickets_path, exist_ok=True)

try:
    app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")
    app.mount("/tickets", StaticFiles(directory=tickets_path), name="tickets")
except:
    pass

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class EventCreate(BaseModel):
    name: str
    event_date: str
    event_time: str
    venue: str
    city: str
    description: Optional[str] = ""

class EventResponse(BaseModel):
    id: int
    name: str
    event_date: str
    event_time: str
    venue: str
    city: str
    description: Optional[str]
    ticket_design_path: Optional[str]
    is_active: bool
    is_locked: bool
    created_at: datetime
    class Config:
        from_attributes = True

class TicketCreate(BaseModel):
    attendee_name: str
    attendee_email: EmailStr
    ticket_type: str
    quantity: int = 1

class TicketUpdate(BaseModel):
    attendee_name: Optional[str] = None
    attendee_email: Optional[EmailStr] = None
    ticket_type: Optional[str] = None

class TicketResponse(BaseModel):
    id: int
    ticket_id: str
    event_id: int
    attendee_name: str
    attendee_email: str
    ticket_type: str
    is_used: bool
    used_at: Optional[datetime]
    created_at: datetime
    class Config:
        from_attributes = True

class ScanRequest(BaseModel):
    ticket_id: str

class DashboardStats(BaseModel):
    total_tickets: int
    used_tickets: int
    remaining_tickets: int
    total_events: int
    active_events: int

@app.on_event("startup")
async def startup_event():
    init_db()
    db = next(get_db())
    create_default_user(db)
    db.close()

@app.get("/")
async def root():
    return {"message": "Ticket9ja API v2.0", "status": "running"}

# ==================== AUTH ROUTES ====================

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer", 
            "user": {"id": user.id, "username": user.username, "email": user.email}}

@app.get("/api/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email}

# ==================== EVENT ROUTES ====================

@app.post("/api/events", response_model=EventResponse)
async def create_event(event_data: EventCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new event - multiple events allowed"""
    new_event = Event(
        name=event_data.name, 
        event_date=event_data.event_date, 
        event_time=event_data.event_time,
        venue=event_data.venue, 
        city=event_data.city, 
        description=event_data.description, 
        is_active=True, 
        is_locked=False
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event

@app.get("/api/events", response_model=List[EventResponse])
async def get_all_events(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all events (active and past)"""
    events = db.query(Event).order_by(Event.created_at.desc()).all()
    return events

@app.get("/api/events/active", response_model=List[EventResponse])
async def get_active_events(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get only active events"""
    events = db.query(Event).filter(Event.is_active == True).order_by(Event.created_at.desc()).all()
    return events

@app.get("/api/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get specific event by ID"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event

@app.put("/api/events/{event_id}", response_model=EventResponse)
async def update_event(event_id: int, event_data: EventCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update event (only if not locked)"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.is_locked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit event after tickets have been generated")
    
    event.name = event_data.name
    event.event_date = event_data.event_date
    event.event_time = event_data.event_time
    event.venue = event_data.venue
    event.city = event_data.city
    event.description = event_data.description
    db.commit()
    db.refresh(event)
    return event

@app.delete("/api/events/{event_id}")
async def delete_event(event_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete an event and all associated tickets"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    
    # Delete associated tickets
    db.query(Ticket).filter(Ticket.event_id == event_id).delete()
    
    # Delete event
    db.delete(event)
    db.commit()
    
    return {"message": f"Event '{event.name}' and all associated tickets deleted successfully"}

@app.post("/api/events/{event_id}/toggle-active")
async def toggle_event_active(event_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Toggle event active/inactive status"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    
    event.is_active = not event.is_active
    db.commit()
    db.refresh(event)
    
    status_text = "activated" if event.is_active else "deactivated"
    return {"message": f"Event '{event.name}' {status_text}", "is_active": event.is_active}

@app.post("/api/events/{event_id}/upload-design")
async def upload_ticket_design(event_id: int, file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Upload ticket design for event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")
    
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"design_{event_id}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    event.ticket_design_path = file_path
    db.commit()
    db.refresh(event)
    return {"message": "Ticket design uploaded successfully", "path": file_path}

# ==================== TICKET ROUTES ====================

@app.post("/api/events/{event_id}/tickets", response_model=List[TicketResponse])
async def create_tickets(event_id: int, ticket_data: TicketCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create tickets for a specific event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    
    if not event.is_locked:
        event.is_locked = True
        db.commit()
    
    created_tickets = []
    for i in range(ticket_data.quantity):
        ticket_id = generate_ticket_id()
        qr_code_path = generate_qr_code(ticket_id)
        ticket_image_path = render_ticket_image(
            event.ticket_design_path or "", 
            ticket_data.attendee_name, 
            ticket_data.ticket_type,
            ticket_id, 
            qr_code_path, 
            event.name, 
            event.event_date, 
            event.event_time, 
            event.venue
        )
        
        new_ticket = Ticket(
            ticket_id=ticket_id, 
            event_id=event.id, 
            attendee_name=ticket_data.attendee_name,
            attendee_email=ticket_data.attendee_email, 
            ticket_type=ticket_data.ticket_type,
            qr_code_path=qr_code_path, 
            ticket_image_path=ticket_image_path, 
            is_used=False
        )
        
        db.add(new_ticket)
        db.commit()
        db.refresh(new_ticket)
        
        send_ticket_email(
            ticket_data.attendee_email, 
            ticket_data.attendee_name, 
            event.name, 
            event.event_date,
            event.event_time, 
            event.venue, 
            event.city, 
            ticket_id, 
            ticket_data.ticket_type, 
            ticket_image_path
        )
        
        created_tickets.append(new_ticket)
    
    return created_tickets

@app.get("/api/events/{event_id}/tickets", response_model=List[TicketResponse])
async def get_event_tickets(event_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all tickets for a specific event"""
    tickets = db.query(Ticket).filter(Ticket.event_id == event_id).order_by(Ticket.created_at.desc()).all()
    return tickets

@app.get("/api/tickets", response_model=List[TicketResponse])
async def get_all_tickets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all tickets across all events"""
    tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).all()
    return tickets

@app.get("/api/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get specific ticket"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket

@app.put("/api/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(ticket_id: int, ticket_data: TicketUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update ticket (preserves ticket_id and QR)"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    
    if ticket_data.attendee_name:
        ticket.attendee_name = ticket_data.attendee_name
    if ticket_data.attendee_email:
        ticket.attendee_email = ticket_data.attendee_email
    if ticket_data.ticket_type:
        ticket.ticket_type = ticket_data.ticket_type
    
    ticket.updated_at = datetime.utcnow()
    event = db.query(Event).filter(Event.id == ticket.event_id).first()
    
    ticket.ticket_image_path = render_ticket_image(
        event.ticket_design_path or "", 
        ticket.attendee_name, 
        ticket.ticket_type,
        ticket.ticket_id, 
        ticket.qr_code_path, 
        event.name, 
        event.event_date, 
        event.event_time, 
        event.venue
    )
    
    db.commit()
    db.refresh(ticket)
    return ticket

@app.delete("/api/tickets/{ticket_id}")
async def delete_ticket(ticket_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a specific ticket"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    
    ticket_info = f"{ticket.attendee_name} - {ticket.ticket_id}"
    
    # Delete ticket files if they exist
    try:
        if ticket.qr_code_path and os.path.exists(ticket.qr_code_path):
            os.remove(ticket.qr_code_path)
        if ticket.ticket_image_path and os.path.exists(ticket.ticket_image_path):
            os.remove(ticket.ticket_image_path)
    except Exception as e:
        print(f"Warning: Could not delete ticket files: {e}")
    
    db.delete(ticket)
    db.commit()
    
    return {"message": f"Ticket deleted successfully: {ticket_info}"}

@app.post("/api/tickets/{ticket_id}/resend")
async def resend_ticket(ticket_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Resend ticket email"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    
    event = db.query(Event).filter(Event.id == ticket.event_id).first()
    success = send_ticket_email(
        ticket.attendee_email, 
        ticket.attendee_name, 
        event.name, 
        event.event_date,
        event.event_time, 
        event.venue, 
        event.city, 
        ticket.ticket_id, 
        ticket.ticket_type, 
        ticket.ticket_image_path
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send email")
    return {"message": "Ticket email resent successfully"}

# ==================== SCAN ROUTES ====================

@app.post("/api/scan/validate")
async def validate_ticket(scan_data: ScanRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Validate scanned ticket"""
    ticket = db.query(Ticket).filter(Ticket.ticket_id == scan_data.ticket_id).first()
    
    if not ticket:
        return {"valid": False, "message": "Invalid ticket - not found", "status": "invalid"}
    
    if ticket.is_used:
        return {
            "valid": False, 
            "message": f"Ticket already used on {ticket.used_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "status": "already_used", 
            "ticket": {
                "attendee_name": ticket.attendee_name, 
                "ticket_type": ticket.ticket_type, 
                "used_at": ticket.used_at.isoformat()
            }
        }
    
    ticket.is_used = True
    ticket.used_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    
    event = db.query(Event).filter(Event.id == ticket.event_id).first()
    
    return {
        "valid": True, 
        "message": "Entry granted", 
        "status": "valid",
        "ticket": {
            "attendee_name": ticket.attendee_name, 
            "ticket_type": ticket.ticket_type, 
            "ticket_id": ticket.ticket_id, 
            "event_name": event.name
        }
    }

# ==================== DASHBOARD ROUTES ====================

@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get overall dashboard statistics"""
    total_events = db.query(Event).count()
    active_events = db.query(Event).filter(Event.is_active == True).count()
    total_tickets = db.query(Ticket).count()
    used_tickets = db.query(Ticket).filter(Ticket.is_used == True).count()
    
    return {
        "total_tickets": total_tickets,
        "used_tickets": used_tickets,
        "remaining_tickets": total_tickets - used_tickets,
        "total_events": total_events,
        "active_events": active_events
    }

@app.get("/api/events/{event_id}/stats")
async def get_event_stats(event_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get statistics for specific event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    
    total_tickets = db.query(Ticket).filter(Ticket.event_id == event_id).count()
    used_tickets = db.query(Ticket).filter(Ticket.event_id == event_id, Ticket.is_used == True).count()
    
    return {
        "event_id": event_id,
        "event_name": event.name,
        "total_tickets": total_tickets,
        "used_tickets": used_tickets,
        "remaining_tickets": total_tickets - used_tickets,
        "is_active": event.is_active,
        "is_locked": event.is_locked
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)