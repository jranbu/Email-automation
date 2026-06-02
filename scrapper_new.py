from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

import time
import traceback
import os
import base64
try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None
    ImageDraw = None
    ImageFont = None


def run_report_process(Config_class):

    def _capture_element_via_cdp(driver, element, path):
        try:
            rect = driver.execute_script(
                "const r = arguments[0].getBoundingClientRect(); return {x: r.left, y: r.top, width: r.width, height: r.height, dpr: window.devicePixelRatio || 1};",
                element,
            )

            if not rect or rect.get('width', 0) == 0 or rect.get('height', 0) == 0:
                raise Exception('Element has zero size')

            dpr = rect.get('dpr', 1)
            clip = {
                'x': rect['x'] * dpr,
                'y': rect['y'] * dpr,
                'width': rect['width'] * dpr,
                'height': rect['height'] * dpr,
                'scale': 1,
            }

            result = driver.execute_cdp_cmd('Page.captureScreenshot', {
                'format': 'png',
                'clip': clip,
                'captureBeyondViewport': True,
            })

            data = result.get('data')
            if not data:
                raise Exception('No screenshot data from CDP')

            with open(path, 'wb') as f:
                f.write(base64.b64decode(data))
            return True
        except Exception as e:
            print(f'CDP element screenshot failed: {e}')
            return False

    def _render_table_image(headers, rows, path):
        try:
            if Image is None:
                print("Pillow not installed. Install with: pip install pillow")
                return False
        except Exception:
            print("Error checking Pillow availability")
            return False

        try:
            print(f"Rendering table image: headers={headers}, rows_count={len(rows)}")
            print(f"Pillow Image object: {Image}, ImageFont: {ImageFont}")
        except Exception:
            pass

        # High-resolution styling
        try:
            title_font_size = 32
            font_size = 22
            title_font = ImageFont.truetype('arial.ttf', title_font_size)
            font = ImageFont.truetype('arial.ttf', font_size)
        except Exception:
            title_font = ImageFont.load_default()
            font = ImageFont.load_default()

        padding_x = 18
        padding_y = 14
        border = 2
        table_margin = 40
        title_margin = 28

        # Measure column widths
        col_count = max(len(headers), max((len(r) for r in rows), default=0))
        try:
            dummy_img = Image.new('RGB', (10, 10))
            measure_draw = ImageDraw.Draw(dummy_img)
        except Exception as e:
            print(f"Failed to create drawing context: {e}")
            return False

        def _measure_text(text, use_title_font=False):
            chosen_font = title_font if use_title_font else font
            try:
                if hasattr(measure_draw, 'textbbox'):
                    left, top, right, bottom = measure_draw.textbbox((0, 0), text, font=chosen_font)
                    return right - left, bottom - top
                if hasattr(chosen_font, 'getsize'):
                    return chosen_font.getsize(text)
                return chosen_font.getmask(text).size
            except Exception as e:
                print(f"Failed to measure text '{text}': {e}")
            return 80, 30

        col_widths = [0] * col_count
        for i, h in enumerate(headers):
            w, _ = _measure_text(h)
            col_widths[i] = max(col_widths[i], w + 2 * padding_x)
        for r in rows:
            for i, cell in enumerate(r):
                w, _ = _measure_text(cell)
                if i < col_count:
                    col_widths[i] = max(col_widths[i], w + 2 * padding_x)

        title_text = 'Daywise Blockload SLA'
        title_width, title_height = _measure_text(title_text, use_title_font=True)
        row_height = _measure_text('Ay')[1] + 2 * padding_y
        table_width = max(sum(col_widths) + (col_count + 1) * border, title_width + 2 * table_margin)
        table_height = (title_height + title_margin +
                        row_height * (1 + max(1, len(rows))) +
                        (len(rows) + 1) * border +
                        table_margin)

        try:
            img = Image.new('RGB', (int(table_width + 2 * table_margin), int(table_height)), 'white')
            draw = ImageDraw.Draw(img)
        except Exception as e:
            print(f"Failed to create image canvas: {e}")
            return False

        image_width = img.width
        content_x = table_margin
        y = table_margin

        # Draw title
        title_x = (image_width - title_width) // 2
        draw.text((title_x, y), title_text, fill='#0b3d91', font=title_font)
        y += title_height + title_margin

        # Draw table outline and header
        highlight_index = None
        for idx, header in enumerate(headers):
            normalized = header.strip().lower().replace(' ', '').replace('\n', '')
            if normalized == 'ls8hrs[%]' or normalized == 'ls8hrs%' or 'ls8' in normalized:
                highlight_index = idx
                break

        table_left = content_x
        table_right = content_x + table_width
        table_bottom = y + row_height * (1 + max(1, len(rows))) + (len(rows) + 1) * border
        draw.rectangle([table_left - 2, y - 2, table_right + 2, table_bottom + 2], outline='#b0b7bf', width=3)

        # Header row
        x = table_left
        for ci in range(col_count):
            w = col_widths[ci] if ci < len(col_widths) else 140
            fill_color = '#e8f0fe' if ci != highlight_index else '#d5f2d5'
            draw.rectangle([x, y, x + w, y + row_height], outline='#c1c7d0', fill=fill_color)
            if ci < len(headers):
                draw.text((x + padding_x, y + padding_y), headers[ci], fill='#1e2d3a', font=font)
            x += w + border

        y += row_height + border

        # Rows
        for row_index, r in enumerate(rows):
            x = table_left
            row_fill = '#fbfcff' if row_index % 2 == 0 else '#f4f7fb'
            for ci in range(col_count):
                w = col_widths[ci] if ci < len(col_widths) else 140
                if ci == highlight_index:
                    # Check the value and color accordingly
                    try:
                        cell_value_str = r[ci].replace('%', '').strip()
                        cell_value = float(cell_value_str)
                        if cell_value < 95:
                            fill_color = '#ffd6d6'  # Light red for values < 95
                        else:
                            fill_color = '#d9f8d9'  # Light green for values >= 95
                    except (ValueError, IndexError):
                        fill_color = '#d9f8d9'  # Default to green if can't parse
                else:
                    fill_color = row_fill
                draw.rectangle([x, y, x + w, y + row_height], outline='#c1c7d0', fill=fill_color)
                if ci < len(r):
                    draw.text((x + padding_x, y + padding_y), r[ci], fill='#1d2430', font=font)
                x += w + border
            y += row_height + border

        try:
            img.save(path)
            print(f"Saved rendered image to {path}")
            return True
        except Exception as e:
            print(f"Failed to save rendered image: {e}")
            return False

    # ---------------- CHROME OPTIONS ----------------

    options = Options()

    # IMPORTANT
    options.page_load_strategy = 'none'

    options.add_argument("--start-maximized")

    options.add_argument("--disable-notifications")

    options.add_argument(
        "--disable-blink-features=AutomationControlled"
    )

    # ---------------- DRIVER ----------------

    driver = webdriver.Chrome(
        service=Service(
            ChromeDriverManager().install()
        ),
        options=options
    )

    wait = WebDriverWait(driver, 30)

    try:

        # ---------------- OPEN WEBSITE ----------------

        print("opening login page..")
        driver.get(Config_class.BASE_URL)
        print("Login page opened")
        
        max_wait = 120
        start_time = time.time()
        while True:
            current_title = driver.title
            print(f"Current page title: '{current_title}'")
            if "Login" in current_title:
                print("Login page detected by title.")
                break
            if time.time() - start_time > max_wait:
                raise Exception(
                    "Login page did not load within 120 seconds"
                )
            time.sleep(2)
            
        print(
            "Current URL:",
            driver.current_url  
        )
        print("Title:", driver.title)

        # ---------------- EMAIL INPUT ----------------


        print("Finding username field...")

        email_input = wait.until(
        EC.presence_of_element_located(
        (By.ID, "username")
    )
)

        print("Username field found")

        email_input.clear()

        email_input.send_keys(
        Config_class.USER
)

        print("Username entered")
        # ---------------- PASSWORD INPUT ----------------
        print("Finding password field...")

        password_input = wait.until(
        EC.presence_of_element_located(
        (
            By.XPATH,
            "//input[@type='password']"
        )
    )
)

        print("Password field found")

        password_input.clear()

        password_input.send_keys(
        Config_class.PASS
)

        print("Password entered")

        # ---------------- LOGIN BUTTON ----------------

        print("Finding login button...")

        login_btn = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(text(),'Login')]"
                )
            )
        )

        print("Login button found")

        login_btn.click()

        print("Login successful")

        # ---------------- WAIT AFTER LOGIN ----------------

        time.sleep(15)

        print(
            "After Login URL:",
            driver.current_url
        )
        # ---------------- NAVIGATE ----------------
        driver.get(Config_class.REPORTS_URL)
        print("Reports page loaded")
        # ---------------- SEARCH ----------------
        search_box = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//input[@placeholder='Search for a report']")
            )
        )
        search_box.clear()
        search_box.send_keys("LP SLA Report")
        print("Report searched")
        time.sleep(3)
        # ?? Click report (IMPORTANT STEP)
        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//*[normalize-space(text())='LP SLA Report']")
            )
        ).click()
        print("LP SLA Report opened successfully")
        # ---------------- REFRESH FIX ----------------
        wait.until(
            EC.element_to_be_clickable((By.ID, "refresh-report-V3y1MeXr2J"))
        ).click()
        print("Refresh clicked")
        today = datetime.today().strftime("%Y-%m-%d")
        start_input = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Start Date']"))
        )
        driver.execute_script("arguments[0].click();", start_input)
        start_day = wait.until(
            EC.presence_of_element_located((By.XPATH, f"//td[@title='{today}']"))
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", start_day
        )
        driver.execute_script("arguments[0].click();", start_day)
        print("Start Date ? Today")
        end_input = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='End Date']"))
        )
        driver.execute_script("arguments[0].click();", end_input)
        end_day = wait.until(
            EC.presence_of_element_located((By.XPATH, f"//td[@title='{today}']"))
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", end_day
        )
        driver.execute_script("arguments[0].click();", end_day)
        print("End Date ? Today")
        save_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(text(),'SAVE')]"))
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", save_btn
        )
        driver.execute_script("arguments[0].click();", save_btn)
        print("Saved Successfully")
        time.sleep(3)
        wait.until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@href,'/dashboards')]"))
        ).click()
        print("Dashboard icon clicked")
        time.sleep(3)
        driver.get("https://reportplus.mizopower.com/dashboards/50")
        print("Dashboard Opened")
        time.sleep(3)
        print("Trying to click refresh icon...")
        icons = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//div[contains(@class,'header-icons')]")
            )
        )
        print(f"Found {len(icons)} header icons")
        refresh_icon = icons[2]
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", refresh_icon
        )
        time.sleep(1)
        driver.execute_script("arguments[0].click();", refresh_icon)
        print("Refresh icon clicked successfully")
        wait.until(
            EC.visibility_of_element_located((By.XPATH, "//div[text()='Refresh Reports']"))
        )
        time.sleep(2)
        daily_refresh = wait.until(
            EC.presence_of_element_located((
                By.XPATH,
                "//div[@class='report-refresh-card']"
                "[.//div[contains(normalize-space(),'Daily SLA SAT Meters')]]"
                "//div[contains(@class,'report-actions')]"
            ))
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", daily_refresh
        )
        time.sleep(1)
        driver.execute_script("arguments[0].click();", daily_refresh)
        print("Daily SLA SAT Meters refreshed")
        today = datetime.today().strftime("%Y-%m-%d")
        start_input = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Start Date']"))
        )
        driver.execute_script("arguments[0].click();", start_input)
        start_day = wait.until(
            EC.presence_of_element_located((By.XPATH, f"//td[@title='{today}']"))
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", start_day
        )
        driver.execute_script("arguments[0].click();", start_day)
        print("Start Date ? Today")
        end_input = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='End Date']"))
        )
        driver.execute_script("arguments[0].click();", end_input)
        end_day = wait.until(
            EC.presence_of_element_located((By.XPATH, f"//td[@title='{today}']"))
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", end_day
        )
        driver.execute_script("arguments[0].click();", end_day)
        print("End Date ? Today")
        save_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(text(),'SAVE')]"))
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", save_btn
        )
        driver.execute_script("arguments[0].click();", save_btn)
        print("Saved Successfully")
        close_btn = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[name()='svg' and @data-icon='close']")
            )
        )
        time.sleep(1)
        close_btn.click()
        print("Popup closed")
        icons = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//div[contains(@class,'header-icons')]")
            )
        )
        print(f"Found {len(icons)} header icons")
        dashboard_icon = icons[3]
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", dashboard_icon
        )
        time.sleep(1)
        driver.execute_script("arguments[0].click();", dashboard_icon)
        print("Dashboard refreshed")
        refresh_now = wait.until(
            EC.presence_of_element_located((By.XPATH, "//div[text()='Refresh Now']"))
        )
        time.sleep(1)
        refresh_now.click()
        print("Refresh Now clicked")
        icons = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//div[contains(@class,'header-icons')]")
            )
        )
        print(f"Found {len(icons)} header icons")
        dashboard_icon = icons[1]
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", dashboard_icon
        )
        time.sleep(1)
        driver.execute_script("arguments[0].click();", dashboard_icon)
        print("Filter option opened")
        date_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(text(),'Date')]"))
        )
        time.sleep(1)
        date_btn.click()
        print("Date clicked")
        date_panel = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class,'date-filter-panel-button')]")
            )
        )
        time.sleep(1)
        date_panel.click()
        print("Date panel opened")
        yesterday_btn = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//span[contains(text(),'Yesterday')]")
            )
        )
        time.sleep(1)
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", yesterday_btn
        )
        time.sleep(1)
        driver.execute_script("arguments[0].click();", yesterday_btn)
        print("Yesterday clicked")
        apply_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, "//div[text()='Apply Filter']"))
        )
        time.sleep(1)
        apply_btn.click()
        print("Filter applied")
        time.sleep(2)
        close_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(@class,'ant-drawer-close')]"))
        )
        time.sleep(1)
        close_btn.click()
        print("Drawer closed")
        table_title = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(text(),'Day wise Block Load SLA')]")
            )
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", table_title
        )
        print("Scrolled to Day wise Block Load SLA table")
        time.sleep(2)
        title = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(text(),'Day wise Block Load SLA')]")
            )
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", title
        )
        time.sleep(2)
        print("Title found")

        # Locate the Day wise Block Load SLA section and read the SLA value
        print("Looking for Day wise Block Load SLA section...")
        section = wait.until(
            EC.presence_of_element_located((
                By.XPATH,
                "//*[contains(text(),'Day wise Block Load SLA')]/ancestor::div[7]"
            ))
        )
        screenshot_root = wait.until(
            EC.presence_of_element_located((
                By.XPATH,
                "//*[contains(text(),'Day wise Block Load SLA')]/ancestor::div[7]"
            ))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", screenshot_root)
        time.sleep(2)
        print("SLA section found")

        table_elements = section.find_elements(By.XPATH, ".//table")
        sla_value = None
        screenshot_name = os.path.join(
            "screenshots",
            f"daywise_block_load_sla_{today}.png"
        )    

        if table_elements:
            table = None
            for candidate in table_elements:
                header_cells = candidate.find_elements(By.XPATH, ".//tr[1]/*[self::th or self::td]")
                if len(header_cells) >= 3:
                    table = candidate
                    break
            if table is None:
                table = table_elements[0]

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", table)
            time.sleep(2)
            print("HTML table found in SLA section")

            rows = table.find_elements(By.XPATH, ".//tbody/tr")
            print(f"Day wise Block Load SLA table row count: {len(rows)}")
            if len(rows) < 3:
                debug_name = f"debug_daywise_block_load_sla_rows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                driver.save_screenshot(debug_name)
                raise Exception(
                    f"Expected at least 3 rows in the Day wise Block Load SLA table, found {len(rows)}. Saved debug screenshot: {debug_name}"
                )

            row_cell = rows[2].find_element(By.XPATH, ".//td[1]")
            sla_text = (row_cell.text or row_cell.get_attribute('textContent') or '').strip()
            print(f"Third row first column value: {sla_text}")
            if not sla_text:
                debug_name = f"debug_daywise_block_load_sla_empty_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                driver.save_screenshot(debug_name)
                raise Exception(
                    f"Found the third row but could not read text. Saved debug screenshot: {debug_name}"
                )

            sla_value = float(sla_text.replace('%', '').strip())

            # Ensure screenshots folder exists
            screenshot_folder = "screenshots"
            os.makedirs(screenshot_folder, exist_ok=True)

            # Build a clean HTML table from extracted header and row text and render
            # it in a temporary data URL so we get a consistent image containing
            # only the column names and values.
            print("Extracting table text to build clean snapshot...")
            # headers: try the THEAD first, fall back to first TR
            header_cells = table.find_elements(By.XPATH, ".//thead//tr[1]/*[self::th or self::td]")
            if not header_cells:
                header_cells = table.find_elements(By.XPATH, ".//tr[1]/*[self::th or self::td]")

            headers = [ (hc.text or hc.get_attribute('textContent') or '').strip() for hc in header_cells ]

            rows_data = []
            for r in table.find_elements(By.XPATH, ".//tbody/tr"):
                cells = r.find_elements(By.XPATH, ".//td")
                rows_data.append([ (c.text or c.get_attribute('textContent') or '').strip() for c in cells ])

            # Try rendering via Pillow image; fallback to CDP or full-page if needed
            screenshot_name = os.path.join(screenshot_folder, f"daywise_block_load_sla_{today}.png")
            try:
                ok = _render_table_image(headers, rows_data, screenshot_name)
                if ok:
                    print(f"Rendered table image saved: {screenshot_name}")
                else:
                    print("Pillow not available or render failed; falling back to CDP/element/full-page screenshots")
                    try:
                        success = _capture_element_via_cdp(driver, table, screenshot_name)
                    except Exception:
                        success = driver.save_screenshot(screenshot_name)
            except Exception as exc:
                print(f"Failed to render table image: {exc}; falling back to CDP/element/full-page screenshots")
                try:
                    success = _capture_element_via_cdp(driver, table, screenshot_name)
                except Exception:
                    success = driver.save_screenshot(screenshot_name)
        else:
            print("No HTML table found; trying dashboard-style SLA widget...")
            percent_elements = section.find_elements(By.XPATH, ".//*[contains(text(), '%')]")
            print(f"Found {len(percent_elements)} percent text elements in SLA section")
            
            if len(percent_elements) == 0:
                print("No percent text found; dumping section structure...")
                section_html = section.get_attribute('outerHTML')
                print(f"Section HTML (first 1000 chars): {section_html[:1000]}")
                
                all_text_elements = section.find_elements(By.XPATH, ".//*")
                print(f"Total child elements in section: {len(all_text_elements)}")
                for idx, elem in enumerate(all_text_elements[:20]):
                    try:
                        text = elem.text.strip()
                        if text:
                            print(f"  Element {idx}: {text[:100]}")
                    except:
                        pass
                
                debug_name = f"debug_daywise_block_load_sla_widget_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                section.screenshot(debug_name)
                raise Exception(
                    f"Expected to find SLA percentage values in the widget, but found 0 percent text elements. Saved debug screenshot: {debug_name}"
                )
            
            if len(percent_elements) < 3:
                debug_name = f"debug_daywise_block_load_sla_widget_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                section.screenshot(debug_name)
                raise Exception(
                    f"Expected at least 3 percent values in the SLA widget, found {len(percent_elements)}. Saved debug screenshot: {debug_name}"
                )

            print("Looking for LS 8 Hrs value specifically...")
            sla_text = None
            import re

            ls_8hrs_labels = section.find_elements(By.XPATH, ".//*[contains(normalize-space(.), 'LS 8 Hrs') or contains(normalize-space(.), 'LS 8 Hrs [%]')]")
            print(f"Found {len(ls_8hrs_labels)} LS 8 Hrs label candidates")

            for idx, label_elem in enumerate(ls_8hrs_labels):
                label_text = label_elem.text.strip()
                print(f"  Label {idx}: {label_text}")
                if not label_text:
                    continue

                # Try the dashboard widget row-final-value directly after the LS 8 Hrs label
                try:
                    value_elem = label_elem.find_element(By.XPATH, "following::div[contains(@class, 'row-final-value')][1]")
                    value_text = (value_elem.text or value_elem.get_attribute('textContent') or '').strip()
                    print(f"    Found row-final-value sibling: {value_text}")
                    if value_text and re.search(r"(\d+(?:\.\d+)?)\s*%", value_text):
                        sla_text = value_text
                        break
                except Exception as exc:
                    print(f"    row-final-value sibling not found: {exc}")

                # Try row-final-value values inside the label's parent block
                try:
                    parent = label_elem.find_element(By.XPATH, "ancestor::div[1]")
                    nearby_values = parent.find_elements(By.XPATH, ".//div[contains(@class, 'row-final-value')]")
                    print(f"    Found {len(nearby_values)} nearby row-final-value candidates")
                    for nidx, near in enumerate(nearby_values):
                        near_text = (near.text or near.get_attribute('textContent') or '').strip()
                        print(f"      Nearby {nidx}: {near_text}")
                        if near_text and re.search(r"(\d+(?:\.\d+)?)\s*%", near_text):
                            sla_text = near_text
                            break
                    if sla_text:
                        break
                except Exception as exc:
                    print(f"    no nearby row-final-value elements: {exc}")

            if not sla_text:
                print("LS 8 Hrs label search did not find a percent value; checking full section for related label/value patterns...")
                candidate_elements = section.find_elements(By.XPATH, ".//*[contains(normalize-space(.), 'LS 8 Hrs') or contains(normalize-space(.), '%')]")
                for idx, elem in enumerate(candidate_elements):
                    elem_text = elem.text.strip()
                    print(f"  Element {idx}: {elem_text}")
                    if 'LS 8 Hrs' in elem_text and '%' in elem_text:
                        sla_text = elem_text
                        break
                    if 'LS 8 Hrs' in elem_text:
                        try:
                            relative = elem.find_element(By.XPATH, "following::div[contains(@class, 'row-final-value')][1]")
                            rel_text = (relative.text or relative.get_attribute('textContent') or '').strip()
                            print(f"    Found relative row-final-value: {rel_text}")
                            if re.search(r"(\d+(?:\.\d+)?)\s*%", rel_text):
                                sla_text = rel_text
                                break
                        except Exception:
                            pass

            if not sla_text:
                print("Falling back to any numeric percent value in section...")
                for idx, elem in enumerate(percent_elements):
                    elem_text = elem.text.strip()
                    print(f"  Candidate {idx}: {elem_text}")
                    if re.search(r"(\d+(?:\.\d+)?)\s*%", elem_text):
                        sla_text = elem_text
                        print(f"  -> Using numeric percent candidate: {sla_text}")
                        break

            if not sla_text:
                debug_name = f"debug_daywise_block_load_sla_widget_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                section.screenshot(debug_name)
                raise Exception(
                    f"Unable to locate an SLA percentage for LS 8 Hrs. Saved debug screenshot: {debug_name}"
                )

            print(f"SLA text to parse: {sla_text}")
            match = re.search(r"(\d+(?:\.\d+)?)\s*%", sla_text)
            if not match:
                debug_name = f"debug_daywise_block_load_sla_widget_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                section.screenshot(debug_name)
                raise Exception(
                    f"Unable to parse SLA percentage from text '{sla_text}'. Saved debug screenshot: {debug_name}"
                )

            sla_value = float(match.group(1))
            
            # Attempt to extract headers and row values from the widget text
            try:
                widget_text = section.text or ''
                import re as _re
                # Expected headers for Day wise Block Load SLA
                headers = ['MeasureDate', 'Devices', 'LS 8 Hrs [%]', 'LS 12 Hrs [%]', 'LS 24 Hrs [%]', 'LP Total [%]']

                # Find the first date (dd-mm-yyyy)
                date_m = _re.search(r"\d{2}-\d{2}-\d{4}", widget_text)
                date_val = date_m.group(0) if date_m else ''

                # Find a nearby integer for devices (first large integer after the date)
                devices_val = ''
                if date_m:
                    after = widget_text[date_m.end():date_m.end() + 200]
                    dev_m = _re.search(r"\b\d{3,}\b", after)
                    if dev_m:
                        devices_val = dev_m.group(0)

                # Find percent-like values in the widget (take first three or four)
                percents = _re.findall(r"\d+(?:\.\d+)?\s*%", widget_text)
                # Find other numeric totals (like LP Total) if present without %
                others = _re.findall(r"\b\d+(?:\.\d+)?\b", widget_text)

                # Choose percent values for LS 8/12/24
                p1 = percents[0] if len(percents) > 0 else ''
                p2 = percents[1] if len(percents) > 1 else ''
                p3 = percents[2] if len(percents) > 2 else ''

                # LP Total may be in percents or plain number; try to pick a number after the percent matches
                lp_total = ''
                if percents:
                    # find position of last percent and look after
                    lastp = widget_text.find(percents[-1])
                    after_all = widget_text[lastp + len(percents[-1]):]
                    m = _re.search(r"\d+(?:\.\d+)?", after_all)
                    if m:
                        lp_total = m.group(0)
                if not lp_total and others:
                    # fallback: take last numeric token
                    lp_total = others[-1]

                row_vals = [date_val, devices_val, p1, p2, p3, lp_total]

                # Render using Pillow (if available)
                screenshot_folder = 'screenshots'
                os.makedirs(screenshot_folder, exist_ok=True)
                screenshot_name = os.path.join(screenshot_folder, f"daywise_block_load_sla_{today}.png")
                rendered = False
                try:
                    rendered = _render_table_image(headers, [row_vals], screenshot_name)
                    if rendered:
                        print(f"Rendered widget table image saved: {screenshot_name}")
                except Exception as _:
                    rendered = False

                if not rendered:
                    print("Couldn't render widget image; falling back to section screenshot")
                    success = _capture_element_via_cdp(driver, section, screenshot_name)

            except Exception as _e:
                print(f"Widget extraction/render failed: {_e}; will screenshot section")
                screenshot_folder = 'screenshots'
                os.makedirs(screenshot_folder, exist_ok=True)
                screenshot_name = os.path.join(screenshot_folder, f"daywise_block_load_sla_{today}.png")
                success = _capture_element_via_cdp(driver, section, screenshot_name)

            # STORE CURRENT SCROLL POSITION
            current_scroll = driver.execute_script(
            "return window.pageYOffset;"
            )

            print(f"Current scroll position: {current_scroll}")

            time.sleep(2)

            # FORCE BACK TO SAME POSITION
            driver.execute_script(
            f"window.scrollTo(0, {current_scroll});"
            )

            time.sleep(2)

            # TAKE ELEMENT-LEVEL SCREENSHOT OF THE SECTION (safer than full page)
            # If we've already rendered a clean table image above, skip re-capturing.
            if os.path.exists(screenshot_name) and os.path.getsize(screenshot_name) > 0:
                print(f"Screenshot already created at {screenshot_name}; skipping section capture")
            else:
                print("Capturing section screenshot immediately after SLA read...")

                screenshot_folder = "screenshots"
                os.makedirs(screenshot_folder, exist_ok=True)

                screenshot_name = os.path.join(
                    screenshot_folder,
                    f"daywise_block_load_sla_{datetime.today().strftime('%Y-%m-%d')}.png"
                )

                try:
                    print("Preparing section for element screenshot (expanding width/overflows)...")
                    try:
                        # make headers wrap and reduce font-size in the section
                        sec_width = driver.execute_script(
                            "var el=arguments[0];"
                            "el.style.overflow='visible';"
                            "el.style.width = 'max-content';"
                            "var ths = el.querySelectorAll('th, thead td');"
                            "for(var i=0;i<ths.length;i++){ ths[i].style.whiteSpace='normal'; ths[i].style.fontSize='12px'; ths[i].style.padding='6px 8px'; ths[i].style.lineHeight='1.1'; }"
                            "var tds = el.querySelectorAll('td'); for(var j=0;j<tds.length;j++){ tds[j].style.whiteSpace='normal'; tds[j].style.fontSize='12px'; }"
                            "return el.scrollWidth;",
                            section
                        )
                        print(f"Section scrollWidth: {sec_width}")
                    except Exception:
                        print("Could not adjust section styles before screenshot; continuing anyway")

                    print("Taking section screenshot via CDP...")
                    success = _capture_element_via_cdp(driver, section, screenshot_name)
                    if success:
                        print(f"Section element screenshot saved: {screenshot_name}")
                    else:
                        print("CDP capture failed, falling back to element.screenshot() and then full-page screenshot")
                        try:
                            success2 = section.screenshot(screenshot_name)
                            print(f"Section element screenshot saved via selenium: {screenshot_name} (success={bool(success2)})")
                        except Exception as exc2:
                            print(f"Section element screenshot failed: {exc2}; falling back to full-page screenshot")
                            success2 = driver.save_screenshot(screenshot_name)
                            print(f"Fallback screenshot saved: {screenshot_name} (success={success2})")
                except Exception as exc:
                    print(f"Section element screenshot failed: {exc}; falling back to full-page screenshot")
                    success = driver.save_screenshot(screenshot_name)
                    print(f"Fallback screenshot saved: {screenshot_name} (success={success})")
        if sla_value >= Config_class.SLA_THRESHOLD:
            print(f"SLA at or above threshold ({sla_value}%), normal report will be sent.")
        else:
            print(f"SLA below threshold ({sla_value}%), escalation email will be sent at {Config_class.ESCALATION_HOUR}:00.")
            
        screenshot_name = os.path.abspath(screenshot_name)

        print(f"Absolute screenshot path: {screenshot_name}")    

        return screenshot_name, sla_value
    except Exception as e:
        print("Error inside scrapper:", e)
        print(traceback.format_exc())
        raise
    finally:
        driver.quit()
