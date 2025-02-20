import time
import datetime
import json

from loguru import logger as logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from pricestream.client import get_redis_client
import os
from dotenv import load_dotenv

# Define credentials
TRADOVATE_USERNAME = os.getenv("TRADOVATE_USERNAME")
TRADOVATE_PASSWORD = os.getenv("TRADOVATE_PASSWORD")

client = get_redis_client()

from datetime import date, datetime, time, timedelta
from functools import wraps
from time import time as timer


def timeit(func):
    """Calculates the execution time of the function on top of which the decorator is assigned"""

    @wraps(func)
    def wrap_func(*args, **kwargs):
        tic = timer()
        result = func(*args, **kwargs)
        tac = timer()
        logging.info(f"Function {func.__name__!r} executed in {(tac - tic):.4f}s")
        return result

    return wrap_func

def login(page):
    """Attempts to log in to the website with retries."""
    kickoff_url: str = "https://trader.tradovate.com/welcome"
    logging.info(f"Navigating to {kickoff_url}")
    page.goto(kickoff_url)
    page.set_viewport_size({"width": 1280, "height": 800})
    page.wait_for_timeout(10000)
    logging.info(f"Attempting login using demo account: {TRADOVATE_USERNAME}")
    page.fill("#name-input", TRADOVATE_USERNAME)
    page.fill("#password-input", TRADOVATE_PASSWORD)
    page.wait_for_timeout(5000)
    page.click("button.MuiButton-containedPrimary")
    page.wait_for_timeout(10000)

    # Click Launch button if available
    try:
        launch_button_selector = "button.MuiButtonBase-root.MuiButton-root"
        logging.info("Clicking on `Launch` to navigate to price stream")
        page.click(launch_button_selector)
        page.wait_for_timeout(10000)
    except Exception as e:
        logging.warning(f"Launch button not found or error occurred: {e}")


@timeit
def get_prices(page):
    prices = {}
    info_columns = page.query_selector_all(".info-column")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    if not info_columns:
        logging.warning("No info-column elements found.")
        raise

    for column in info_columns:
        # Extract the symbol name if this is the symbol column
        symbol_elem = column.query_selector("div > span")
        symbol = symbol_elem.inner_text().strip() if symbol_elem else None
        label_elem = column.query_selector("small.text-muted")
        price_elem = column.query_selector(".number")

        if not label_elem or not price_elem:
            continue  # Skip this iteration if elements are missing

        label = label_elem.inner_text().strip()
        price = price_elem.inner_text().strip()
        price = column.query_selector(".number").inner_text().strip()
        if label in ["ASK", "BID", "LAST"]:
            prices[label] = price

    return prices, timestamp, symbol


@timeit
@retry(stop=stop_after_attempt(3), wait=wait_fixed(3), retry=retry_if_exception_type(Exception))
def scrape_data(page, writer):
    """Scrapes last price data and writes it to CSV with retries."""
    prices, timestamp, _ = get_prices(page)
    price_data = {
        "TIMESTAMP": timestamp,
        "LAST": prices.get("LAST", None),
        "BID": prices.get("BID", None),
        "ASK": prices.get("ASK", None) 
    }
    logging.info(f"Price data scrapped: {price_data}")
    client.publish("market_data", json.dumps(price_data))
    logging.info(f"Published message to redis: {price_data}")


def connection():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()


def run():
    max_retries = 5  # Set a maximum number of retries
    retries = 0

    while retries < max_retries:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            try:
                login(page)
                delay: float = 0.05
                logging.success(f"Starting streaming every {delay} seconds")
                while True:
                    try:
                        scrape_data(page, writer=None)  # Scrape data with retries
                        # time.sleep(delay)
                    except PlaywrightTimeoutError:
                        logging.error("Timeout while scraping, retrying...")
                        break  # Exit inner loop to restart
                    except Exception as e:
                        logging.error(f"Unexpected error during scraping: {e}")
                        break  # Exit inner loop to restart
                    except KeyboardInterrupt:
                        logging.warning("Scraping manually stopped by user")
                        return  # Exit the run function completely
            except Exception as e:
                logging.error(f"Error in main run loop: {e}")
            finally:
                browser.close()
                logging.info("Browser closed")

        retries += 1  # Increment retry counter
        logging.info(f"Attempt {retries}/{max_retries} failed. Restarting...")

    logging.error("Max retries reached. Exiting...")


if __name__ == "__main__":
    run()