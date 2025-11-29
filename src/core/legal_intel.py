"""
Legal intelligence classifier for domain ownership risk assessment.
"""
from datetime import datetime, timezone
from typing import List, Tuple
from dateutil.relativedelta import relativedelta
import re


class LegalIntelligence:
    """Classifier for legal risk and ownership assessment."""
    
    def __init__(self, expected_group_names: List[str], expiry_threshold_months: int = 6):
        """Initialize legal intelligence classifier.
        
        Args:
            expected_group_names: List of expected company names in the group
            expiry_threshold_months: Threshold for expiry warning in months
        """
        self.expected_group_names = [self._normalize_name(name) for name in expected_group_names]
        self.expiry_threshold_months = expiry_threshold_months
    
    def _normalize_name(self, name: str) -> str:
        """Normalize company name for comparison.
        
        Removes punctuation, extra spaces, and converts to lowercase.
        """
        if not name:
            return ''
        # Remove common punctuation and normalize spaces
        normalized = re.sub(r'[.,\-_()]+', ' ', name.lower())
        normalized = ' '.join(normalized.split())
        return normalized
    
    def _is_natural_person(self, name: str) -> bool:
        """Heuristic to detect if a name appears to be a natural person.
        
        Args:
            name: Registrant name to check
            
        Returns:
            True if name appears to be a natural person
        """
        if not name:
            return False
        
        name_lower = name.lower()
        
        # Common company suffixes
        company_indicators = [
            'inc', 'llc', 'ltd', 'corp', 'corporation', 'company',
            'gmbh', 'b.v.', 'bv', 'n.v.', 'nv', 'sa', 's.a.',
            'limited', 'holdings', 'group', 'enterprises', 'solutions',
            'technologies', 'services', 'international'
        ]
        
        for indicator in company_indicators:
            if indicator in name_lower:
                return False
        
        # Check if it looks like a person name (2-4 words, no special chars)
        words = name.split()
        if 2 <= len(words) <= 4:
            # If all words start with capital letter and no numbers/special chars
            if all(word[0].isupper() for word in words if word):
                if not re.search(r'[0-9@#$%&*]', name):
                    return True
        
        return False
    
    def _matches_expected_group(self, registrant_org: str) -> bool:
        """Check if registrant organization matches expected group names.
        
        Args:
            registrant_org: Registrant organization name
            
        Returns:
            True if matches any expected group name
        """
        if not registrant_org or not self.expected_group_names:
            return False
        
        normalized_org = self._normalize_name(registrant_org)
        
        for expected_name in self.expected_group_names:
            # Check for exact match or substring match
            if expected_name in normalized_org or normalized_org in expected_name:
                return True
            
            # Check if key words match (for partial matches)
            expected_words = set(expected_name.split())
            org_words = set(normalized_org.split())
            
            # If more than 50% of words match
            if expected_words and org_words:
                overlap = len(expected_words & org_words)
                if overlap / min(len(expected_words), len(org_words)) > 0.5:
                    return True
        
        return False
    
    def _is_expiring_soon(self, expiry_date: datetime) -> bool:
        """Check if domain is expiring soon.
        
        Args:
            expiry_date: Domain expiry date
            
        Returns:
            True if expiring within threshold
        """
        if not expiry_date:
            return False
        
        # Ensure expiry_date is timezone-aware
        if expiry_date.tzinfo is None:
            expiry_date = expiry_date.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        threshold_date = now + relativedelta(months=self.expiry_threshold_months)
        
        return expiry_date <= threshold_date
    
    def classify(
        self,
        registrant_org: str,
        registrant_name: str,
        is_privacy_protected: bool,
        expiry_date: datetime
    ) -> Tuple[str, str, List[str]]:
        """Classify domain ownership risk.
        
        Args:
            registrant_org: Registrant organization name
            registrant_name: Registrant full name
            is_privacy_protected: Whether privacy protection is enabled
            expiry_date: Domain expiry date
            
        Returns:
            Tuple of (legal_risk_flag, ui_ownership_tag, risk_reasons)
        """
        risk_reasons = []
        
        # Check if matches expected group
        if self._matches_expected_group(registrant_org):
            legal_risk_flag = "LIKELY_OK"
            ui_ownership_tag = "INSIDE_GROUP"
            risk_reasons.append("Registrant organization matches expected group name")
            
            # Still check for expiry warning
            if self._is_expiring_soon(expiry_date):
                risk_reasons.append(f"Domain expiring within {self.expiry_threshold_months} months")
            
            return legal_risk_flag, ui_ownership_tag, risk_reasons
        
        # Check for privacy protection
        if is_privacy_protected:
            legal_risk_flag = "NEEDS_ATTENTION"
            ui_ownership_tag = "UNKNOWN_OR_PRIVACY"
            risk_reasons.append("Domain uses privacy protection service")
            
            if self._is_expiring_soon(expiry_date):
                risk_reasons.append(f"Domain expiring within {self.expiry_threshold_months} months")
            
            return legal_risk_flag, ui_ownership_tag, risk_reasons
        
        # Check if registrant appears to be unknown or empty
        if not registrant_org and not registrant_name:
            legal_risk_flag = "NEEDS_ATTENTION"
            ui_ownership_tag = "UNKNOWN_OR_PRIVACY"
            risk_reasons.append("Registrant information is not available")
            
            if self._is_expiring_soon(expiry_date):
                risk_reasons.append(f"Domain expiring within {self.expiry_threshold_months} months")
            
            return legal_risk_flag, ui_ownership_tag, risk_reasons
        
        # Check if registrant appears to be a natural person
        name_to_check = registrant_org or registrant_name
        if self._is_natural_person(name_to_check):
            legal_risk_flag = "HIGH_RISK"
            ui_ownership_tag = "POSSIBLY_OUTSIDE_GROUP"
            risk_reasons.append("Registrant appears to be a natural person (not a company)")
            
            if self._is_expiring_soon(expiry_date):
                risk_reasons.append(f"Domain expiring within {self.expiry_threshold_months} months")
            
            return legal_risk_flag, ui_ownership_tag, risk_reasons
        
        # Default case: registrant doesn't match group
        legal_risk_flag = "HIGH_RISK"
        ui_ownership_tag = "POSSIBLY_OUTSIDE_GROUP"
        risk_reasons.append("Registrant organization does not match expected group names")
        
        if self._is_expiring_soon(expiry_date):
            risk_reasons.append(f"Domain expiring within {self.expiry_threshold_months} months")
        
        return legal_risk_flag, ui_ownership_tag, risk_reasons

