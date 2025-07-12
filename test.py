from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import requests
import json
import os
from concurrent.futures import ThreadPoolExecutor

# Logging config
logging.basicConfig(level=logging.INFO)

# Constants
BROWSERSTACK_USERNAME = 'shashanksingh_DcRibx'
BROWSERSTACK_ACCESS_KEY = 'jkxz9pvHsD3eD64CptFn'
TRANSLATION_API_KEY = 'AIzaSyBRMFXPRFbd57hSiqsQhVAmnWiKnJZgqKA'
TRANSLATION_URL = 'https://translation.googleapis.com/language/translate/v2'
DOWNLOAD_FOLDER = "/Users/shashank/Desktop/Selenium_BrowserStack"


def print_output(message, data=None):
    print(f"\n=== {message} ===")
    if isinstance(data, list):
        for idx, item in enumerate(data, 1):
            print(f"{idx}. {item}")
    elif isinstance(data, dict):
        for key, value in data.items():
            print(f"{key}: {value}")
    elif data:
        print(data)


def get_browserstack_driver(browser_name, os_version, browser_version):
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions

    browser = browser_name.lower()
    if browser == "chrome":
        options = ChromeOptions()
    elif browser == "firefox":
        options = FirefoxOptions()
    elif browser == "edge":
        options = EdgeOptions()
    else:
        options = webdriver.ChromeOptions()

    # Set capabilities
    options.set_capability("browserName", browser_name)
    options.set_capability("browserVersion", browser_version)
    options.set_capability("os", "OS X" if browser_name == "Safari" else "Windows")
    options.set_capability("osVersion", os_version)
    options.set_capability("name", f"Test on {browser_name} {browser_version} {os_version}")
    options.set_capability("build", "BrowserStack Scraper Build")
    options.set_capability("browserstack.local", "false")
    options.set_capability("browserstack.selenium_version", "4.0.0")

    url = f"https://{BROWSERSTACK_USERNAME}:{BROWSERSTACK_ACCESS_KEY}@hub-cloud.browserstack.com/wd/hub"
    driver = webdriver.Remote(command_executor=url, options=options)
    return driver


def translate_titles(titles):
    translations = []
    for title in titles:
        payload = {"q": title, "source": "es", "target": "en", "key": TRANSLATION_API_KEY}
        response = requests.post(TRANSLATION_URL, data=payload)
        try:
            response_data = response.json()
            translated_text = response_data["data"]["translations"][0]["translatedText"]
            translations.append(translated_text)
        except Exception as e:
            logging.error(f"Translation error: {e}")
            translations.append(f"Failed: {title}")
    return translations


def scrape_articles(driver):
    driver.get("https://elpais.com")
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except:
        logging.error("Page did not load.")
        return []

    try:
        accept_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Aceptar"]'))
        )
        accept_button.click()
    except:
        logging.warning("No cookie popup or failed to click it.")

    try:
        WebDriverWait(driver, 10).until_not(
            EC.presence_of_element_located((By.CLASS_NAME, "blockNavigation"))
        )
    except:
        logging.warning("Overlay still present after timeout.")

    try:
        opinion_link = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/opinion/']"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", opinion_link)
        driver.execute_script("arguments[0].click();", opinion_link)
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article"))
        )
    except Exception as e:
        logging.error(f"Failed to click 'Opinión' link: {e}")
        return []

    articles = driver.find_elements(By.CSS_SELECTOR, "article")[:5]
    results = []
    for article in articles:
        try:
            title = article.find_element(By.CSS_SELECTOR, "h2").text
        except:
            title = "No title found"

        try:
            content = article.find_element(By.CSS_SELECTOR, "p").text
        except:
            content = "No content found"

        try:
            img_element = WebDriverWait(article, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "img"))
            )
            img_url = img_element.get_attribute("src")
        except:
            img_url = None

        results.append({"title": title, "content": content, "img_url": img_url})
    return results


def analyze_headers(headers):
    word_count = {}
    for header in headers:
        for word in header.split():
            word_count[word] = word_count.get(word, 0) + 1
    return {word: count for word, count in word_count.items() if count > 2}


def main(browser_name, os_version, browser_version):
    logging.info(f"Running test: {browser_name} on {os_version}")
    driver = None
    try:
        driver = get_browserstack_driver(browser_name, os_version, browser_version)
        articles = scrape_articles(driver)
        titles = [a["title"] for a in articles]
        translated = translate_titles(titles)
        repeated = analyze_headers(translated)

        print_output("Original Titles", titles)
        print_output("Translated Titles", translated)
        print_output("Repeated Words", repeated)

        os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
        for idx, article in enumerate(articles):
            img_url = article["img_url"]
            if img_url:
                try:
                    img_data = requests.get(img_url).content
                    with open(os.path.join(DOWNLOAD_FOLDER, f"article_{idx+1}.jpg"), "wb") as f:
                        f.write(img_data)
                except Exception as e:
                    logging.warning(f"Failed to download image: {e}")
    except Exception as e:
        logging.error(f"Error in test: {e}")
    finally:
        if driver:
            driver.quit()


def execute_in_parallel():
    browsers = [
        {"browser_name": "Chrome", "os_version": "10", "browser_version": "latest"},
        {"browser_name": "Firefox", "os_version": "10", "browser_version": "latest"},
        {"browser_name": "Edge", "os_version": "10", "browser_version": "latest"},
        {"browser_name": "Safari", "os_version": "Monterey", "browser_version": "latest"},
        {"browser_name": "Chrome", "os_version": "11", "browser_version": "latest-1"},
    ]
    with ThreadPoolExecutor(max_workers=5) as executor:
        for browser in browsers:
            executor.submit(main, **browser)


if __name__ == "__main__":
    execute_in_parallel()
