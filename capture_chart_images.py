import asyncio
import os
import base64
import io
from PIL import Image
from playwright.async_api import async_playwright
from logger_setup import setup_logger

logger = setup_logger(__name__)

tradingview_url = [
    ("https://en.tradingview.com/chart/GR1CpUCR/", "1. Daily Trend and Momentum Analysis (MACD, RSI, Trendlines)"),
    ("https://en.tradingview.com/chart/epZugjza/", "2. Daily Moving Averages and Volume Profile Analysis"),
    ("https://en.tradingview.com/chart/vOnmoT3y/", "3. 4-Hour Trend and Momentum Analysis (MACD, RSI, Trendlines)"),
]


def get_chart_images():
    return tradingview_url


async def navigate_and_capture(page, url):
    try:
        logger.info(f"Navigating to {url}")
        await page.goto(url, timeout=600000)
        logger.info("Waiting 120 seconds for elements to load...")
        await asyncio.sleep(180)  # Wait for all elements to load
        chart_container = await page.query_selector(".chart-container")
        return await chart_container.screenshot(type='png')
    except Exception as e:
        logger.error(f"Error during navigation or interaction for {url}: {e}")
        return None


async def process_image(png_bytes, file_name):
    if png_bytes:
        try:
            image = Image.open(io.BytesIO(png_bytes))
            image_path = os.path.join("captured_images", f"{file_name}.png")
            image.save(image_path, format="PNG")
            logger.info(f"Image saved as {file_name}.png")

            image_data = base64.b64encode(png_bytes).decode("utf-8")
            return image_data
        except Exception as e:
            logger.error(f"Error processing image: {e}")
    return None


async def capture_screenshot_with_retry(url, file_name, context, max_retries=4):
    for attempt in range(max_retries):
        try:
            page = await context.new_page()
            png_bytes = await navigate_and_capture(page, url)
            image_data = await process_image(png_bytes, file_name)
            await page.close()
            if image_data:
                return image_data
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} attempts failed for {url}")
                return None
            await asyncio.sleep(3)  # Wait before retrying
    return None


async def capture_tradingview_charts(url_list):
    os.makedirs("captured_images", exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-extensions',
            '--mute-audio',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
        ])
        context = await browser.new_context(viewport={"width": 1420, "height": 800})

        semaphore = asyncio.Semaphore(3)

        async def process_url(url, file_name):
            async with semaphore:
                image_data = await capture_screenshot_with_retry(url, file_name, context)
                return {"file_name": file_name, "image_data": image_data}

        tasks = [process_url(url, file_name) for url, file_name in url_list]
        results = await asyncio.gather(*tasks)

        await browser.close()
        return results  # This is now a list of dictionaries


def main():
    results = asyncio.run(capture_tradingview_charts(tradingview_url))
    logger.info("Completed all captures.")
    for result in results:
        file_name = result["file_name"]
        image_data = result["image_data"]
        if image_data:
            logger.info(f"Result: {file_name} - Image Data Length: {len(image_data)}")
        else:
            logger.warning(f"Failed to capture image for {file_name} after all retries")


if __name__ == '__main__':
    main()
