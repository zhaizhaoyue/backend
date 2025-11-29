"""
Complete Domain Verification Pipeline
完整的域名验证Pipeline

Pipeline stages:
1. RDAP/WHOIS API lookup
2. Playwright scraping for API failures
3. TXT verification for uncertain ownership

All data organized by run_id in data/ folder
所有数据按run_id组织在data/文件夹中
"""
import asyncio
import csv
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
import re

from src.core.rdap_client import RDAPClient
from src.core.txt_verification import TXTVerificationManager
from src.models.domain import DomainResult
from src.utils.csv_exporter import CSVExporter
from config.settings import settings


class CompleteDomainPipeline:
    """Complete pipeline for domain verification."""
    
    def __init__(self, run_id: str):
        """Initialize pipeline with run ID."""
        self.run_id = run_id
        self.run_dir = Path(f"data/run_{run_id}")
        
        # Create directory structure
        self.screenshots_dir = self.run_dir / "screenshots"
        self.intermediate_dir = self.run_dir / "intermediate"
        self.results_dir = self.run_dir / "results"
        
        for dir_path in [self.screenshots_dir, self.intermediate_dir, self.results_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize clients
        self.rdap_client = RDAPClient(api_ninjas_key=settings.api_ninjas_key)
        self.txt_manager = TXTVerificationManager(
            db_path=str(self.run_dir / "txt_verification.db")
        )
        
        # Storage for results at each stage
        self.stage1_results = []  # API results
        self.stage2_results = []  # Playwright results
        self.stage3_results = []  # TXT verification tasks
        
        self.domains = []
    
    def save_metadata(self, stage: str, data: dict):
        """Save metadata for a stage."""
        metadata_file = self.intermediate_dir / f"stage_{stage}_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"   💾 Metadata saved: {metadata_file.name}")
    
    async def stage1_api_lookup(self, domains: List[str]):
        """Stage 1: RDAP/WHOIS API lookup."""
        
        print("\n" + "=" * 80)
        print("📡 STAGE 1: RDAP/WHOIS API Lookup")
        print("=" * 80)
        
        print(f"\n🔍 Processing {len(domains)} domains with API...")
        
        api_success = []
        api_failed = []
        
        for i, domain in enumerate(domains, 1):
            print(f"[{i}/{len(domains)}] {domain:30}", end=" ", flush=True)
            
            try:
                lookup_data, source_url = await self.rdap_client.lookup_domain(domain)
                
                if lookup_data.get('data_source_type') == 'failed':
                    print("❌ API failed")
                    api_failed.append(domain)
                else:
                    print(f"✅ {lookup_data.get('data_source_type', 'unknown')}")
                    
                    # Create domain result
                    domain_result = DomainResult(
                        domain=domain,
                        registrant_organization=lookup_data.get('registrant_org'),
                        registrar=lookup_data.get('registrar'),
                        registry=lookup_data.get('registry'),
                        creation_date=lookup_data.get('creation_date'),
                        expiry_date=lookup_data.get('expiry_date'),
                        nameservers=lookup_data.get('nameservers', []),
                        data_source=lookup_data.get('data_source'),
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    self.stage1_results.append(domain_result)
                    api_success.append(domain)
                
                await asyncio.sleep(2.0)
                
            except Exception as e:
                print(f"❌ Error: {str(e)[:40]}")
                api_failed.append(domain)
        
        # Save Stage 1 results
        stage1_file = self.intermediate_dir / "stage1_api_results.json"
        with open(stage1_file, 'w', encoding='utf-8') as f:
            json.dump(
                [r.model_dump(mode='json') for r in self.stage1_results],
                f, indent=2, default=str
            )
        
        # Save failed domains list for Stage 2
        failed_file = self.intermediate_dir / "stage1_failed_domains.txt"
        with open(failed_file, 'w') as f:
            f.write('\n'.join(api_failed))
        
        # Save metadata
        self.save_metadata('1', {
            'stage': 'RDAP/WHOIS API Lookup',
            'total_domains': len(domains),
            'successful': len(api_success),
            'failed': len(api_failed),
            'success_rate': f"{len(api_success)/len(domains)*100:.1f}%",
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"\n📊 Stage 1 Summary:")
        print(f"   ✅ API Success: {len(api_success)}")
        print(f"   ❌ API Failed: {len(api_failed)}")
        print(f"   📝 Failed domains saved for Stage 2")
        
        return api_failed
    
    async def stage2_playwright_scraping(self, failed_domains: List[str]):
        """Stage 2: Playwright scraping for API failures."""
        
        if not failed_domains:
            print("\n✅ No domains need Playwright scraping (all succeeded in Stage 1)")
            return []
        
        print("\n" + "=" * 80)
        print("🌐 STAGE 2: Playwright Scraping (who.is)")
        print("=" * 80)
        
        print(f"\n🔍 Processing {len(failed_domains)} failed domains with Playwright...")
        
        playwright_success = []
        playwright_failed = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            for i, domain in enumerate(failed_domains, 1):
                print(f"[{i}/{len(failed_domains)}] {domain:30}", end=" ", flush=True)
                
                try:
                    result = await self.scrape_with_playwright(browser, domain, i)
                    
                    if result['success']:
                        print(f"✅ Data found")
                        if result.get('creation_date'):
                            print(f"      Created: {result['creation_date']}")
                        playwright_success.append(domain)
                    else:
                        print(f"⚠️  No data")
                        playwright_failed.append(domain)
                    
                    self.stage2_results.append(result)
                    
                    await asyncio.sleep(3.0)
                    
                except Exception as e:
                    print(f"❌ Error: {str(e)[:40]}")
                    playwright_failed.append(domain)
                    self.stage2_results.append({
                        'domain': domain,
                        'success': False,
                        'error': str(e)
                    })
            
            await browser.close()
        
        # Save Stage 2 results
        stage2_file = self.intermediate_dir / "stage2_playwright_results.json"
        with open(stage2_file, 'w', encoding='utf-8') as f:
            json.dump(self.stage2_results, f, indent=2)
        
        # Save domains that still need TXT verification
        txt_needed_file = self.intermediate_dir / "stage2_need_txt_verification.txt"
        with open(txt_needed_file, 'w') as f:
            f.write('\n'.join(playwright_failed))
        
        # Save metadata
        self.save_metadata('2', {
            'stage': 'Playwright Scraping',
            'total_domains': len(failed_domains),
            'successful': len(playwright_success),
            'failed': len(playwright_failed),
            'success_rate': f"{len(playwright_success)/len(failed_domains)*100:.1f}%" if failed_domains else "N/A",
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"\n📊 Stage 2 Summary:")
        print(f"   ✅ Playwright Success: {len(playwright_success)}")
        print(f"   ❌ Still Failed: {len(playwright_failed)}")
        print(f"   📝 Domains saved for Stage 3 (TXT verification)")
        
        return playwright_failed
    
    async def scrape_with_playwright(self, browser, domain: str, index: int):
        """Scrape single domain with Playwright."""
        
        result = {
            'domain': domain,
            'registrant_org': None,
            'registrar': None,
            'creation_date': None,
            'expiry_date': None,
            'nameservers': [],
            'data_source': 'who.is (Playwright)',
            'success': False
        }
        
        try:
            page = await browser.new_page()
            
            url = f"https://who.is/whois/{domain}"
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            
            # Take screenshot
            screenshot_file = self.screenshots_dir / f"{index:03d}_{domain.replace('.', '_')}.png"
            await page.screenshot(path=str(screenshot_file))
            
            # Get page content
            page_text = await page.inner_text('body')
            
            # Extract creation date
            created_match = re.search(r'Created\s+(\d{1,2}/\d{1,2}/\d{4})', page_text)
            if created_match:
                result['creation_date'] = created_match.group(1)
                result['success'] = True
            
            # Extract registrar
            registrar_match = re.search(r'Registrar:\s*(.+)', page_text, re.IGNORECASE)
            if registrar_match:
                result['registrar'] = registrar_match.group(1).strip()[:100]
                result['success'] = True
            
            # Extract registrant
            registrant_patterns = [
                r'Registrant\s+Organization:\s*(.+)',
                r'Organization:\s*(.+)',
            ]
            
            for pattern in registrant_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    org = match.group(1).strip()
                    if 'privacy' not in org.lower() and 'redacted' not in org.lower():
                        result['registrant_org'] = org[:100]
                        result['success'] = True
                        break
            
            await page.close()
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def stage3_txt_verification(self, uncertain_domains: List[str]):
        """Stage 3: TXT verification for uncertain ownership."""
        
        if not uncertain_domains:
            print("\n✅ No domains need TXT verification")
            return
        
        print("\n" + "=" * 80)
        print("🔐 STAGE 3: TXT Verification Setup")
        print("=" * 80)
        
        print(f"\n📝 Creating TXT verification tasks for {len(uncertain_domains)} domains...")
        
        txt_tasks = []
        
        for i, domain in enumerate(uncertain_domains, 1):
            print(f"[{i}/{len(uncertain_domains)}] {domain:30}", end=" ", flush=True)
            
            try:
                # Create TXT verification task
                task_id, token = self.txt_manager.create_txt_task(
                    domain=domain,
                    case_id=self.run_id,
                    max_attempts=60
                )
                
                txt_tasks.append({
                    'domain': domain,
                    'task_id': task_id,
                    'token': token,
                    'txt_name': '@',
                    'instructions': f"Add TXT record: @ = {token}"
                })
                
                print(f"✅ Task created")
                print(f"      Token: {token}")
                
                self.stage3_results.append({
                    'domain': domain,
                    'task_id': task_id,
                    'token': token
                })
                
            except Exception as e:
                print(f"❌ Error: {str(e)[:40]}")
        
        # Save Stage 3 results
        stage3_file = self.intermediate_dir / "stage3_txt_tasks.json"
        with open(stage3_file, 'w', encoding='utf-8') as f:
            json.dump(txt_tasks, f, indent=2)
        
        # Create instructions file
        instructions_file = self.results_dir / "TXT_VERIFICATION_INSTRUCTIONS.txt"
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("TXT Verification Instructions\n")
            f.write(f"Run ID: {self.run_id}\n")
            f.write("=" * 80 + "\n\n")
            
            for task in txt_tasks:
                f.write(f"Domain: {task['domain']}\n")
                f.write(f"  Add DNS TXT record:\n")
                f.write(f"  Host/Name: {task['txt_name']}\n")
                f.write(f"  Type: TXT\n")
                f.write(f"  Value: {task['token']}\n")
                f.write(f"  Task ID: {task['task_id']}\n")
                f.write("\n" + "-" * 80 + "\n\n")
        
        # Save metadata
        self.save_metadata('3', {
            'stage': 'TXT Verification Setup',
            'total_domains': len(uncertain_domains),
            'tasks_created': len(txt_tasks),
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"\n📊 Stage 3 Summary:")
        print(f"   📝 TXT Tasks Created: {len(txt_tasks)}")
        print(f"   📄 Instructions: {instructions_file.name}")
        print(f"\n💡 Users can now add TXT records to verify domain ownership")
    
    async def run_complete_pipeline(self, input_csv: str):
        """Run the complete 3-stage pipeline."""
        
        print("=" * 80)
        print(f"🚀 Complete Domain Verification Pipeline")
        print(f"   Run ID: {self.run_id}")
        print(f"   Data Directory: {self.run_dir}")
        print("=" * 80)
        
        # Copy input file to run directory
        input_copy = self.run_dir / "input.csv"
        shutil.copy(input_csv, input_copy)
        print(f"\n📥 Input copied to: {input_copy}")
        
        # Read domains from CSV
        domains = []
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and row[1]:
                    domain = row[1].strip()
                    if domain and '.' in domain:
                        domains.append(domain)
        
        self.domains = domains
        print(f"📋 Total domains: {len(domains)}")
        
        start_time = datetime.now()
        
        # Stage 1: API Lookup
        stage1_failed = await self.stage1_api_lookup(domains)
        
        # Stage 2: Playwright Scraping
        stage2_failed = await self.stage2_playwright_scraping(stage1_failed)
        
        # Stage 3: TXT Verification
        await self.stage3_txt_verification(stage2_failed)
        
        # Generate final report
        total_time = (datetime.now() - start_time).total_seconds()
        
        await self.generate_final_report(total_time)
        
        print("\n" + "=" * 80)
        print("✅ PIPELINE COMPLETE!")
        print("=" * 80)
        print(f"\n📁 All results saved in: {self.run_dir}")
        print(f"   📊 Final report: results/FINAL_REPORT.txt")
        print(f"   📸 Screenshots: screenshots/")
        print(f"   📝 Intermediate files: intermediate/")
    
    async def generate_final_report(self, total_time: float):
        """Generate comprehensive final report."""
        
        report_file = self.results_dir / "FINAL_REPORT.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("COMPLETE DOMAIN VERIFICATION PIPELINE - FINAL REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Run ID: {self.run_id}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Total Processing Time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)\n")
            f.write(f"Total Domains: {len(self.domains)}\n\n")
            
            f.write("-" * 80 + "\n")
            f.write("STAGE 1: RDAP/WHOIS API LOOKUP\n")
            f.write("-" * 80 + "\n")
            f.write(f"Successful: {len(self.stage1_results)}\n")
            f.write(f"Failed: {len(self.domains) - len(self.stage1_results)}\n")
            f.write(f"Success Rate: {len(self.stage1_results)/len(self.domains)*100:.1f}%\n\n")
            
            f.write("-" * 80 + "\n")
            f.write("STAGE 2: PLAYWRIGHT SCRAPING\n")
            f.write("-" * 80 + "\n")
            successful_stage2 = sum(1 for r in self.stage2_results if r.get('success'))
            f.write(f"Processed: {len(self.stage2_results)}\n")
            f.write(f"Successful: {successful_stage2}\n")
            f.write(f"Screenshots Captured: {len(list(self.screenshots_dir.glob('*.png')))}\n\n")
            
            f.write("-" * 80 + "\n")
            f.write("STAGE 3: TXT VERIFICATION\n")
            f.write("-" * 80 + "\n")
            f.write(f"Tasks Created: {len(self.stage3_results)}\n")
            f.write(f"Status: Waiting for DNS records\n\n")
            
            f.write("-" * 80 + "\n")
            f.write("OVERALL SUMMARY\n")
            f.write("-" * 80 + "\n")
            total_resolved = len(self.stage1_results) + successful_stage2
            f.write(f"Resolved (Stage 1 + 2): {total_resolved}/{len(self.domains)} ({total_resolved/len(self.domains)*100:.1f}%)\n")
            f.write(f"Pending TXT Verification: {len(self.stage3_results)}\n")
            f.write(f"Total Success Rate: {total_resolved/len(self.domains)*100:.1f}%\n")
        
        # Also save as JSON
        report_json = self.results_dir / "FINAL_REPORT.json"
        with open(report_json, 'w', encoding='utf-8') as f:
            json.dump({
                'run_id': self.run_id,
                'timestamp': datetime.now().isoformat(),
                'total_time_seconds': total_time,
                'total_domains': len(self.domains),
                'stage1': {
                    'successful': len(self.stage1_results),
                    'failed': len(self.domains) - len(self.stage1_results)
                },
                'stage2': {
                    'processed': len(self.stage2_results),
                    'successful': sum(1 for r in self.stage2_results if r.get('success'))
                },
                'stage3': {
                    'tasks_created': len(self.stage3_results)
                }
            }, f, indent=2)
        
        # Save combined results as CSV
        csv_file = self.results_dir / f"all_results_{self.run_id}.csv"
        CSVExporter.save_to_file(self.stage1_results, str(csv_file))
        
        print(f"\n📄 Final report generated:")
        print(f"   {report_file}")
        print(f"   {report_json}")


async def main():
    """Main entry point."""
    
    # Generate run ID
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Input CSV
    input_csv = "../Houthoff-Challenge_Domain-Names.csv"
    
    if not Path(input_csv).exists():
        print(f"❌ Error: Input file not found: {input_csv}")
        return
    
    # Create and run pipeline
    pipeline = CompleteDomainPipeline(run_id)
    await pipeline.run_complete_pipeline(input_csv)
    
    print(f"\n🎉 Complete! Check results in: data/run_{run_id}/")


if __name__ == "__main__":
    asyncio.run(main())

