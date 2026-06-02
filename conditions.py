import time
from datetime import datetime
from selenium.webdriver.common.by import By

from mailer import send_report_email


def check_sla_condition(driver, title, config):

    retry_count = 0

    while retry_count < 2:

        print(f"\n🔄 SLA Check Attempt {retry_count + 1}")

        time.sleep(5)

        # READ TABLE CELLS
        cells = driver.find_elements(
            By.XPATH,
            "//div[contains(@class,'ant-table-cell')]"
        )

        sla_text = cells[8].text

        print("📊 SLA TEXT:", sla_text)

        sla_value = float(
            sla_text.replace("%", "").strip()
        )

        print("📈 SLA VALUE:", sla_value)

        # -----------------------------
        # SLA ACHIEVED
        # -----------------------------

        if sla_value >= 95:

            print("✅ SLA ACHIEVED")

            section = title.find_element(
                By.XPATH,
                "./ancestor::div[7]"
            )

            section.screenshot("final_table.png")

            print("📸 Screenshot Taken")

       send_report_email(
                config,
                "final_table.png"
            )

            print("📧 Success Email Sent")

            return True

        # -----------------------------
        # SLA FAILED
        # -----------------------------

        else:

            print("❌ SLA BELOW 95%")

            retry_count += 1

            current_hour = datetime.now().hour

            # FINAL ESCALATION
            if retry_count == 2 and current_hour >= 16:

                print("🚨 SLA NOT ACHIEVED")

                section = title.find_element(
                    By.XPATH,
                    "./ancestor::div[7]"
                )

                section.screenshot("final_table.png")

                send_report_email(
                    config,
                    "final_table.png"
                )

                print("📧 Escalation Email Sent")

                return False

            print("⏳ Waiting 2 Hours")

            time.sleep(7200)