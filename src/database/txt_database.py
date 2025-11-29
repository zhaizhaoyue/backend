"""
Database layer for TXT verification tasks.
Uses SQLite for persistence.
"""
import sqlite3
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict
from contextlib import contextmanager
from pathlib import Path


class TXTDatabase:
    """Database manager for TXT verification tasks."""
    
    def __init__(self, db_path: str = "./txt_verification.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # TXT verification tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS txt_verification_tasks (
                    id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    txt_name TEXT NOT NULL,
                    expected_token TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 1,
                    last_checked_at TEXT,
                    verified_at TEXT,
                    fail_reason TEXT,
                    dns_raw_result TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create indexes for txt_verification_tasks
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_txt_status ON txt_verification_tasks(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_txt_domain ON txt_verification_tasks(domain)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_txt_case_id ON txt_verification_tasks(case_id)
            """)
            
            # Domain results table (to track ownership status)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS domain_results (
                    id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    ownership_status TEXT NOT NULL,
                    ownership_reason TEXT,
                    txt_task_id TEXT,
                    rdap_raw TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create indexes for domain_results
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_domain_domain ON domain_results(domain)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_domain_case_id ON domain_results(case_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_domain_txt_task_id ON domain_results(txt_task_id)
            """)
            
            conn.commit()
    
    def create_txt_task(self, task_data: Dict) -> str:
        """Create a new TXT verification task.
        
        Args:
            task_data: Task data dictionary
            
        Returns:
            Task ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO txt_verification_tasks 
                (id, case_id, domain, txt_name, expected_token, status, 
                 attempts, max_attempts, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_data['id'],
                task_data['case_id'],
                task_data['domain'],
                task_data['txt_name'],
                task_data['expected_token'],
                task_data['status'],
                task_data.get('attempts', 0),
                task_data.get('max_attempts', 60),
                task_data['created_at'].isoformat(),
                task_data['updated_at'].isoformat()
            ))
            conn.commit()
            return task_data['id']
    
    def get_txt_task(self, task_id: str) -> Optional[Dict]:
        """Get TXT task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task data dictionary or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM txt_verification_tasks WHERE id = ?",
                (task_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_dict(row)
            return None
    
    def get_waiting_tasks(self) -> List[Dict]:
        """Get all tasks waiting for verification.
        
        Returns:
            List of task data dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM txt_verification_tasks 
                WHERE status = 'WAITING' AND attempts < max_attempts
                ORDER BY created_at ASC
            """)
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def update_txt_task(self, task_id: str, updates: Dict):
        """Update TXT task fields.
        
        Args:
            task_id: Task ID
            updates: Dictionary of fields to update
        """
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Build SET clause dynamically
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        values.append(task_id)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE txt_verification_tasks SET {set_clause} WHERE id = ?",
                values
            )
            conn.commit()
    
    def mark_task_verified(self, task_id: str, dns_raw: str, verified_at: datetime):
        """Mark task as verified.
        
        Args:
            task_id: Task ID
            dns_raw: Raw DNS output
            verified_at: Verification timestamp
        """
        self.update_txt_task(task_id, {
            'status': 'VERIFIED',
            'dns_raw_result': dns_raw,
            'verified_at': verified_at.isoformat(),
            'last_checked_at': verified_at.isoformat()
        })
    
    def increment_task_attempt(self, task_id: str, dns_raw: Optional[str], 
                               error: Optional[str], checked_at: datetime):
        """Increment task attempt counter.
        
        Args:
            task_id: Task ID
            dns_raw: Raw DNS output (if available)
            error: Error message (if any)
            checked_at: Check timestamp
        """
        task = self.get_txt_task(task_id)
        if not task:
            return
        
        new_attempts = task['attempts'] + 1
        updates = {
            'attempts': new_attempts,
            'last_checked_at': checked_at.isoformat()
        }
        
        if dns_raw:
            updates['dns_raw_result'] = dns_raw
        
        if error:
            updates['fail_reason'] = error
        
        # Mark as FAILED if max attempts reached
        if new_attempts >= task['max_attempts']:
            updates['status'] = 'FAILED'
        
        self.update_txt_task(task_id, updates)
    
    def save_domain_result(self, domain_data: Dict) -> str:
        """Save or update domain result.
        
        Args:
            domain_data: Domain result data
            
        Returns:
            Domain result ID
        """
        result_id = domain_data.get('id', f"{domain_data['case_id']}_{domain_data['domain']}")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if exists
            cursor.execute(
                "SELECT id FROM domain_results WHERE domain = ? AND case_id = ?",
                (domain_data['domain'], domain_data['case_id'])
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE domain_results 
                    SET ownership_status = ?, ownership_reason = ?, 
                        txt_task_id = ?, updated_at = ?
                    WHERE domain = ? AND case_id = ?
                """, (
                    domain_data['ownership_status'],
                    domain_data.get('ownership_reason'),
                    domain_data.get('txt_task_id'),
                    datetime.now(timezone.utc).isoformat(),
                    domain_data['domain'],
                    domain_data['case_id']
                ))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO domain_results 
                    (id, case_id, domain, ownership_status, ownership_reason, 
                     txt_task_id, rdap_raw, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result_id,
                    domain_data['case_id'],
                    domain_data['domain'],
                    domain_data['ownership_status'],
                    domain_data.get('ownership_reason'),
                    domain_data.get('txt_task_id'),
                    domain_data.get('rdap_raw'),
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat()
                ))
            
            conn.commit()
            return result_id
    
    def update_domain_ownership(self, domain: str, case_id: str, 
                                ownership_status: str, ownership_reason: str):
        """Update domain ownership status.
        
        Args:
            domain: Domain name
            case_id: Case/run ID
            ownership_status: New ownership status
            ownership_reason: Reason for status
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE domain_results 
                SET ownership_status = ?, ownership_reason = ?, updated_at = ?
                WHERE domain = ? AND case_id = ?
            """, (
                ownership_status,
                ownership_reason,
                datetime.now(timezone.utc).isoformat(),
                domain,
                case_id
            ))
            conn.commit()
    
    def get_tasks_by_case(self, case_id: str) -> List[Dict]:
        """Get all TXT tasks for a case.
        
        Args:
            case_id: Case/run ID
            
        Returns:
            List of task dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM txt_verification_tasks WHERE case_id = ?",
                (case_id,)
            )
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Convert SQLite row to dictionary.
        
        Args:
            row: SQLite row object
            
        Returns:
            Dictionary representation
        """
        return dict(row)
