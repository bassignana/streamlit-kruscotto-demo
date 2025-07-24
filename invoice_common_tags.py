#!/usr/bin/env python3
"""
Invoice XML Common Tags Finder

This tool analyzes XML invoices from one or more folders and finds common tags
that appear across all invoices. Designed for Italian electronic invoices 
(Fattura Elettronica) and other XML invoice formats.

Features:
- Handles multiple folders containing XML invoices
- Extracts all XML tags from each invoice
- Finds common tags present in ALL invoices
- Provides detailed analysis and statistics
- Handles XML parsing errors gracefully
- Supports different XML encodings

Usage:
    python invoice_common_tags.py folder1 [folder2 folder3 ...]
    python invoice_common_tags.py --help
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict, Counter
from typing import Set, List, Dict, Tuple
import argparse


class InvoiceTagAnalyzer:
    """Analyzes XML invoice files to find common tags."""
    
    def __init__(self):
        self.all_tags_per_invoice: List[Set[str]] = []
        self.all_tag_paths_per_invoice: List[Set[str]] = []
        self.invoice_files: List[str] = []
        self.parsing_errors: List[Tuple[str, str]] = []
        self.tag_frequency: Counter = Counter()
        self.tag_path_frequency: Counter = Counter()
        
    def extract_tags_from_xml(self, xml_file_path: str) -> Tuple[Set[str], Set[str]]:
        """
        Extract all unique XML tags and their full paths from a single XML file.
        
        Args:
            xml_file_path: Path to the XML file
            
        Returns:
            Tuple of (set of unique tag names, set of unique tag paths)
        """
        tags = set()
        tag_paths = set()
        
        try:
            # Try different encodings commonly used in XML invoices
            encodings = ['utf-8', 'iso-8859-1', 'windows-1252']
            tree = None
            
            for encoding in encodings:
                try:
                    with open(xml_file_path, 'r', encoding=encoding) as file:
                        content = file.read()
                    tree = ET.fromstring(content)
                    break
                except (UnicodeDecodeError, ET.ParseError):
                    continue
            
            if tree is None:
                # Try parsing without specifying encoding (let ET decide)
                tree = ET.parse(xml_file_path).getroot()
            
            # Recursively extract all tag names and paths
            def extract_tags_recursive(element, path=""):
                # Remove namespace prefixes for cleaner comparison
                tag_name = element.tag
                if '}' in tag_name:
                    tag_name = tag_name.split('}')[1]
                
                # Build current path
                current_path = f"{path}/{tag_name}" if path else tag_name
                
                tags.add(tag_name)
                tag_paths.add(current_path)
                
                for child in element:
                    extract_tags_recursive(child, current_path)
            
            extract_tags_recursive(tree)
            
        except ET.ParseError as e:
            self.parsing_errors.append((xml_file_path, f"XML Parse Error: {str(e)}"))
        except FileNotFoundError:
            self.parsing_errors.append((xml_file_path, "File not found"))
        except Exception as e:
            self.parsing_errors.append((xml_file_path, f"Unexpected error: {str(e)}"))
        
        return tags, tag_paths
    
    def find_xml_files(self, folder_paths: List[str]) -> List[str]:
        """
        Find all XML files in the specified folders recursively.
        
        Args:
            folder_paths: List of folder paths to search
            
        Returns:
            List of XML file paths
        """
        xml_files = []
        
        for folder_path in folder_paths:
            folder = Path(folder_path)
            
            if not folder.exists():
                print(f"⚠️  Warning: Folder '{folder_path}' does not exist")
                continue
                
            if not folder.is_dir():
                print(f"⚠️  Warning: '{folder_path}' is not a directory")
                continue
            
            # Find all XML files recursively (case-insensitive)
            xml_patterns = ['**/*.xml', '**/*.XML']
            for pattern in xml_patterns:
                xml_files.extend(list(folder.glob(pattern)))
        
        return [str(f) for f in xml_files]
    
    def analyze_invoices(self, folder_paths: List[str]) -> Dict:
        """
        Main analysis function that processes all invoices and finds common tags.
        
        Args:
            folder_paths: List of folder paths containing XML invoices
            
        Returns:
            Dictionary with analysis results
        """
        print("🔍 Searching for XML invoice files...")
        
        # Find all XML files
        xml_files = self.find_xml_files(folder_paths)
        
        if not xml_files:
            print("❌ No XML files found in the specified folders")
            return {}
        
        print(f"📄 Found {len(xml_files)} XML files")
        
        # Process each XML file
        print("\n📊 Analyzing XML files...")
        for i, xml_file in enumerate(xml_files, 1):
            print(f"   Processing {i}/{len(xml_files)}: {Path(xml_file).name}")
            
            tags, tag_paths = self.extract_tags_from_xml(xml_file)
            
            if tags:  # Only add if we successfully extracted tags
                self.all_tags_per_invoice.append(tags)
                self.all_tag_paths_per_invoice.append(tag_paths)
                self.invoice_files.append(xml_file)
                
                # Update frequency counters
                for tag in tags:
                    self.tag_frequency[tag] += 1
                for tag_path in tag_paths:
                    self.tag_path_frequency[tag_path] += 1
        
        # Calculate common tags and paths
        if not self.all_tags_per_invoice:
            print("❌ No valid XML files could be processed")
            return {}
        
        # Find tags that appear in ALL invoices
        common_tags = set.intersection(*self.all_tags_per_invoice)
        common_tag_paths = set.intersection(*self.all_tag_paths_per_invoice)
        
        # Find tags that are NOT common (don't appear in all invoices)
        unique_tags_all = set.union(*self.all_tags_per_invoice) if self.all_tags_per_invoice else set()
        non_common_tags = unique_tags_all - common_tags
        
        # Calculate statistics
        total_invoices = len(self.all_tags_per_invoice)
        
        results = {
            'common_tags': sorted(common_tags),
            'common_tag_paths': sorted(common_tag_paths),
            'non_common_tags': sorted(non_common_tags),
            'total_invoices_processed': total_invoices,
            'total_xml_files_found': len(xml_files),
            'tag_frequency': dict(self.tag_frequency.most_common()),
            'tag_path_frequency': dict(self.tag_path_frequency.most_common()),
            'parsing_errors': self.parsing_errors,
            'processed_files': self.invoice_files
        }
        
        return results
    
    def print_results(self, results: Dict):
        """
        Print analysis results in a formatted way.
        
        Args:
            results: Dictionary containing analysis results
        """
        if not results:
            return
        
        print("\n" + "="*60)
        print("📋 INVOICE XML ANALYSIS RESULTS")
        print("="*60)
        
        print(f"\n📊 SUMMARY:")
        print(f"   • Total XML files found: {results['total_xml_files_found']}")
        print(f"   • Successfully processed: {results['total_invoices_processed']}")
        print(f"   • Parsing errors: {len(results['parsing_errors'])}")
        
        # Common tags (appear in ALL invoices)
        common_tags = results['common_tags']
        print(f"\n🎯 COMMON TAGS (present in ALL {results['total_invoices_processed']} invoices):")
        if common_tags:
            print(f"   Found {len(common_tags)} common tags:")
            for i, tag in enumerate(common_tags, 1):
                print(f"   {i:2d}. {tag}")
        else:
            print("   ❌ No tags are common to all invoices")
        
        # Common tag paths (full hierarchical paths)
        common_tag_paths = results['common_tag_paths']
        if common_tag_paths:
            print(f"\n🌳 COMMON TAG PATHS (full hierarchical structure):")
            print(f"   Found {len(common_tag_paths)} common tag paths:")
            for i, tag_path in enumerate(common_tag_paths, 1):
                print(f"   {i:2d}. {tag_path}")
        
        # Non-common tags (don't appear in all invoices)
        non_common_tags = results['non_common_tags']
        print(f"\n❓ NON-COMMON TAGS (not present in all invoices):")
        if non_common_tags:
            print(f"   Found {len(non_common_tags)} non-common tags:")
            for i, tag in enumerate(non_common_tags, 1):
                frequency = results['tag_frequency'][tag]
                percentage = (frequency / results['total_invoices_processed']) * 100
                print(f"   {i:2d}. {tag:<25} ({frequency}/{results['total_invoices_processed']} invoices, {percentage:.1f}%)")
        else:
            print("   ✅ All tags are common to all invoices")
        
        # Parsing errors
        if results['parsing_errors']:
            print(f"\n⚠️  PARSING ERRORS:")
            for file_path, error in results['parsing_errors']:
                print(f"   • {Path(file_path).name}: {error}")
        
        # Save results to file
        self.save_results_to_file(results)
    
    def save_results_to_file(self, results: Dict):
        """Save results to a text file for future reference."""
        output_file = "invoice_analysis_results.txt"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("INVOICE XML ANALYSIS RESULTS\n")
                f.write("="*50 + "\n\n")
                
                f.write(f"Analysis Date: {__import__('datetime').datetime.now()}\n")
                f.write(f"Total invoices processed: {results['total_invoices_processed']}\n\n")
                
                f.write("COMMON TAGS (present in ALL invoices):\n")
                for tag in results['common_tags']:
                    f.write(f"  - {tag}\n")
                
                f.write(f"\nCOMMON TAG PATHS (full hierarchical structure):\n")
                for tag_path in results['common_tag_paths']:
                    f.write(f"  - {tag_path}\n")
                
                f.write(f"\nNON-COMMON TAGS (not present in all invoices):\n")
                for tag in results['non_common_tags']:
                    frequency = results['tag_frequency'][tag]
                    percentage = (frequency / results['total_invoices_processed']) * 100
                    f.write(f"  - {tag} ({frequency}/{results['total_invoices_processed']} invoices, {percentage:.1f}%)\n")
                
                f.write(f"\nPROCESSED FILES:\n")
                for file_path in results['processed_files']:
                    f.write(f"  - {file_path}\n")
                
                if results['parsing_errors']:
                    f.write(f"\nPARSING ERRORS:\n")
                    for file_path, error in results['parsing_errors']:
                        f.write(f"  - {file_path}: {error}\n")
            
            print(f"\n💾 Results saved to: {output_file}")
            
        except Exception as e:
            print(f"⚠️  Could not save results to file: {e}")


def main():
    """Main function to run the invoice analysis."""
    parser = argparse.ArgumentParser(
        description="Find common XML tags across invoice files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python invoice_common_tags.py invoices/
  python invoice_common_tags.py sales_invoices/ purchase_invoices/
  python invoice_common_tags.py /path/to/invoices --verbose
        """
    )
    
    parser.add_argument(
        'folders',
        nargs='+',
        help='One or more folders containing XML invoice files'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    print("🏷️  Invoice XML Common Tags Finder")
    print("="*40)
    
    # Validate folders
    valid_folders = []
    for folder in args.folders:
        if os.path.exists(folder) and os.path.isdir(folder):
            valid_folders.append(folder)
            print(f"✅ Folder: {folder}")
        else:
            print(f"❌ Invalid folder: {folder}")
    
    if not valid_folders:
        print("\n❌ No valid folders provided. Exiting.")
        sys.exit(1)
    
    # Run analysis
    analyzer = InvoiceTagAnalyzer()
    results = analyzer.analyze_invoices(valid_folders)
    
    if results:
        analyzer.print_results(results)
        
        # Return common tags as the main result
        common_tags = results['common_tags']
        if common_tags:
            print(f"\n🎯 FINAL RESULT: {len(common_tags)} common tags found across all invoices")
            return common_tags
        else:
            print(f"\n⚠️  No tags are common to all {results['total_invoices_processed']} invoices")
            return []
    else:
        print("\n❌ Analysis failed - no results to display")
        return []


if __name__ == "__main__":
    common_tags = main()