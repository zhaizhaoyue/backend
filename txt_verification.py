"""
TXT Verification Layer for Domain Control Validation.
Implements active control verification via DNS TXT records.
"""
import secrets
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from txt_database import TXTDatabase


class TXTVerificationManager:
    """Manager for TXT verification tasks and logic."""
    
    # Privacy protection keywords
    PRIVACY_KEYWORDS = [
        "REDACTED FOR PRIVACY",
        "Contact Privacy",
        "WhoisGuard",
        "Privacy Protect",
        "REDACTED",
        "Privacy Service",
        "Domains By Proxy",
        "Private Registration",
        "Protected",
    ]
    
    def __init__(self, db_path: str = "./txt_verification.db"):
        """Initialize TXT verification manager.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db = TXTDatabase(db_path)
    
    def generate_verification_token(self) -> str:
        """Generate a random verification token.
        
        Returns:
            Verification token string (e.g., "momen-verify-1a2b3c4d5e6f7g8h")
        """
        suffix = secrets.token_hex(8)
        return f"momen-verify-{suffix}"
    
    def is_ownership_complete(self, parsed_data: Dict) -> bool:
        """Determine if ownership information is complete and reliable.
        
        Args:
            parsed_data: Parsed RDAP/WHOIS data
            
        Returns:
            True if ownership is clear, False if TXT verification is needed
        """
        registrant_org = parsed_data.get('registrant_org', '') or ''
        registrant_name = parsed_data.get('registrant_name_raw', '') or ''
        
        # Check if registrant org exists and is not privacy-protected
        if registrant_org:
            registrant_org_upper = registrant_org.upper()
            
            # Check for privacy keywords
            for keyword in self.PRIVACY_KEYWORDS:
                if keyword.upper() in registrant_org_upper:
                    return False  # Privacy protected, needs TXT verification
            
            # Has valid registrant org
            return True
        
        # Check registrant name as fallback
        if registrant_name:
            registrant_name_upper = registrant_name.upper()
            
            # Check for privacy keywords
            for keyword in self.PRIVACY_KEYWORDS:
                if keyword.upper() in registrant_name_upper:
                    return False
            
            # Has valid registrant name
            return True
        
        # No registrant information available
        return False
    
    def create_txt_task(self, domain: str, case_id: str, 
                       max_attempts: int = 60) -> Tuple[str, str]:
        """Create a new TXT verification task.
        
        Args:
            domain: Domain name to verify
            case_id: Case/run ID
            max_attempts: Maximum number of verification attempts
            
        Returns:
            Tuple of (task_id, expected_token)
        """
        task_id = str(uuid.uuid4())
        token = self.generate_verification_token()
        txt_name = "@"  # Root domain TXT record
        now = datetime.now(timezone.utc)
        
        task_data = {
            'id': task_id,
            'case_id': case_id,
            'domain': domain,
            'txt_name': txt_name,
            'expected_token': token,
            'status': 'WAITING',
            'attempts': 0,
            'max_attempts': max_attempts,
            'created_at': now,
            'updated_at': now
        }
        
        self.db.create_txt_task(task_data)
        
        return task_id, token
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get current status of a TXT verification task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task data dictionary or None
        """
        return self.db.get_txt_task(task_id)
    
    def get_verification_instructions(self, task_id: str) -> Optional[str]:
        """Generate user-friendly verification instructions.
        
        Args:
            task_id: Task ID
            
        Returns:
            Formatted instructions string or None
        """
        task = self.db.get_txt_task(task_id)
        if not task:
            return None
        
        instructions = f"""
请在 DNS 中为域名 {task['domain']} 添加以下 TXT 记录：

Host/名称: {task['txt_name']}
Type/类型: TXT
Value/值: {task['expected_token']}

添加完成后，系统将在 {task['max_attempts']} 分钟内自动检测并验证。
当前已尝试: {task['attempts']}/{task['max_attempts']}
状态: {task['status']}
"""
        
        if task['status'] == 'VERIFIED':
            instructions += f"\n✓ 验证成功于: {task['verified_at']}"
        elif task['status'] == 'FAILED':
            instructions += f"\n✗ 验证失败: {task.get('fail_reason', '超过最大尝试次数')}"
        
        return instructions.strip()
    
    def assess_ownership(self, domain: str, case_id: str, 
                        parsed_data: Dict) -> Tuple[str, str, Optional[str]]:
        """Assess domain ownership and create TXT task if needed.
        
        Args:
            domain: Domain name
            case_id: Case/run ID
            parsed_data: Parsed RDAP/WHOIS data
            
        Returns:
            Tuple of (ownership_status, ownership_reason, txt_task_id)
        """
        if self.is_ownership_complete(parsed_data):
            # Ownership information is complete
            registrant = parsed_data.get('registrant_org') or parsed_data.get('registrant_name_raw')
            return (
                "OK",
                f"RDAP/WHOIS registrant information available: {registrant}",
                None
            )
        else:
            # Ownership incomplete, create TXT verification task
            task_id, token = self.create_txt_task(domain, case_id)
            
            return (
                "PENDING_TXT",
                "Ownership information incomplete or privacy-protected. TXT verification requested.",
                task_id
            )
    
    def get_tasks_by_case(self, case_id: str) -> list:
        """Get all TXT verification tasks for a case.
        
        Args:
            case_id: Case/run ID
            
        Returns:
            List of task dictionaries
        """
        return self.db.get_tasks_by_case(case_id)
    
    def save_domain_result(self, case_id: str, domain: str, 
                          ownership_status: str, ownership_reason: str,
                          txt_task_id: Optional[str] = None,
                          rdap_raw: Optional[str] = None):
        """Save domain result to database.
        
        Args:
            case_id: Case/run ID
            domain: Domain name
            ownership_status: Ownership status
            ownership_reason: Reason for status
            txt_task_id: Optional TXT task ID
            rdap_raw: Optional raw RDAP data
        """
        domain_data = {
            'case_id': case_id,
            'domain': domain,
            'ownership_status': ownership_status,
            'ownership_reason': ownership_reason,
            'txt_task_id': txt_task_id,
            'rdap_raw': rdap_raw
        }
        
        self.db.save_domain_result(domain_data)
    
    def update_domain_verified(self, domain: str, case_id: str, verified_at: datetime):
        """Update domain status after TXT verification succeeds.
        
        Args:
            domain: Domain name
            case_id: Case/run ID
            verified_at: Verification timestamp
        """
        ownership_status = "VERIFIED_BY_TXT"
        ownership_reason = f"Domain control verified via DNS TXT at {verified_at.isoformat()}"
        
        self.db.update_domain_ownership(
            domain=domain,
            case_id=case_id,
            ownership_status=ownership_status,
            ownership_reason=ownership_reason
        )


