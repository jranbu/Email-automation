import time
from datetime import datetime
from config import Config
from scrapper_new import run_report_process
from mailer import send_report_email, send_escalation_email


def wait_until(hour, minute=0):
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now >= target:
        print("Escalation hour has already passed, sending escalation email immediately.")
        return

    seconds_left = (target - now).total_seconds()
    print(f"Waiting {int(seconds_left)} seconds until escalation time at {target.strftime('%H:%M')}...")
    while datetime.now() < target:
        time.sleep(min(60, (target - datetime.now()).total_seconds()))

def job():
    print(f"[{time.strftime('%H:%M:%S')}] Starting the automated report process...")
    
    max_retries = 3
    retry_delay = 10  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n{'='*60}")
            print(f"Attempt {attempt}/{max_retries}")
            print(f"{'='*60}")
            report_path, sla_value = run_report_process(Config)

            if sla_value is None:
                print("❌ Unable to determine SLA value, aborting email flow.")
                return

            if sla_value >= Config.SLA_THRESHOLD:
                print(f"✅ SLA is acceptable ({sla_value}%), sending report email.")
                print(f"📍 Screenshot saved at: {report_path}")
                send_report_email(Config, report_path)
                return

            print(f"⚠️ SLA below threshold ({sla_value}%), waiting until {Config.ESCALATION_HOUR}:00 to send escalation email.")
            wait_until(
                Config.ESCALATION_HOUR,
                Config.ESCALATION_MINUTE
            )
            send_escalation_email(Config, sla_value, report_path)
            return

        except Exception as e:
            print(f"❌ Attempt {attempt} failed: {e}")
            
            if attempt < max_retries:
                print(f"⏳ Retrying in {retry_delay} seconds... (Attempt {attempt + 1} of {max_retries})")
                time.sleep(retry_delay)
            else:
                print(f"❌ All {max_retries} attempts failed. Automation aborted.")
                raise


if __name__ == "__main__":
    job()