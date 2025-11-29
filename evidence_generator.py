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
                    await page.wait_for_timeout(1000)
                    success = True
                except Exception:
                    success = False
            
            if success:
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

