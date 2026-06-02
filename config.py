# config.py
class Config:
    # 🌐 URLs
    BASE_URL = "https://reportplus.mizopower.com/"
    REPORTS_URL = "https://reportplus.mizopower.com/reports"
    
    
    # 🔐 Login Credentials (for website, NOT email)
    USER = "anbudesigan.c@cuculus.in"
    PASS = "Cuculus@123"
    
    
    # 📧 Email Configuration (Office 365 SMTP)
    SMTP_SERVER = "smtp.office365.com"
    SMTP_PORT = 587
    SMTP_USE_TLS = True
    
    # ✅ Sender Email
    SENDER = "reportingbot@cuculus.in"
    # ✅ IMPORTANT: App Password (NO SPACES)
    SENDER_PASS = "mjtgsxcqctgmskdq"
    # ✅ Receiver
    RECEIVER = "anbudesigan.c@cuculus.in"
    # ✅ CC (can be multiple if needed)
    CC = [ "sandeep.p@cuculus.in"
          "ambika.sharma@cuculus.in"
    ]
    
    
    # 🖼 Logos
    TOP_LOGO = "logo_top.png"
    BOTTOM_LOGO = "logo_bottom.png"
    
    # ⏱ SLA and escalation settings
    SLA_THRESHOLD = 95.0
    ESCALATION_HOUR = 11
    ESCALATION_MINUTE = 14