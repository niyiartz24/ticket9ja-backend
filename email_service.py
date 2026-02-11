import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import Optional

# Email configuration from environment variables
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER)
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
    """
    Send ticket email with attachment.
    Returns True if successful, False otherwise.
    """
    
    # Check if SMTP is configured
    if not SMTP_USER or not SMTP_PASSWORD:
        print("⚠️  WARNING: SMTP not configured. Email will not be sent.")
        print("   Configure SMTP_USER and SMTP_PASSWORD environment variables.")
        return False
    
    try:
        print(f"📧 Sending ticket email to {to_email}...")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = f"🎫 Your Ticket for {event_name}"
        
        # Email body
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">🎫 Ticket9ja</h1>
                <p style="color: white; margin: 10px 0 0 0;">Your Event Ticket</p>
            </div>
            
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">Hello {attendee_name}!</h2>
                
                <p style="color: #666; font-size: 16px;">
                    Your ticket for <strong>{event_name}</strong> has been confirmed! 🎉
                </p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea;">
                    <h3 style="color: #667eea; margin-top: 0;">Event Details</h3>
                    <p style="margin: 10px 0;"><strong>📅 Date:</strong> {event_date}</p>
                    <p style="margin: 10px 0;"><strong>⏰ Time:</strong> {event_time}</p>
                    <p style="margin: 10px 0;"><strong>📍 Venue:</strong> {venue}</p>
                    <p style="margin: 10px 0;"><strong>🏙️ City:</strong> {city}</p>
                    <p style="margin: 10px 0;"><strong>🎫 Ticket Type:</strong> {ticket_type}</p>
                    <p style="margin: 10px 0;"><strong>🆔 Ticket ID:</strong> <code style="background: #f0f0f0; padding: 4px 8px; border-radius: 4px;">{ticket_id}</code></p>
                </div>
                
                <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
                    <p style="margin: 0; color: #856404;">
                        <strong>⚠️ Important:</strong> Please bring this ticket (digital or printed) to the event. 
                        Your QR code will be scanned at the entrance.
                    </p>
                </div>
                
                <p style="color: #999; font-size: 14px; margin-top: 30px;">
                    Need help? Contact us at support@ticket9ja.com
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Attach ticket image if it exists
        if ticket_image_path and os.path.exists(ticket_image_path):
            try:
                with open(ticket_image_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                
                filename = f"ticket_{ticket_id}.png"
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {filename}",
                )
                
                msg.attach(part)
                print(f"   ✓ Ticket image attached: {filename}")
            except Exception as e:
                print(f"   ⚠️  Could not attach ticket image: {e}")
        else:
            print(f"   ⚠️  Ticket image not found: {ticket_image_path}")
        
        # Send email with timeout
        print(f"   → Connecting to {SMTP_HOST}:{SMTP_PORT}...")
        
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        server.set_debuglevel(0)  # Set to 1 for detailed debugging
        server.starttls()
        
        print(f"   → Logging in as {SMTP_USER}...")
        server.login(SMTP_USER, SMTP_PASSWORD)
        
        print(f"   → Sending email...")
        server.send_message(msg)
        server.quit()
        
        print(f"   ✅ Email sent successfully to {to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"   ❌ SMTP Authentication failed: {e}")
        print(f"      Check SMTP_USER and SMTP_PASSWORD")
        return False
    except smtplib.SMTPException as e:
        print(f"   ❌ SMTP Error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Failed to send email: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_email_configuration():
    """Test if email is configured correctly"""
    if not SMTP_USER or not SMTP_PASSWORD:
        return False, "SMTP credentials not configured"
    
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.quit()
        return True, "Email configuration is valid"
    except Exception as e:
        return False, f"Email configuration error: {str(e)}"        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
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
