import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Ticket9ja")


def send_ticket_email(
    to_email: str,
    attendee_name: str,
    event_name: str,
    event_date: str,
    event_time: str,
    venue: str,
    city: str,
    ticket_id: str,
    ticket_type: str,
    ticket_image_path: str
) -> bool:
    """Send ticket email with image attachment"""
    
    try:
        msg = MIMEMultipart('related')
        msg['Subject'] = f"Your Ticket for {event_name}"
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg['To'] = to_email
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4A90E2; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .event-details {{ background-color: white; padding: 20px; margin: 20px 0; border-left: 4px solid #4A90E2; }}
                .ticket-info {{ background-color: #e8f4f8; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }}
                img {{ max-width: 100%; height: auto; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎫 {event_name}</h1>
            </div>
            <div class="content">
                <p>Dear {attendee_name},</p>
                <p>Thank you for registering! Your ticket has been confirmed.</p>
                <div class="event-details">
                    <h2>Event Details</h2>
                    <p><strong>📅 Date:</strong> {event_date}</p>
                    <p><strong>⏰ Time:</strong> {event_time}</p>
                    <p><strong>📍 Venue:</strong> {venue}</p>
                    <p><strong>🏙️ City:</strong> {city}</p>
                </div>
                <div class="ticket-info">
                    <h3>Your Ticket Information</h3>
                    <p><strong>Ticket ID:</strong> {ticket_id}</p>
                    <p><strong>Ticket Type:</strong> {ticket_type}</p>
                    <p><strong>Attendee:</strong> {attendee_name}</p>
                </div>
                <h3>Your Ticket:</h3>
                <img src="cid:ticket_image" alt="Your Ticket">
                <p><strong>Important Instructions:</strong></p>
                <ul>
                    <li>Present this ticket at the venue entrance</li>
                    <li>The QR code will be scanned for entry</li>
                    <li>Each ticket can only be used once</li>
                    <li>Keep this email safe</li>
                </ul>
                <p>We look forward to seeing you at the event!</p>
                <div class="footer">
                    <p>Powered by Ticket9ja</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)
        
        html_part = MIMEText(html_body, 'html')
        msg_alternative.attach(html_part)
        
        # Attach ticket image
        if os.path.exists(ticket_image_path):
            with open(ticket_image_path, 'rb') as f:
                img_data = f.read()
                image = MIMEImage(img_data)
                image.add_header('Content-ID', '<ticket_image>')
                image.add_header('Content-Disposition', 'inline', filename='ticket.jpg')
                msg.attach(image)
                
                attachment = MIMEBase('application', 'octet-stream')
                attachment.set_payload(img_data)
                encoders.encode_base64(attachment)
                attachment.add_header('Content-Disposition', f'attachment; filename=Ticket_{ticket_id}.jpg')
                msg.attach(attachment)
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"✓ Email sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"✗ Email error for {to_email}: {str(e)}")
        return False