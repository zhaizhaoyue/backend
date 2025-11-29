"""
Demo script for TXT Verification Layer.
Demonstrates the complete workflow with example domains.
"""
import json
from txt_verification import TXTVerificationManager
from txt_worker import TXTWorker


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def demo_ownership_assessment():
    """Demonstrate ownership assessment logic."""
    print_section("Demo 1: Ownership Assessment")
    
    manager = TXTVerificationManager(db_path="./demo_txt_verification.db")
    
    # Test cases
    test_cases = [
        {
            "domain": "clear-company.com",
            "data": {
                "registrant_org": "Acme Corporation",
                "registrant_name_raw": "John Smith"
            },
            "expected": "OK"
        },
        {
            "domain": "privacy-protected.com",
            "data": {
                "registrant_org": "REDACTED FOR PRIVACY",
                "registrant_name_raw": "Privacy Protected"
            },
            "expected": "PENDING_TXT"
        },
        {
            "domain": "whoisguard.com",
            "data": {
                "registrant_org": "WhoisGuard, Inc.",
                "registrant_name_raw": None
            },
            "expected": "PENDING_TXT"
        },
        {
            "domain": "missing-info.com",
            "data": {
                "registrant_org": None,
                "registrant_name_raw": ""
            },
            "expected": "PENDING_TXT"
        }
    ]
    
    case_id = "demo-case-001"
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test_case['domain']}")
        print("-" * 70)
        
        print(f"Input Data:")
        print(f"  registrant_org: {test_case['data']['registrant_org']}")
        print(f"  registrant_name: {test_case['data']['registrant_name_raw']}")
        
        # Assess ownership
        status, reason, task_id = manager.assess_ownership(
            domain=test_case['domain'],
            case_id=case_id,
            parsed_data=test_case['data']
        )
        
        print(f"\nResult:")
        print(f"  Status: {status}")
        print(f"  Reason: {reason}")
        
        if task_id:
            print(f"  TXT Task ID: {task_id}")
            print(f"\n  Verification Instructions:")
            instructions = manager.get_verification_instructions(task_id)
            for line in instructions.split('\n'):
                print(f"    {line}")
        
        # Verify expectation
        expected_status = test_case['expected']
        if status == expected_status:
            print(f"\n  ✅ Result matches expected: {expected_status}")
        else:
            print(f"\n  ❌ Unexpected result! Expected {expected_status}, got {status}")
        
        print()


def demo_txt_worker_check():
    """Demonstrate TXT worker DNS checking."""
    print_section("Demo 2: TXT Worker DNS Check")
    
    worker = TXTWorker(db_path="./demo_txt_verification.db", poll_interval=5)
    
    # Test with well-known domains
    test_domains = [
        ("google.com", "momen-verify-demo123"),
        ("cloudflare.com", "momen-verify-demo456"),
    ]
    
    print("Testing DNS TXT record checking with real domains:")
    print("(These domains should have TXT records, but not our tokens)\n")
    
    for domain, fake_token in test_domains:
        print(f"Domain: {domain}")
        print(f"Looking for token: {fake_token}")
        
        success, dns_raw, error = worker.check_txt_via_dig(domain, fake_token)
        
        print(f"  Result: {'✓ Found' if success else '✗ Not found'}")
        print(f"  Error: {error if error else 'None'}")
        
        if dns_raw:
            # Show first 150 chars of DNS output
            dns_preview = dns_raw[:150] + "..." if len(dns_raw) > 150 else dns_raw
            print(f"  DNS Output: {dns_preview}")
        
        print()


