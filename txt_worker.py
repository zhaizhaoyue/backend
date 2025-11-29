"""
TXT Worker - Background process for DNS TXT verification.
Uses dig command with Cloudflare DNS (1.1.1.1) to poll for TXT records.
"""
import subprocess
import time
import signal
import sys
from datetime import datetime, timezone
from typing import Tuple, Optional
from txt_database import TXTDatabase
from txt_verification import TXTVerificationManager


class TXTWorker:
    """Background worker for TXT verification polling."""
    
    def __init__(self, db_path: str = "./txt_verification.db", 
                 poll_interval: int = 60):
        """Initialize TXT worker.
        
        Args:
            db_path: Path to SQLite database
            poll_interval: Polling interval in seconds (default: 60)
        """
        self.db = TXTDatabase(db_path)
        self.verification_manager = TXTVerificationManager(db_path)
        self.poll_interval = poll_interval
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n[TXT Worker] Received signal {signum}, shutting down...")
        self.running = False
    
    def check_txt_via_dig(self, domain: str, expected_token: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Check TXT record using dig command.
        
        Args:
            domain: Domain name to check
            expected_token: Expected verification token
            
        Returns:
            Tuple of (success, dns_raw_output, error_message)
        """
        try:
            # Use Cloudflare DNS (1.1.1.1) with dig
            cmd = ["dig", "@1.1.1.1", "TXT", domain, "+short"]
            
            print(f"[TXT Worker] Checking {domain} for token: {expected_token}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = result.stdout.strip()
            
            # Check if there's any output
            if not output:
                print(f"[TXT Worker] No TXT records found for {domain}")
                return False, output, "NO_ANSWER"
            
            print(f"[TXT Worker] DNS output for {domain}: {output}")
            
            # Parse TXT records
            lines = output.splitlines()
            for line in lines:
                # Remove quotes from TXT record value
                txt_value = line.strip().strip('"')
                
                # Check if token is present
                if expected_token in txt_value:
                    print(f"[TXT Worker] ✓ Token found for {domain}!")
                    return True, output, None
            
            print(f"[TXT Worker] Token not found in TXT records for {domain}")
            return False, output, "TOKEN_NOT_FOUND"
            
        except subprocess.TimeoutExpired:
            print(f"[TXT Worker] Timeout checking {domain}")
            return False, None, "TIMEOUT"
        except FileNotFoundError:
            print(f"[TXT Worker] ERROR: 'dig' command not found. Please install bind-tools/dnsutils.")
            return False, None, "DIG_NOT_INSTALLED"
        except Exception as e:
            print(f"[TXT Worker] Error checking {domain}: {e}")
            return False, None, str(e)
    
    def process_task(self, task: dict):
        """Process a single TXT verification task.
        
        Args:
            task: Task dictionary from database
        """
        task_id = task['id']
        domain = task['domain']
        expected_token = task['expected_token']
        
        print(f"\n[TXT Worker] Processing task {task_id} for domain {domain}")
        print(f"[TXT Worker] Attempt {task['attempts'] + 1}/{task['max_attempts']}")
        
        # Check TXT record
        success, dns_raw, error = self.check_txt_via_dig(domain, expected_token)
        now = datetime.now(timezone.utc)
        
        if success:
            # Token found - mark as verified
            print(f"[TXT Worker] ✓ Verification successful for {domain}")
            self.db.mark_task_verified(task_id, dns_raw, now)
            
            # Update domain result status
            self.verification_manager.update_domain_verified(
                domain=domain,
                case_id=task['case_id'],
                verified_at=now
            )
        else:
            # Token not found - increment attempt
            print(f"[TXT Worker] ✗ Verification not yet complete for {domain}: {error}")
            self.db.increment_task_attempt(task_id, dns_raw, error, now)
            
            # Check if max attempts reached
            if task['attempts'] + 1 >= task['max_attempts']:
                print(f"[TXT Worker] Max attempts reached for {domain}, marking as FAILED")
    
    def run_once(self):
        """Run one iteration of the worker loop."""
        # Get all waiting tasks
        tasks = self.db.get_waiting_tasks()
        
        if not tasks:
            print(f"[TXT Worker] No waiting tasks at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return
        
        print(f"\n[TXT Worker] Found {len(tasks)} waiting task(s)")
        
        # Process each task
        for task in tasks:
            self.process_task(task)
    
    def run(self):
        """Run the worker loop continuously."""
        self.running = True
        
        print("=" * 60)
        print("[TXT Worker] Starting TXT Verification Worker")
        print(f"[TXT Worker] Polling interval: {self.poll_interval} seconds")
        print(f"[TXT Worker] Database: {self.db.db_path}")
        print("=" * 60)
        
        iteration = 0
        
        while self.running:
            try:
                iteration += 1
                print(f"\n[TXT Worker] === Iteration {iteration} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
                
                # Run one iteration
                self.run_once()
                
                # Sleep until next iteration
                if self.running:
                    print(f"[TXT Worker] Sleeping for {self.poll_interval} seconds...")
                    time.sleep(self.poll_interval)
                    
            except KeyboardInterrupt:
                print("\n[TXT Worker] Keyboard interrupt received")
                break
            except Exception as e:
                print(f"[TXT Worker] ERROR in main loop: {e}")
                import traceback
                traceback.print_exc()
                # Continue running even if one iteration fails
                time.sleep(self.poll_interval)
        
        print("\n[TXT Worker] Worker stopped")
        print("=" * 60)


def main():
    """Main entry point for TXT worker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="TXT Verification Worker")
    parser.add_argument(
        "--db-path",
        default="./txt_verification.db",
        help="Path to SQLite database (default: ./txt_verification.db)"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="Polling interval in seconds (default: 60)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (for testing)"
    )
    
    args = parser.parse_args()
    
    # Create and run worker
    worker = TXTWorker(
        db_path=args.db_path,
        poll_interval=args.poll_interval
    )
    
    if args.once:
        print("[TXT Worker] Running in single-iteration mode")
        worker.run_once()
    else:
        worker.run()


if __name__ == "__main__":
    main()


