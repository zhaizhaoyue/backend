"""
Debug Playwright scraping - see what we actually get from who.is
调试Playwright爬取 - 查看从who.is实际获取的内容
"""
import asyncio
from playwright.async_api import async_playwright


async def debug_scrape(domain: str):
    """Debug what we get from who.is."""
    
    print(f"🔍 Debugging: {domain}")
    print("=" * 70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser
        page = await browser.new_page()
        
        url = f"https://who.is/whois/{domain}"
        print(f"📡 Visiting: {url}\n")
        
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)
        
        # Get page content
        page_text = await page.inner_text('body')
        
        print("📄 Page Content (first 2000 chars):")
        print("-" * 70)
        print(page_text[:2000])
        print("-" * 70)
        
        # Save full content
        output_file = f"debug_{domain.replace('.', '_')}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(page_text)
        
        print(f"\n💾 Full content saved to: {output_file}")
        print(f"📏 Total length: {len(page_text)} characters")
        
        await browser.close()


async def main():
    """Test with one domain."""
    await debug_scrape("delhaize.be")


if __name__ == "__main__":
    asyncio.run(main())