def demo_complete_workflow():
    """Demonstrate complete verification workflow."""
    print_section("Demo 3: Complete Verification Workflow")
    
    manager = TXTVerificationManager(db_path="./demo_txt_verification.db")
    
    print("Simulating a complete verification workflow:\n")
    
    # Step 1: Domain with privacy protection
    domain = "example-privacy.com"
    case_id = "demo-workflow-001"
    
    print("Step 1: Receive domain with privacy protection")
    print(f"  Domain: {domain}")
    
    parsed_data = {
        "registrant_org": "Privacy Service Inc.",
        "registrant_name_raw": "REDACTED"
    }
    print(f"  Registrant: {parsed_data['registrant_org']}")
    
    # Step 2: Assess ownership
    print("\nStep 2: Assess ownership")
    status, reason, task_id = manager.assess_ownership(domain, case_id, parsed_data)
    
    print(f"  Status: {status}")
    print(f"  Reason: {reason}")
    print(f"  Task created: {'Yes' if task_id else 'No'}")
    
    if not task_id:
        print("\n❌ No task created, workflow cannot continue")
        return
    
    # Step 3: Get task details
    print("\nStep 3: Retrieve task details")
    task = manager.get_task_status(task_id)
    
    print(f"  Task ID: {task['id']}")
    print(f"  Domain: {task['domain']}")
    print(f"  Token: {task['expected_token']}")
    print(f"  Status: {task['status']}")
    print(f"  Attempts: {task['attempts']}/{task['max_attempts']}")
    
    # Step 4: Show instructions
    print("\nStep 4: Generate configuration instructions for user")
    instructions = manager.get_verification_instructions(task_id)
    print("  Instructions to send to domain owner:")
    print("  " + "-" * 66)
    for line in instructions.split('\n'):
        print(f"  {line}")
    print("  " + "-" * 66)
    
    # Step 5: Simulate DNS check (will fail as we don't actually add the record)
    print("\nStep 5: Worker checks DNS (simulation)")
    worker = TXTWorker(db_path="./demo_txt_verification.db", poll_interval=5)
    
    success, dns_raw, error = worker.check_txt_via_dig(domain, task['expected_token'])
    
    print(f"  DNS Check Result: {'✓ Verified' if success else '✗ Not verified yet'}")
    print(f"  Error: {error if error else 'None'}")
    
    if success:
        print("\n  ✅ Verification successful!")
        print("  System would now update domain status to VERIFIED_BY_TXT")
    else:
        print("\n  ⏳ Verification pending...")
        print("  In production, worker would continue checking every 60 seconds")
        print("  Once domain owner adds the TXT record, verification completes automatically")
    
    # Step 6: Show what happens after verification
    print("\nStep 6: After successful verification (conceptual)")
    print("  1. Worker detects token in DNS")
    print("  2. Task status: WAITING → VERIFIED")
    print("  3. Domain ownership_status: PENDING_TXT → VERIFIED_BY_TXT")
    print("  4. Verification timestamp and DNS output saved as evidence")
    print("  5. Frontend/Report shows domain control is confirmed")


def demo_database_queries():
    """Demonstrate database query capabilities."""
    print_section("Demo 4: Database Queries")
    
    manager = TXTVerificationManager(db_path="./demo_txt_verification.db")
    
    case_id = "demo-case-001"
    
    print(f"Querying all tasks for case: {case_id}\n")
    
    tasks = manager.get_tasks_by_case(case_id)
    
    if not tasks:
        print("  No tasks found for this case")
        return
    
    print(f"Found {len(tasks)} task(s):\n")
    
    for i, task in enumerate(tasks, 1):
        print(f"Task {i}:")
        print(f"  Domain: {task['domain']}")
        print(f"  Status: {task['status']}")
        print(f"  Token: {task['expected_token']}")
        print(f"  Attempts: {task['attempts']}/{task['max_attempts']}")
        print(f"  Created: {task['created_at']}")
        
        if task['status'] == 'VERIFIED':
            print(f"  ✅ Verified at: {task.get('verified_at', 'N/A')}")
        elif task['status'] == 'FAILED':
            print(f"  ❌ Failed: {task.get('fail_reason', 'Unknown')}")
        
        print()


def main():
    """Run all demos."""
    print("\n" + "#" * 70)
    print("#" + " " * 68 + "#")
    print("#" + "  TXT Verification Layer - Interactive Demo".center(68) + "#")
    print("#" + " " * 68 + "#")
    print("#" * 70)
    
    print("\nThis demo will showcase the TXT verification workflow:")
    print("  1. Ownership assessment logic")
    print("  2. DNS TXT record checking")
    print("  3. Complete verification workflow")
    print("  4. Database queries")
    
    try:
        # Run demos
        demo_ownership_assessment()
        demo_txt_worker_check()
        demo_complete_workflow()
        demo_database_queries()
        
        # Summary
        print_section("Demo Complete!")
        print("Key Takeaways:")
        print("  ✅ System automatically detects privacy-protected domains")
        print("  ✅ Unique verification tokens are generated securely")
        print("  ✅ Clear instructions provided for domain owners")
        print("  ✅ Worker polls DNS automatically in the background")
        print("  ✅ Verification status updates automatically")
        print("  ✅ Complete audit trail maintained in database")
        
        print("\nNext Steps:")
        print("  • Review code in txt_verification.py, txt_worker.py")
        print("  • Run test suite: python test_txt_verification.py")
        print("  • Start API server: python main.py")
        print("  • Start worker: ./start_txt_worker.sh")
        print("  • Read full docs: TXT_VERIFICATION_README.md")
        
        print("\n" + "#" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


