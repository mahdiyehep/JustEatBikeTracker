
import os
import re
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright


FORM_URL = "https://www.justeat.it/en/courier/form"

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

FORM_EMAIL = os.getenv("FORM_EMAIL")
FORM_FIRST_NAME = os.getenv("FORM_FIRST_NAME")
FORM_LAST_NAME = os.getenv("FORM_LAST_NAME")
FORM_PHONE = os.getenv("FORM_PHONE")


BIKE_WORDS = [
    "driver bike",
    "bike",
    "bicycle",
    "e-bike",
    "ebike",
    "bicicletta",
    "cyclist",
]


def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram token or chat id is missing.")
        print(message)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
        },
        timeout=20,
    )

    response.raise_for_status()


def safe_click_text(page, text_pattern, timeout=4000):
    try:
        locator = page.get_by_text(re.compile(text_pattern, re.I)).first
        locator.wait_for(timeout=timeout)
        locator.click()
        return True
    except Exception:
        return False


def safe_fill(page, selectors, value):
    if not value:
        return False

    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() > 0:
                locator.fill(value, timeout=4000)
                return True
        except Exception:
            pass

    return False


def check_bike_option():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            viewport={
                "width": 1365,
                "height": 900,
            }
        )

        page.set_default_timeout(12000)

        try:
            page.goto(FORM_URL, wait_until="networkidle")

            # Accept cookies if a cookie button appears
            safe_click_text(page, r"accept|agree|allow|ok", timeout=3000)

            # Fill email
            safe_fill(
                page,
                [
                    "input[type='email']",
                    "input[name='email']",
                    "input[placeholder*='email' i]",
                ],
                FORM_EMAIL,
            )

            # Fill/select Bologna
            safe_fill(
                page,
                [
                    "input[placeholder*='city' i]",
                    "input[name*='city' i]",
                    "input[type='text']",
                ],
                "Bologna",
            )

            safe_click_text(page, r"bologna", timeout=6000)

            # Go forward from first step
            safe_click_text(page, r"next|continue|start|apply", timeout=8000)

            # Fill personal data
            safe_fill(
                page,
                [
                    "input[name*='first' i]",
                    "input[placeholder*='first' i]",
                ],
                FORM_FIRST_NAME,
            )

            safe_fill(
                page,
                [
                    "input[name*='last' i]",
                    "input[placeholder*='last' i]",
                ],
                FORM_LAST_NAME,
            )

            safe_fill(
                page,
                [
                    "input[type='tel']",
                    "input[name*='phone' i]",
                    "input[placeholder*='phone' i]",
                ],
                FORM_PHONE,
            )

            # Try common answers
            common_answers = [
                r"^no$",
                r"^yes$",
                r"weekday dinner and weekend",
            ]

            for answer in common_answers:
                safe_click_text(page, answer, timeout=2500)

            # Keep moving forward until vehicle step appears
            for _ in range(8):
                html = page.content().lower()

                vehicle_step_seen = (
                    "driver scooter" in html
                    or "driver car" in html
                    or "vehicle_type" in html
                    or "vehicle type" in html
                )

                if vehicle_step_seen:
                    break

                clicked = safe_click_text(page, r"next|continue", timeout=4000)

                if not clicked:
                    break

                page.wait_for_timeout(1500)

            html = page.content().lower()

            found_bike_words = [word for word in BIKE_WORDS if word in html]

            if found_bike_words:
                message = (
                    f"🚲 Just Eat Bologna check\n"
                    f"Time: {now}\n\n"
                    f"Bike option may be ACTIVE.\n"
                    f"Found words: {', '.join(found_bike_words)}\n\n"
                    f"Open the form now:\n{FORM_URL}"
                )
            else:
                message = (
                    f"❌ Just Eat Bologna check\n"
                    f"Time: {now}\n\n"
                    f"Bike option is not visible yet.\n"
                    f"Current options are probably still car/scooter."
                )

            send_telegram(message)

        except Exception as error:
            send_telegram(
                f"⚠️ Just Eat Bologna checker error\n"
                f"Time: {now}\n\n"
                f"{type(error).__name__}: {error}"
            )
            raise

        finally:
            browser.close()


if __name__ == "__main__":
    check_bike_option()
