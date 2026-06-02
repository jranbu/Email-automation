import mimetypes
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime

def _attach_inline_image(msg, image_path, cid_name):
    if not image_path or not os.path.isfile(image_path):
        return False
    guessed_type = mimetypes.guess_type(image_path)[0]
    maintype, subtype = guessed_type.split('/') if guessed_type else ('image', 'png')
    with open(image_path, 'rb') as img:
        img_data = img.read()
    msg.get_payload()[1].add_related(
        img_data,
        maintype=maintype,
        subtype=subtype,
        cid=f"<{cid_name}>"
    )
    return True

def _attach_file(msg, file_path, content_type=None):
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
            file_name = os.path.basename(file_path)
        if content_type:
            maintype, subtype = content_type.split('/')
        else:
            guessed = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            maintype, subtype = guessed.split('/')
        msg.add_attachment(
            file_data,
            maintype=maintype,
            subtype=subtype,
            filename=file_name
        )
        return True
    except Exception:
        return False

def send_report_email(config, image_path):
    """
    Sends an email with the report screenshot attached.
    """
    msg = EmailMessage()
    msg['Subject'] = f"Daily LP SLA Report for 8hr Profile - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = config.SENDER
    msg['To'] = config.RECEIVER
    msg['Cc'] = ", ".join(config.CC)
    text_content = (
        f"Hello Team,\n\n"
        f"Please find attached the SLA report for the 8-hour profile for Satnam, - {datetime.now().strftime('%B %d, %Y')}.\n\n"
        f"The 8hr LP SLA target has been achieved,\n\n"
        f"This is an automated notification from the Cuculus Reporting system.\n\n"
        f"Best regards,\n"
        f"reportbot@CCI"
    )
    msg.set_content(text_content)
    # ✅ HTML with blurred inline background logo (if provided)
    logo_cid = 'cuculus_logo'
    logo_path = os.path.join(os.path.dirname(__file__), 'Cuculus-Logo (1).png')
    html_content = (
        f"<html><body style='font-family:Times Roman, sans-serif; color:#1a1a1a; line-height:1.5; margin:0; padding:0;'>"
        f"<div style='position:relative; min-height:180px; text-align:center;'>"
        f"<img src=\"cid:{logo_cid}\" alt=\"\" style=\"position:relative; left:0; top:0; width:320px; height:auto; object-fit:contain; transform:none; opacity:1; z-index:0; display:block; margin:0 auto;\"/>"
        f"<div style='position:relative; z-index:1; padding:50px 40px 40px 40px; background-color:rgba(255,255,255,0.95); text-align:left;'>"
        f"<p style='font-size:16px; font-weight:700; margin:0 0 20px 0;'>Hello Team,</p>"
        f"<p style='font-size:16px; font-weight:700; margin:0 0 12px 0;'>Please find attached the SLA report for the 8-hour profile for Satnam, - {datetime.now().strftime('%B %d, %Y')}.</p>"
        f"<p style='font-size:16px; font-weight:700; margin:0 0 12px 0;'>The 8hr LP SLA target has been achieved,</p>"
        f"<p style='font-size:16px; font-weight:700; margin:0 0 12px 0;'>This is an automated notification from the Cuculus Reporting system.</p>"
        f"<p style='font-size:16px; font-weight:700; margin:18px 0 0 0;'>Best regards,<br />reportbot@CCI </p>"
        f"<a href='https://www.cuculus.com/' "
        f"style='color:#1a73e8; text-decoration:none;'>"
        f"https://www.cuculus.com/"
        f"</a>"
        f"</div></div></body></html>"
        f"</div></div></body></html>"
    )
    msg.add_alternative(html_content, subtype='html')
    # Attach inline logo as a related resource for the HTML part (best-effort)
    try:
        if os.path.isfile(logo_path):
            _attach_inline_image(msg, logo_path, logo_cid)
        else:
            print(f"Logo not found at {logo_path}; sending without background logo.")
    except Exception as _:
        print("Failed to attach inline logo; continuing without it.")
    if image_path:
        with open(image_path, "rb") as f:

            file_data = f.read()

        file_name = os.path.basename(image_path)

        msg.add_attachment(
        file_data,
        maintype="image",
        subtype="png",
        filename=file_name
        )

        print(f"Screenshot attached: {file_name}")
    try:
        # ✅ FIXED SMTP BLOCK
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(config.SENDER, config.SENDER_PASS)
            smtp.send_message(msg)
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def send_escalation_email(config, sla_value, image_path=None):
    """Sends an escalation email when SLA falls below threshold."""
    msg = EmailMessage()
    msg['Subject'] = f"Escalation: LP SLA Not Achieved with ({sla_value}%) - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = config.SENDER
    msg['To'] = config.RECEIVER
    msg['Cc'] = ", ".join(config.CC)
    text_content = (
        f"Hello Team,\n\n"
        f"Please find attached the SLA report for the 8-hour profile for Satnam, {datetime.now().strftime('%B %d, %Y')}.\n\n"
        f"The 8hr LP SLA target has not been achieved because there was an issue with the 8hr Load Profile. We hope to resolve this soon.\n\n"
        f"This is an automated notification from the Cuculus Reporting system.\n\n"
        f"Best regards,\n"
        f"reportbot@CCI"
    )
    msg.set_content(text_content)
    # ✅ HTML with blurred inline background logo (if provided)
    logo_cid = 'cuculus_logo'
    logo_path = os.path.join(os.path.dirname(__file__), 'Cuculus-Logo (1).png')
    html_content = (
        f"<html><body style='font-family:Times Roman, sans-serif; color:#1a1a1a; line-height:1.5; margin:0; padding:0;'>"
        f"<div style='position:relative; min-height:180px; text-align:center;'>"
        f"<img src=\"cid:{logo_cid}\" alt=\"\" style=\"position:relative; left:0; top:0; width:320px; height:auto; object-fit:contain; transform:none; opacity:1; z-index:0; display:block; margin:0 auto;\"/>"
        f"<div style='position:relative; z-index:1; padding:50px 40px 40px 40px; background-color:rgba(255,255,255,0.95); text-align:left;'>"
        f"<p style='font-size:16px; font-weight:700; margin:0 0 20px 0;'>Hello Team,</p>"
        f"<p style='font-size:16px; font-weight:700; margin:0 0 12px 0;'>Please find attached the SLA report for the 8-hour profile for Satnam,- {datetime.now().strftime('%B %d, %Y')}.</p>"
        f"<p style='font-size:16px; font-weight:700; margin:0 0 12px 0;'>The 8hr LP SLA target has not been achieved because there was an issue with the 8hr Load Profile. We hope to resolve this soon.</p>"
        f"<p style='font-size:16px; font-weight:700; margin:0 0 12px 0;'>This is an automated notification from the Cuculus Reporting system.</p>"
        f"<p style='font-size:16px; font-weight:700; margin:18px 0 0 0;'>Best regards,<br />reportbot@CCI</p>"
        f"<a href='https://www.cuculus.com/' "
        f"style='color:#1a73e8; text-decoration:none;'>"
        f"https://www.cuculus.com/"
        f"</a>"
        f"</div></div></body></html>"
    )
    msg.add_alternative(html_content, subtype='html')
    # Attach inline logo as a related resource for the HTML part (best-effort)
    try:
        if os.path.isfile(logo_path):
            _attach_inline_image(msg, logo_path, logo_cid)
        else:
            print(f"Logo not found at {logo_path}; sending without background logo.")
    except Exception as _:
        print("Failed to attach inline logo; continuing without it.")
    if image_path:
        with open(image_path, "rb") as f:

            file_data = f.read()

        file_name = os.path.basename(image_path)

        msg.add_attachment(
        file_data,
        maintype="image",
        subtype="png",
        filename=file_name
        )

        print(f"Screenshot attached: {file_name}")
    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(config.SENDER, config.SENDER_PASS)
            smtp.send_message(msg)
        print("✅ Escalation email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send escalation email: {e}") 