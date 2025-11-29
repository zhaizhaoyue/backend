"""
CSV export functionality for domain lookup results.
"""
import csv
from io import StringIO
from typing import List
from models import DomainResult


class CSVExporter:
    """Exporter for domain results to CSV format."""
    
    # Field order - simplified structure
    FIELD_ORDER = [
        "domain",
        "registrant_organization",
        "registrar",
        "registry",
        "creation_date",
        "expiry_date",
        "nameservers",
        "data_source",
        "timestamp",
    ]
    
    @staticmethod
    def format_value(value) -> str:
        """Format a value for CSV output.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted string value
        """
        if value is None:
            return ""
        
        if isinstance(value, bool):
            return "Yes" if value else "No"
        
        if isinstance(value, list):
            # Join list items with semicolons
            return "; ".join(str(item) for item in value)
        
        return str(value)
    
    @staticmethod
    def export_to_csv(results: List[DomainResult]) -> str:
        """Export domain results to CSV format.
        
        Args:
            results: List of DomainResult objects
            
        Returns:
            CSV string
        """
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=CSVExporter.FIELD_ORDER)
        
        # Write header
        writer.writeheader()
        
        # Write rows
        for result in results:
            row = {}
            
            for field in CSVExporter.FIELD_ORDER:
                value = getattr(result, field, None)
                row[field] = CSVExporter.format_value(value)
            
            writer.writerow(row)
        
        return output.getvalue()
    
    @staticmethod
    def save_to_file(results: List[DomainResult], filepath: str):
        """Save domain results to CSV file.
        
        Args:
            results: List of DomainResult objects
            filepath: Path to save CSV file
        """
        csv_content = CSVExporter.export_to_csv(results)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            f.write(csv_content)

