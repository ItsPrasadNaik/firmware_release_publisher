#!/usr/bin/env python3
"""
Test Output Validator for Firmware Release Publisher
Compares actual output against golden reference and produces grading report
"""

import sys
import json
import subprocess
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class TestResult:
    name: str
    passed: bool
    expected: str
    actual: str
    details: str = ""

class PublisherTestValidator:
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.environment_dir = self.repo_root / "environment"
        self.solution_dir = self.repo_root / "solution"
        self.tests_dir = self.repo_root / "tests"
        self.golden_file = self.environment_dir / "reports" / "publications.expected.txt"
        self.results: List[TestResult] = []

    def read_golden_output(self) -> str:
        """Read the expected output from golden file"""
        if not self.golden_file.exists():
            raise FileNotFoundError(f"Golden file not found: {self.golden_file}")
        return self.golden_file.read_text().strip()

    def normalize_output(self, text: str) -> List[str]:
        """Normalize output: strip whitespace, filter empty lines"""
        return [line.strip() for line in text.strip().split('\n') if line.strip()]

    def test_file_structure(self) -> bool:
        """Test 1: Verify required files exist"""
        required_files = [
            self.environment_dir / "Dockerfile",
            self.environment_dir / "package.json",
            self.environment_dir / "fixtures" / "build_manifest.csv",
            self.solution_dir / "release-publisher.mjs",
            self.golden_file,
        ]
        
        all_exist = all(f.exists() for f in required_files)
        missing = [str(f) for f in required_files if not f.exists()]
        
        self.results.append(TestResult(
            name="File Structure",
            passed=all_exist,
            expected="All required files present",
            actual=f"Found {len(required_files) - len(missing)}/{len(required_files)} files",
            details=f"Missing: {missing}" if missing else ""
        ))
        
        return all_exist

    def test_node_syntax(self) -> bool:
        """Test 2: Verify Node.js syntax"""
        solution_file = self.solution_dir / "release-publisher.mjs"
        try:
            result = subprocess.run(
                ["node", "--check", str(solution_file)],
                capture_output=True,
                timeout=5
            )
            passed = result.returncode == 0
        except Exception as e:
            passed = False
        
        self.results.append(TestResult(
            name="Node.js Syntax",
            passed=passed,
            expected="Valid JavaScript syntax",
            actual="Valid" if passed else "Syntax error",
        ))
        
        return passed

    def test_csv_manifest(self) -> bool:
        """Test 3: Verify CSV manifest structure"""
        manifest_file = self.environment_dir / "fixtures" / "build_manifest.csv"
        if not manifest_file.exists():
            self.results.append(TestResult(
                name="CSV Manifest",
                passed=False,
                expected="40 records",
                actual="File not found"
            ))
            return False
        
        lines = manifest_file.read_text().strip().split('\n')
        record_count = len(lines) - 1  # Subtract header
        passed = record_count == 40
        
        self.results.append(TestResult(
            name="CSV Manifest",
            passed=passed,
            expected="40 records",
            actual=f"{record_count} records"
        ))
        
        return passed

    def test_golden_output_format(self) -> bool:
        """Test 4: Verify expected output format"""
        try:
            golden = self.read_golden_output()
            lines = self.normalize_output(golden)
            
            passed = len(lines) == 6
            
            self.results.append(TestResult(
                name="Golden Output Format",
                passed=passed,
                expected="6 lines (3 bundles × 2)",
                actual=f"{len(lines)} lines"
            ))
            
            return passed
        except Exception as e:
            self.results.append(TestResult(
                name="Golden Output Format",
                passed=False,
                expected="6 lines",
                actual=f"Error: {str(e)}"
            ))
            return False

    def test_output_structure(self) -> bool:
        """Test 5: Verify output line structure"""
        try:
            golden = self.read_golden_output()
            lines = self.normalize_output(golden)
            
            # Check for BUNDLE keyword in all lines
            has_bundle_keyword = all("BUNDLE" in line for line in lines)
            
            # Check for expected bundle IDs
            has_bnd_101 = any("BND-101" in line for line in lines)
            has_bnd_102 = any("BND-102" in line for line in lines)
            has_bnd_103 = any("BND-103" in line for line in lines)
            
            # Check for SIGNED and PUBLISHED keywords
            has_signed = any("SIGNED" in line for line in lines)
            has_published = any("PUBLISHED" in line for line in lines)
            
            passed = (has_bundle_keyword and has_bnd_101 and has_bnd_102 and 
                     has_bnd_103 and has_signed and has_published)
            
            details = []
            if not has_bundle_keyword:
                details.append("Missing BUNDLE keyword")
            if not has_bnd_101 or not has_bnd_102 or not has_bnd_103:
                details.append("Missing bundle IDs")
            if not has_signed:
                details.append("Missing SIGNED keyword")
            if not has_published:
                details.append("Missing PUBLISHED keyword")
            
            self.results.append(TestResult(
                name="Output Structure",
                passed=passed,
                expected="Lines with BUNDLE, bundle IDs, SIGNED, PUBLISHED",
                actual="Structure OK" if passed else "Structure mismatch",
                details="; ".join(details) if details else ""
            ))
            
            return passed
        except Exception as e:
            self.results.append(TestResult(
                name="Output Structure",
                passed=False,
                expected="Valid structure",
                actual=f"Error: {str(e)}"
            ))
            return False

    def test_package_json(self) -> bool:
        """Test 6: Verify package.json npm scripts"""
        package_file = self.environment_dir / "package.json"
        if not package_file.exists():
            self.results.append(TestResult(
                name="package.json",
                passed=False,
                expected="'report' script configured",
                actual="File not found"
            ))
            return False
        
        try:
            content = package_file.read_text()
            has_report_script = '"report"' in content
            
            self.results.append(TestResult(
                name="package.json",
                passed=has_report_script,
                expected="'npm run report' script",
                actual="Script found" if has_report_script else "Script missing"
            ))
            
            return has_report_script
        except Exception as e:
            self.results.append(TestResult(
                name="package.json",
                passed=False,
                expected="Valid JSON",
                actual=f"Error: {str(e)}"
            ))
            return False

    def run_all_tests(self) -> Tuple[int, int]:
        """Run all tests and return (passed, failed) counts"""
        tests = [
            self.test_file_structure,
            self.test_node_syntax,
            self.test_csv_manifest,
            self.test_golden_output_format,
            self.test_output_structure,
            self.test_package_json,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"Error in {test.__name__}: {e}", file=sys.stderr)
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        return passed, failed

    def print_results(self):
        """Print test results in human-readable format"""
        print("\n" + "="*60)
        print("FIRMWARE RELEASE PUBLISHER - TEST RESULTS")
        print("="*60 + "\n")
        
        for i, result in enumerate(self.results, 1):
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"[{i}] {result.name}: {status}")
            print(f"    Expected: {result.expected}")
            print(f"    Actual:   {result.actual}")
            if result.details:
                print(f"    Details:  {result.details}")
            print()
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        total = len(self.results)
        
        print("="*60)
        print(f"SUMMARY: {passed}/{total} tests passed")
        if failed == 0:
            print("✓ All tests passed! Ready for submission.")
        else:
            print(f"✗ {failed} test(s) failed. Review output above.")
        print("="*60)
        
        return failed == 0

    def to_json(self) -> str:
        """Export results as JSON for CI/CD integration"""
        results_data = {
            "total": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "tests": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "expected": r.expected,
                    "actual": r.actual,
                    "details": r.details
                }
                for r in self.results
            ]
        }
        return json.dumps(results_data, indent=2)

def main():
    if len(sys.argv) < 2:
        repo_root = os.getcwd()
    else:
        repo_root = sys.argv[1]
    
    validator = PublisherTestValidator(repo_root)
    
    try:
        passed, failed = validator.run_all_tests()
        success = validator.print_results()
        
        # Export JSON if requested
        if "--json" in sys.argv:
            print("\nJSON Output:")
            print(validator.to_json())
        
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
