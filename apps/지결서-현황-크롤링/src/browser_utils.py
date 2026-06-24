from playwright.sync_api import Page, TimeoutError
from pathlib import Path
from config import OUTPUT_DIR, logger

def save_error_dom(page: Page, context_msg: str):
    """Saves the current DOM to output/error_dom.html for debugging."""
    try:
        content = page.content()
        err_file = OUTPUT_DIR / "error_dom.html"
        with open(err_file, "w", encoding="utf-8") as f:
            f.write(content)
        logger.error(f"{context_msg}. Saved current DOM to: {err_file}")
        logger.error("에러가 발생했습니다. output/error_dom.html에서 해당 버튼 주변 코드를 확인해 주세요.")
    except Exception as e:
         logger.error(f"Failed to save error DOM: {e}")

def proactive_click(page: Page, locators: list[str], timeout: int = 5000):
    """
    Attempts to click using a list of possible locators to handle DOM uncertainty.
    """
    for loc in locators:
        try:
            # Wait for locator and click if available
            element = page.locator(loc).first
            element.wait_for(state="visible", timeout=timeout)
            element.click(timeout=timeout)
            logger.info(f"Successfully clicked using locator: {loc}")
            return True
        except TimeoutError:
            continue
        except Exception as e:
            logger.warning(f"Unexpected error with locator {loc}: {e}")
            continue
            
    # If all fail, save DOM
    save_error_dom(page, "Proactive click failed for all provided locators")
    raise TimeoutError("All locators failed for proactive click.")

def proactive_text_content(page: Page, locators: list[str], timeout: int = 5000) -> str:
    """
    Attempts to extract text using a list of possible locators.
    """
    for loc in locators:
        try:
            element = page.locator(loc).first
            element.wait_for(state="visible", timeout=timeout)
            return element.inner_text(timeout=timeout).strip()
        except TimeoutError:
            continue
        except Exception as e:
            continue
            
    # If all fail, log it and return empty
    logger.warning("(일부 문서 양식 차이로 특정 정보를 찾지 못했지만, 유연하게 다음 항목으로 넘어갑니다)")
    return ""
