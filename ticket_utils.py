import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
import uuid
from datetime import datetime

# Paths
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
TICKETS_DIR = os.path.join(os.path.dirname(__file__), "..", "tickets")
QR_DIR = os.path.join(TICKETS_DIR, "qr_codes")

# Create directories
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TICKETS_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)


def generate_ticket_id() -> str:
    """Generate a unique ticket ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"TKT-{timestamp}-{unique_id}"


def generate_qr_code(ticket_id: str) -> str:
    """Generate QR code for a ticket"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(ticket_id)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    filename = f"qr_{ticket_id}.png"
    output_path = os.path.join(QR_DIR, filename)
    img.save(output_path)
    
    return output_path


def render_ticket_image(
    ticket_design_path: str,
    attendee_name: str,
    ticket_type: str,
    ticket_id: str,
    qr_code_path: str,
    event_name: str,
    event_date: str,
    event_time: str,
    venue: str
) -> str:
    """Render final ticket image"""
    
    # Load or create ticket background
    if ticket_design_path and os.path.exists(ticket_design_path):
        ticket = Image.open(ticket_design_path).convert('RGB')
        ticket = ticket.resize((800, 400), Image.Resampling.LANCZOS)
    else:
        # Create default gradient background
        ticket = Image.new('RGB', (800, 400), color='white')
        draw_temp = ImageDraw.Draw(ticket)
        for i in range(400):
            color_val = int(200 - (i * 0.3))
            draw_temp.rectangle([0, i, 800, i+1], fill=(color_val, color_val + 20, color_val + 50))
        draw_temp.rectangle([10, 10, 790, 390], outline=(255, 255, 255), width=3)
    
    # Load fonts
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font_title = ImageFont.load_default()
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Add QR code
    if os.path.exists(qr_code_path):
        qr_img = Image.open(qr_code_path)
        qr_img = qr_img.resize((120, 120), Image.Resampling.LANCZOS)
        ticket.paste(qr_img, (650, 20))
    
    # Add semi-transparent overlay for text readability
    overlay = Image.new('RGBA', ticket.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([20, 20, 600, 380], fill=(0, 0, 0, 150))
    
    ticket = ticket.convert('RGBA')
    ticket = Image.alpha_composite(ticket, overlay)
    draw = ImageDraw.Draw(ticket)
    
    text_color = (255, 255, 255)
    
    # Add text
    draw.text((40, 40), event_name[:40], fill=text_color, font=font_title)
    draw.text((40, 90), f"Attendee: {attendee_name}", fill=text_color, font=font_large)
    draw.text((40, 130), f"Type: {ticket_type}", fill=text_color, font=font_medium)
    draw.text((40, 170), f"Date: {event_date}", fill=text_color, font=font_medium)
    draw.text((40, 200), f"Time: {event_time}", fill=text_color, font=font_medium)
    draw.text((40, 230), f"Venue: {venue}", fill=text_color, font=font_medium)
    draw.text((40, 350), f"Ticket ID: {ticket_id}", fill=text_color, font=font_small)
    
    # Save ticket
    ticket = ticket.convert('RGB')
    filename = f"ticket_{ticket_id}.jpg"
    output_path = os.path.join(TICKETS_DIR, filename)
    ticket.save(output_path, quality=95)
    
    return output_path