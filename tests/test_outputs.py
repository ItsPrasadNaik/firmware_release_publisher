#!/usr/bin/env python3
"""
Pytest-based validator for Firmware Release Publisher
Tests the reference solution against grading criteria with proper pytest assertions
"""

import subprocess
from pathlib import Path

# Get repo root (tests/ directory parent)
REPO_ROOT = Path(__file__).parent.parent
ENVIRONMENT_DIR = REPO_ROOT / "environment"
SOLUTION_DIR = REPO_ROOT / "solution"
GOLDEN_FILE = ENVIRONMENT_DIR / "reports" / "publications.expected.txt"
MANIFEST_FILE = ENVIRONMENT_DIR / "fixtures" / "build_manifest.csv"


class TestFileStructure:
    """Verify repository structure"""
    
    def test_solution_exists(self):
        """Test that reference solution exists"""
        solution_file = SOLUTION_DIR / "release-publisher.mjs"
        assert solution_file.exists(), f"Solution file not found: {solution_file}"
    
    def test_golden_output_exists(self):
        """Test that golden reference file exists"""
        assert GOLDEN_FILE.exists(), f"Golden file not found: {GOLDEN_FILE}"
    
    def test_manifest_exists(self):
        """Test that build manifest exists"""
        assert MANIFEST_FILE.exists(), f"Manifest file not found: {MANIFEST_FILE}"
    
    def test_docker_configured(self):
        """Test that Dockerfile exists"""
        dockerfile = ENVIRONMENT_DIR / "Dockerfile"
        assert dockerfile.exists(), f"Dockerfile not found: {dockerfile}"
    
    def test_package_json_exists(self):
        """Test that package.json exists"""
        package_file = ENVIRONMENT_DIR / "package.json"
        assert package_file.exists(), f"package.json not found: {package_file}"


