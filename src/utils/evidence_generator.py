"""
Evidence generation using Playwright for screenshot capture.
"""
import os
import asyncio
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page


class EvidenceGenerator:
    """Generator for domain lookup evidence screenshots."""
    
    def __init__(self, evidence_base_path: str = "./evidence"):
        """Initialize evidence generator.
        
        Args:
            evidence_base_path: Base directory for storing evidence files
        """
        self.evidence_base_path = Path(evidence_base_path)
        self.evidence_base_path.mkdir(exist_ok=True)
        self.browser: Optional[Browser] = None
    
    async def initialize(self):
        """Initialize Playwright browser."""
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
    
    async def close(self):
        """Close Playwright browser."""
        if self.browser:
            await self.browser.close()
            await self.playwright.stop()
            self.browser = None
    
    def get_evidence_path(self, run_id: str, domain: str) -> Path:
        """Get the file path for evidence screenshot.
        
        Args:
            run_id: Unique run identifier
            domain: Domain name
            
        Returns:
            Path object for the evidence file
        """
        run_dir = self.evidence_base_path / run_id
        run_dir.mkdir(exist_ok=True)
        return run_dir / f"{domain}.png"
    
    def get_evidence_url(self, run_id: str, domain: str) -> str:
        """Get the URL path for evidence screenshot.
        
        Args:
            run_id: Unique run identifier
            domain: Domain name
            
        Returns:
            URL path string
        """
        return f"/api/evidence/{run_id}/{domain}.png"
    
    async def _handle_cookie_consent(self, page: Page):
        """Handle cookie consent banners by clicking accept/consent buttons.
        
        Args:
            page: Playwright page object
        """
        try:
            # Common cookie consent button selectors
            consent_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accept all")',
                'button:has-text("Accepteer")',
                'button:has-text("Accepteren")',
                'button:has-text("Akkoord")',
                'button:has-text("Agree")',
                'button:has-text("I agree")',
                'button:has-text("Consent")',
                'button:has-text("OK")',
                'a:has-text("Accept")',
                'a:has-text("Accepteer")',
                '[id*="accept"]',
                '[class*="accept"]',
                '[id*="consent"]',
                '[class*="consent"]',
            ]
            
            # Try each selector with a short timeout
            for selector in consent_selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=2000)
                    if button:
                        await button.click()
                        print(f"✓ Clicked cookie consent button: {selector}")
                        await page.wait_for_timeout(1000)  # Wait for animation
                        break
                except Exception:
                    continue
        except Exception as e:
            # Cookie consent handling is optional, so don't fail
            pass
    
    async def _add_source_watermark(self, page: Page, source_url: str):
        """Add source URL watermark to the page.
        
        Args:
            page: Playwright page object
            source_url: Source URL to display
        """
        try:
            # Inject a watermark div at the top of the page
            await page.evaluate(f"""
                () => {{
                    const watermark = document.createElement('div');
                    watermark.style.cssText = `
                        position: fixed;
                        top: 0;
                        left: 0;
                        right: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 12px 20px;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        font-size: 14px;
                        font-weight: 500;
                        z-index: 999999;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    `;
                    watermark.innerHTML = `
                        <span style="font-weight: 600;">📸 Evidence Source:</span>
                        <span style="opacity: 0.95;">{source_url}</span>
                        <span style="margin-left: auto; font-size: 12px; opacity: 0.8;">
                            {new Date().toLocaleString()}
                        </span>
                    `;
                    document.body.insertBefore(watermark, document.body.firstChild);
                    
                    // Adjust body padding to prevent content from being hidden
                    document.body.style.paddingTop = '50px';
                }}
            """)
            await page.wait_for_timeout(500)  # Wait for watermark to render
        except Exception as e:
            print(f"Failed to add watermark: {e}")
            # Watermark is optional, so don't fail
    
    async def _capture_rdap_json(self, page: Page, url: str) -> bool:
        """Capture screenshot of RDAP JSON page.
        
        Args:
            page: Playwright page object
            url: RDAP endpoint URL
            
        Returns:
            True if successful
        """
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await self._handle_cookie_consent(page)
            await page.wait_for_timeout(1000)  # Give it a moment to render
            return True
        except Exception as e:
            print(f"Failed to load RDAP page {url}: {e}")
            return False
    
    async def _capture_sidn_whois(self, page: Page, domain: str) -> bool:
        """Capture screenshot of SIDN WHOIS search.
        
        Args:
            page: Playwright page object
            domain: Domain name to search
            
        Returns:
            True if successful
        """
        try:
            # Go to SIDN WHOIS page
            await page.goto("https://www.sidn.nl/en/whois", wait_until="networkidle", timeout=30000)
            
            # Handle cookie consent
            await self._handle_cookie_consent(page)
            
            # Find search input and enter domain
            search_input = await page.query_selector('input[type="text"]')
            if search_input:
                await search_input.fill(domain)
                
                # Submit search
                submit_button = await page.query_selector('button[type="submit"], input[type="submit"]')
                if submit_button:
                    await submit_button.click()
                else:
                    # Try pressing Enter
                    await search_input.press("Enter")
                
                # Wait for results
                await page.wait_for_timeout(3000)
                return True
            
            return False
        except Exception as e:
            print(f"Failed to capture SIDN WHOIS for {domain}: {e}")
            return False
    
    async def generate_evidence(
        self,
        run_id: str,
        domain: str,
        source_url: Optional[str],
        tld: str
    ) -> dict:
        """Generate evidence screenshot for a domain lookup.
        
        Args:
            run_id: Unique run identifier
            domain: Domain name
            source_url: Source URL (RDAP endpoint or API)
            tld: Top-level domain
            
        Returns:
            Evidence info dict with status, format, url, source_url
        """
        if not self.browser:
            await self.initialize()
        
        evidence_path = self.get_evidence_path(run_id, domain)
        evidence_url = self.get_evidence_url(run_id, domain)
        
        try:
            page = await self.browser.new_page()
            page.set_default_timeout(30000)
            
            success = False
            
            # Special handling for .nl domains (SIDN)
            if tld == '.nl':
                success = await self._capture_sidn_whois(page, domain)
                if success:
                    source_url = "https://www.sidn.nl/en/whois"
            # For other domains with RDAP URLs
            elif source_url and ('rdap' in source_url.lower() or 'json' in source_url.lower()):
                success = await self._capture_rdap_json(page, source_url)
            # Fallback: try source URL directly
            elif source_url:
                try:
                    await page.goto(source_url, wait_until="networkidle", timeout=30000)
                    await self._handle_cookie_consent(page)
                    await page.wait_for_timeout(1000)
                    success = True
                except Exception:
                    success = False
            
            if success:
                # Add source URL watermark to page
                await self._add_source_watermark(page, source_url or "Unknown source")
                
                # Take screenshot
                await page.screenshot(path=str(evidence_path), full_page=True)
                await page.close()
                
                return {
                    'status': 'READY',
                    'format': 'png',
                    'url': evidence_url,
                    'source_url': source_url
                }
            else:
                await page.close()
                return {
                    'status': 'FAILED',
                    'format': 'png',
                    'url': None,
                    'source_url': source_url
                }
        
        except Exception as e:
            print(f"Evidence generation failed for {domain}: {e}")
            return {
                'status': 'FAILED',
                'format': 'png',
                'url': None,
                'source_url': source_url
            }
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

