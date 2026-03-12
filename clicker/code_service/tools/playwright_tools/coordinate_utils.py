from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from config import logger

if TYPE_CHECKING:
    from playwright.async_api import Page


ELEMENT_INFO_SCRIPT = """
(args) => {
    const x = args[0];
    const y = args[1];
    const element = document.elementFromPoint(x, y);
    if (!element) return null;

    const rect = element.getBoundingClientRect();

    function getEnrichedXPath(el) {
        const path = [];
        let current = el;
        while (current && current !== document.documentElement) {
            let selector = current.tagName.toLowerCase();

            if (current.id) {
                selector += '#' + current.id;
            }
            if (current.className && typeof current.className === 'string') {
                const classes = current.className.split(' ').filter(c => c).join('.');
                if (classes) selector += '.' + classes;
            }

            const ariaAttrs = [];
            if (current.hasAttribute('role')) {
                ariaAttrs.push(`[role="${current.getAttribute('role')}"]`);
            }
            if (current.hasAttribute('aria-label')) {
                ariaAttrs.push(`[aria-label="${current.getAttribute('aria-label')}"]`);
            }
            if (current.hasAttribute('data-testid')) {
                ariaAttrs.push(`[data-testid="${current.getAttribute('data-testid')}"]`);
            }
            if (current.hasAttribute('type')) {
                ariaAttrs.push(`[type="${current.getAttribute('type')}"]`);
            }
            if (current.hasAttribute('name')) {
                ariaAttrs.push(`[name="${current.getAttribute('name')}"]`);
            }
            if (current.hasAttribute('placeholder')) {
                ariaAttrs.push(`[placeholder="${current.getAttribute('placeholder')}"]`);
            }

            selector += ariaAttrs.join('');
            path.unshift(selector);
            current = current.parentElement;
        }
        return path;
    }

    return {
        enrichedXPath: getEnrichedXPath(element),
        tagName: element.tagName,
        className: element.className,
        id: element.id,
        textContent: element.textContent?.substring(0, 100) || '',
        x: Math.round(rect.left + rect.width / 2),
        y: Math.round(rect.top + rect.height / 2),
        width: Math.round(rect.width),
        height: Math.round(rect.height)
    };
}
"""


async def get_element_at_coordinates(page: Page, x: int, y: int) -> Optional[dict]:
    logger.info(f"Getting element at coordinates: ({x}, {y})")
    element = await page.evaluate(ELEMENT_INFO_SCRIPT, [x, y])
    return element


def format_xpath_result(element: dict) -> str:
    if not element:
        return "Element not found"
    
    xpath = " > ".join(element['enrichedXPath']) if element.get('enrichedXPath') else element.get('tagName', 'unknown').lower()
    return f"XPath: {xpath}"