class TestSyntaxValidation:
    """Verify code syntax"""
    
    def test_solution_syntax_valid(self):
        """Test that solution.mjs has valid Node.js syntax"""
        solution_file = SOLUTION_DIR / "release-publisher.mjs"
        result = subprocess.run(
            ["node", "--check", str(solution_file)],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert result.returncode == 0, f"Syntax error in solution: {result.stderr}"


class TestManifestData:
    """Verify input data"""
    
    def test_manifest_has_40_records(self):
        """Test that build manifest has exactly 40 records"""
        lines = MANIFEST_FILE.read_text().strip().split('\n')
        record_count = len(lines) - 1  # Subtract header
        assert record_count == 40, f"Expected 40 records, got {record_count}"
    
    def test_manifest_has_required_columns(self):
        """Test that manifest has required CSV columns"""
        lines = MANIFEST_FILE.read_text().strip().split('\n')
        header = lines[0]
        required_columns = [
            "entry_id", "bundle_id", "component_id", "version", 
            "size_bytes", "record_type", "supersedes_id", "recorded_at"
        ]
        for column in required_columns:
            assert column in header, f"Missing required column: {column}"


class TestGoldenOutput:
    """Verify expected output format"""
    
    def test_golden_output_has_6_lines(self):
        """Test that golden output has exactly 6 lines (3 bundles × 2)"""
        golden = GOLDEN_FILE.read_text().strip()
        lines = [line.strip() for line in golden.split('\n') if line.strip()]
        assert len(lines) == 6, f"Expected 6 lines, got {len(lines)}"
    
    def test_golden_output_has_bundle_keyword(self):
        """Test that all output lines contain BUNDLE keyword"""
        golden = GOLDEN_FILE.read_text().strip()
        lines = [line.strip() for line in golden.split('\n') if line.strip()]
        for i, line in enumerate(lines):
            assert "BUNDLE" in line, f"Line {i+1} missing BUNDLE keyword: {line}"
    
    def test_golden_has_three_bundles(self):
        """Test that output contains exactly 3 bundles (BND-101, BND-102, BND-103)"""
        golden = GOLDEN_FILE.read_text().strip()
        assert "BND-101" in golden, "Missing BND-101 in golden output"
        assert "BND-102" in golden, "Missing BND-102 in golden output"
        assert "BND-103" in golden, "Missing BND-103 in golden output"
    
    def test_golden_output_line_format(self):
        """Test that output lines follow expected format"""
        golden = GOLDEN_FILE.read_text().strip()
        lines = [line.strip() for line in golden.split('\n') if line.strip()]
        
        # Lines should alternate: SIGNED, PUBLISHED, SIGNED, PUBLISHED, ...
        for i, line in enumerate(lines):
            if i % 2 == 0:
                # Even lines should have SIGNED
                assert "SIGNED" in line, f"Line {i+1} should contain SIGNED: {line}"
                assert "KEY=" in line, f"Line {i+1} should contain KEY=: {line}"
            else:
                # Odd lines should have PUBLISHED
                assert "PUBLISHED" in line, f"Line {i+1} should contain PUBLISHED: {line}"
                assert "RECEIPT=" in line, f"Line {i+1} should contain RECEIPT=: {line}"
                assert "TOKEN=" in line, f"Line {i+1} should contain TOKEN=: {line}"
                assert "STATUS=" in line, f"Line {i+1} should contain STATUS=: {line}"
    
    def test_golden_output_deterministic_order(self):
        """Test that bundles appear in ascending order"""
        golden = GOLDEN_FILE.read_text().strip()
        lines = [line.strip() for line in golden.split('\n') if line.strip()]
        
        bundle_order = []
        for line in lines:
            if "BUNDLE" in line:
                for bundle_id in ["BND-101", "BND-102", "BND-103"]:
                    if bundle_id in line:
                        bundle_order.append(bundle_id)
                        break
        
        # Should appear in order: BND-101 (2 times), BND-102 (2 times), BND-103 (2 times)
        expected_order = ["BND-101", "BND-101", "BND-102", "BND-102", "BND-103", "BND-103"]
        assert bundle_order == expected_order, f"Bundle order wrong. Expected {expected_order}, got {bundle_order}"


class TestProofA:
    """Verify Proof A: environment/publisher/ is empty (reference solution not in solver location)"""
    
    def test_publisher_directory_empty(self):
        """Test that environment/publisher/ contains no implementation files"""
        publisher_dir = ENVIRONMENT_DIR / "publisher"
        
        # Should exist (directory)
        assert publisher_dir.exists(), f"publisher/ directory should exist at {publisher_dir}"
        
        # Should be empty (or contain only dotfiles)
        mjs_files = list(publisher_dir.glob("*.mjs"))
        js_files = list(publisher_dir.glob("*.js"))
        
        assert len(mjs_files) == 0, f"publisher/ should not contain .mjs files, found: {mjs_files}"
        assert len(js_files) == 0, f"publisher/ should not contain .js files, found: {js_files}"


class TestProofB:
    """Verify Proof B: solution/ contains reference implementation"""
    
    def test_solution_directory_has_implementation(self):
        """Test that solution/ contains the reference implementation"""
        solution_file = SOLUTION_DIR / "release-publisher.mjs"
        assert solution_file.exists(), f"Solution should contain release-publisher.mjs at {solution_file}"
        
        # Should have meaningful content (more than 1KB)
        size = solution_file.stat().st_size
        assert size > 1000, f"Solution file is too small ({size} bytes), likely empty or placeholder"
    
    def test_solution_imports_required_modules(self):
        """Test that solution imports duckdb, fs, execSync, http, etc."""
        solution_file = SOLUTION_DIR / "release-publisher.mjs"
        content = solution_file.read_text()
        
        required_imports = [
            "duckdb",
            "readFileSync",
            "execSync",
            "http"
        ]
        
        for import_name in required_imports:
            assert import_name in content, f"Solution should use {import_name}"


class TestTaskAuthoring:
    """Verify all 6 required authoring components (per Handbook Section 2)"""
    
    def test_instruction_md_exists_and_substantial(self):
        """Test that instruction.md exists and contains substantial content"""
        instruction_file = REPO_ROOT / "instruction.md"
        assert instruction_file.exists(), "instruction.md should exist in repo root"
        content = instruction_file.read_text()
        assert len(content) > 1000, f"instruction.md too short ({len(content)} bytes), should be >1000"
    
    def test_task_toml_valid(self):
        """Test that task.toml exists and contains metadata"""
        task_file = REPO_ROOT / "task.toml"
        assert task_file.exists(), "task.toml should exist in repo root"
        content = task_file.read_text()
        assert "title" in content, "task.toml should contain task title"
        assert "[task]" in content or "[metadata]" in content, "task.toml should have TOML structure"
    
    def test_author_notes_exists_and_substantial(self):
        """Test that AUTHOR_NOTES.md exists and contains detailed guidance"""
        notes_file = REPO_ROOT / "AUTHOR_NOTES.md"
        assert notes_file.exists(), "AUTHOR_NOTES.md should exist in repo root"
        content = notes_file.read_text()
        assert len(content) > 1000, f"AUTHOR_NOTES.md too short ({len(content)} bytes), should be >1000"
    
    def test_tests_directory_has_validators(self):
        """Test that tests/ contains proper validators"""
        tests_dir = REPO_ROOT / "tests"
        assert tests_dir.exists(), "tests/ directory should exist"
        assert (tests_dir / "test.sh").exists(), "tests/test.sh should exist"
        assert (tests_dir / "test_outputs.py").exists(), "tests/test_outputs.py should exist"
    
    def test_solution_directory_exists(self):
        """Test that solution/ directory exists"""
        solution_dir = REPO_ROOT / "solution"
        assert solution_dir.exists(), "solution/ directory should exist in repo root"
    
    def test_environment_directory_complete(self):
        """Test that environment/ is complete with all required subdirectories"""
        env_dir = REPO_ROOT / "environment"
        assert env_dir.exists(), "environment/ directory should exist"
        required_subdirs = ["fixtures", "keys", "publisher", "reports"]
        for subdir in required_subdirs:
            subdir_path = env_dir / subdir
            assert subdir_path.exists() and subdir_path.is_dir(), f"environment/{subdir}/ should exist"


if __name__ == "__main__":
    print("Run tests with: pytest tests/test_outputs.py -v")
    print("Or for verbose output: pytest tests/test_outputs.py -vv")
