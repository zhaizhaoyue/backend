"""
RDAP and WHOIS client for domain lookups.
"""
import httpx
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import re


class RDAPClient:
    """Client for RDAP and WHOIS lookups."""
    
    # Official RDAP endpoints
    RDAP_ENDPOINTS = {
        ".com": "https://rdap.verisign.com/com/v1/domain/{}",
        ".net": "https://rdap.verisign.com/net/v1/domain/{}",
        ".org": "https://rdap.publicinterestregistry.org/rdap/domain/{}",
        ".nl": "https://rdap.sidn.nl/domain/{}",
    }
    
    # Fallback WHOIS API
    WHOIS_API = "https://api.api-ninjas.com/v1/whois?domain={}"
    
    def __init__(self, api_ninjas_key: Optional[str] = None):
        """Initialize RDAP client.
        
        Args:
            api_ninjas_key: Optional API key for API Ninjas WHOIS fallback
        """
        self.api_ninjas_key = api_ninjas_key
        self.timeout = httpx.Timeout(30.0)
    
    def get_tld(self, domain: str) -> str:
        """Extract TLD from domain."""
        parts = domain.lower().split('.')
        if len(parts) >= 2:
            return '.' + parts[-1]
        return ''
    
    def detect_privacy_protection(self, data: Dict) -> bool:
        """Detect if domain uses privacy protection.
        
        Args:
            data: Parsed RDAP or WHOIS data
            
        Returns:
            True if privacy protection is detected
        """
        privacy_keywords = [
            "REDACTED FOR PRIVACY",
            "Contact Privacy",
            "WhoisGuard",
            "Privacy Protect",
            "REDACTED",
            "Privacy Service",
            "Domains By Proxy"
        ]
        
        # Check registrant org
        registrant_org = data.get('registrant_org', '') or ''
        for keyword in privacy_keywords:
            if keyword.lower() in registrant_org.lower():
                return True
        
        # Check registrant name
        registrant_name = data.get('registrant_name_raw', '') or ''
        for keyword in privacy_keywords:
            if keyword.lower() in registrant_name.lower():
                return True
        
        return False
    
    def parse_rdap_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse RDAP date string to datetime."""
        if not date_str:
            return None
        try:
            # RDAP dates are typically ISO 8601
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    def parse_rdap_response(self, rdap_data: Dict, source_url: str) -> Dict:
        """Parse RDAP JSON response into standardized format.
        
        Args:
            rdap_data: Raw RDAP JSON response
            source_url: The RDAP endpoint URL used
            
        Returns:
            Parsed domain data dictionary
        """
        result = {
            'registrar': None,
            'registry': None,
            'creation_date': None,
            'expiry_date': None,
            'nameservers': [],
            'registrant_org': None,
            'registrant_name_raw': None,
            'raw_status': [],
            'data_source': source_url,
            'data_source_type': 'rdap_registry',
        }
        
        # Extract dates
        events = rdap_data.get('events', [])
        for event in events:
            event_action = event.get('eventAction', '')
            event_date = event.get('eventDate')
            
            if event_action == 'registration':
                result['creation_date'] = self.parse_rdap_date(event_date)
            elif event_action == 'expiration':
                result['expiry_date'] = self.parse_rdap_date(event_date)
        
        # Extract status
        result['raw_status'] = rdap_data.get('status', [])
        
        # Extract nameservers
        nameservers = rdap_data.get('nameservers', [])
        for ns in nameservers:
            ns_name = ns.get('ldhName')
            if ns_name:
                result['nameservers'].append(ns_name)
        
        # Extract entities (registrar, registrant)
        entities = rdap_data.get('entities', [])
        for entity in entities:
            roles = entity.get('roles', [])
            
            if 'registrar' in roles:
                vcards = entity.get('vcardArray', [])
                if len(vcards) > 1:
                    for vcard_item in vcards[1]:
                        if isinstance(vcard_item, list) and len(vcard_item) > 3:
                            if vcard_item[0] == 'fn':
                                result['registrar'] = vcard_item[3]
                                break
            
            if 'registrant' in roles:
                vcards = entity.get('vcardArray', [])
                if len(vcards) > 1:
                    for vcard_item in vcards[1]:
                        if isinstance(vcard_item, list) and len(vcard_item) > 3:
                            if vcard_item[0] == 'org':
                                result['registrant_org'] = vcard_item[3]
                            elif vcard_item[0] == 'fn':
                                result['registrant_name_raw'] = vcard_item[3]
        
        # Try to extract registry name from source URL
        if 'verisign' in source_url:
            result['registry'] = 'Verisign'
        elif 'publicinterestregistry' in source_url:
            result['registry'] = 'Public Interest Registry'
        elif 'sidn.nl' in source_url:
            result['registry'] = 'SIDN'
        
        return result
    
    def parse_whois_response(self, whois_data: Dict) -> Dict:
        """Parse WHOIS API response into standardized format.
        
        Args:
            whois_data: Raw WHOIS API JSON response
            
        Returns:
            Parsed domain data dictionary
        """
        result = {
            'registrar': whois_data.get('registrar'),
            'registry': None,
            'creation_date': None,
            'expiry_date': None,
            'nameservers': whois_data.get('name_servers', []),
            'registrant_org': whois_data.get('registrant_organization'),
            'registrant_name_raw': whois_data.get('registrant_name'),
            'raw_status': [whois_data.get('domain_status', '')] if whois_data.get('domain_status') else [],
            'data_source': 'api.api-ninjas.com',
            'data_source_type': 'whois_api',
        }
        
        # Parse dates
        creation_date = whois_data.get('creation_date')
        if creation_date:
            try:
                result['creation_date'] = datetime.fromisoformat(creation_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        expiry_date = whois_data.get('expiration_date')
        if expiry_date:
            try:
                result['expiry_date'] = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        return result
    
    async def lookup_domain(self, domain: str) -> Tuple[Dict, str]:
        """Perform domain lookup using RDAP or WHOIS.
        
        Args:
            domain: Domain name to lookup
            
        Returns:
            Tuple of (parsed_data, source_url)
        """
        tld = self.get_tld(domain)
        
        # Try RDAP first
        if tld in self.RDAP_ENDPOINTS:
            rdap_url = self.RDAP_ENDPOINTS[tld].format(domain)
            
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(rdap_url)
                    response.raise_for_status()
                    rdap_data = response.json()
                    
                    parsed = self.parse_rdap_response(rdap_data, rdap_url)
                    return parsed, rdap_url
            except Exception as e:
                print(f"RDAP lookup failed for {domain}: {e}")
        
        # Fallback to WHOIS API
        if self.api_ninjas_key:
            whois_url = self.WHOIS_API.format(domain)
            
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    headers = {'X-Api-Key': self.api_ninjas_key}
                    response = await client.get(whois_url, headers=headers)
                    response.raise_for_status()
                    whois_data = response.json()
                    
                    parsed = self.parse_whois_response(whois_data)
                    return parsed, whois_url
            except Exception as e:
                print(f"WHOIS API lookup failed for {domain}: {e}")
        
        # Return empty result if all lookups fail
        return {
            'registrar': None,
            'registry': None,
            'creation_date': None,
            'expiry_date': None,
            'nameservers': [],
            'registrant_org': None,
            'registrant_name_raw': None,
            'raw_status': [],
            'data_source': None,
            'data_source_type': 'failed',
        }, ''

