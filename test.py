#!/usr/bin/env python3
"""
Test script for LLDB Odin variable summaries.

This script:
1. Builds the Odin program using build.sh
2. Starts an LLDB debug session using CLI interface
3. Parses main.odin for expected test cases
4. Runs the debug session and validates variable summaries
"""

import re
import subprocess
import sys
from typing import List, Optional

class ANSI:
    RED       = '\033[91m'
    GREEN     = '\033[92m'
    YELLOW    = '\033[93m'
    BLUE      = '\033[94m'
    MAGENTA   = '\033[95m'
    CYAN      = '\033[96m'
    WHITE     = '\033[97m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'
    END       = '\033[0m'

def colored   (text: str, color: str) -> str: return f"{color}{text}{ANSI.END}"

def success   (text: str) -> str: return colored(text, ANSI.GREEN)
def error     (text: str) -> str: return colored(text, ANSI.RED)
def warning   (text: str) -> str: return colored(text, ANSI.YELLOW)
def info      (text: str) -> str: return colored(text, ANSI.BLUE)
def highlight (text: str) -> str: return colored(text, ANSI.BOLD)


class TestCase:
    variable_name: str
    command: str
    expected: str
    
    def __init__(self, variable_name: str, command: str, expected: str):
        self.variable_name = variable_name
        self.command       = command
        self.expected      = expected
    
    def __repr__(self):
        return f"TestCase({self.variable_name}, '{self.command}', '{self.expected}')"

def print_line(msg: str, width: int = 80, color: str = ANSI.CYAN) -> None:
    print(colored(msg.center(width, '-'), color))

def run_build_script() -> bool:
    print(info("Building Odin program..."))
    print_line("build.sh")
    try:
        # Run without capturing output so it shows in real-time
        subprocess.run(['bash', 'build.sh'], 
                       text=True, 
                       check=True)
        print_line("success", color=ANSI.GREEN)
        return True
    except subprocess.CalledProcessError as e:
        print_line(f"failed: {e.returncode}", color=ANSI.RED)
        return False


def parse_test_cases(filename: str) -> List[TestCase]:
    print(info(f"Parsing test cases from {filename}..."))
    
    test_cases = []
    
    with open(filename, 'r') as f:
        content = f.read()
    
    # Pattern to match:
    # variable := value
    # // (lldb) command
    # // expected_output
    pattern = r'(\w+)\s*:?=.*?\n\s*//\s*\(lldb\)\s*(.+?)\n\s*//\s*(.+?)(?=\n|$)'
    
    matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
    
    for match in matches:
        var_name = match[0].strip()
        command  = match[1].strip()
        expected = match[2].strip()
        
        test_cases.append(TestCase(var_name, command, expected))
    
    print(success(f"Found {len(test_cases)} test cases"))
    return test_cases


def normalize_pointer_values(text: str) -> str:
    """Replace actual pointer values with %PTR% for comparison."""
    # Match hexadecimal pointer values (0x followed by hex digits)
    return re.sub(r'0x[0-9a-fA-F]+', '%PTR%', text)


def compare_outputs(expected: str, actual: str) -> bool:
    expected_norm = normalize_pointer_values(expected.strip())
    actual_norm   = normalize_pointer_values(actual.strip())
    
    return expected_norm == actual_norm

def run_lldb(test_cases: List[TestCase]) -> str:

    cmd = ["lldb", "main.bin", "-o", "command script import odin.py", "-o", "b breakpoint", "-o", "r", "-o", "up"]

    for test_case in test_cases:
        cmd.append("-o")
        cmd.append(test_case.command)

    cmd.append("-o")
    cmd.append("quit")

    print(info("Running LLDB session:\n"), " ".join(cmd))
    print_line("lldb")
    
    timeout = 120
    process = None
    
    try:
        result = subprocess.run(cmd, 
                                capture_output=True, 
                                text=True, 
                                timeout=timeout)
        
        if result.returncode != 0:
            print(error(f"LLDB exited with code {result.returncode}"))
            print(error(f"Stderr: {result.stderr}"))

        # Use Popen to stream output in real-time while capturing it
        process = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   text=True,
                                   bufsize=1,  # Line buffered
                                   universal_newlines=True)
        
        output_lines = []
        
        # Read output line by line and display it while capturing
        if process.stdout:
            for line in process.stdout:
                print(line, end='')
                output_lines.append(line)
        
        return_code = process.wait(timeout=timeout)
        if return_code != 0:
            print(error(f"\nLLDB exited with code {return_code}"))
        
        return ''.join(output_lines)
    
    except subprocess.TimeoutExpired:
        if process:
            process.kill()
        print(error(f"\nLLDB session timed out after {timeout} seconds"))
        print(warning("This might be due to DWARF symbol indexing taking too long."))
        return ""
    except FileNotFoundError:
        print(error("Error: LLDB not found. Please install LLDB."))
        print(info("On Ubuntu: sudo apt-get install lldb"))
        return ""


def parse_lldb_output(output: str, test_cases: List[TestCase]) -> dict[str, str | None]:

    results: dict[str, str | None] = {}

    start_from = 0
    
    for test_case in test_cases:
        start_marker = f"(lldb) {test_case.command}\n"
        
        start_idx = output.find(start_marker, start_from) + len(start_marker)
        end_idx   = output.find("\n(lldb) ", start_idx)

        if start_idx == -1 or end_idx == -1:
            results[test_case.variable_name] = None
            continue

        start_from = end_idx+1
        
        test_output = output[start_idx:end_idx].strip()
        results[test_case.variable_name] = test_output
    
    return results


def run_test_case(test_case: TestCase, actual_output: Optional[str]) -> bool:
    """Validate a single test case result."""
    if actual_output is None:
        print(error(f"  FAIL: {test_case.variable_name} - No output captured"))
        return False
    
    if compare_outputs(test_case.expected, actual_output):
        print(success(f"  PASS: {test_case.variable_name}"))
        return True
    else:
        print(error(f"  FAIL: {test_case.variable_name}"))
        print(f"    {success('Expected:')} {highlight(test_case.expected)}")
        print(f"    {error('Actual:')}   {highlight(actual_output)}")
        return False


def check_dependencies() -> bool:
    required_checks = [
        (["odin", "version"],   "Odin compiler not found. Please install Odin."),
        (["lldb", "--version"], "LLDB debugger not found. Please install LLDB.\nOn Ubuntu: sudo apt-get install lldb"),
        (["bash", "--version"], "Bash shell not found.")
    ]
    
    for cmd, error_msg in required_checks:
        try:
            subprocess.run(cmd, 
                           capture_output=True, 
                           check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(error(f"Error: {error_msg}"))
            return False
    
    return True


def run_tests() -> bool:
    print(highlight("Starting LLDB Odin tests..."))
    
    # Check dependencies first
    if not check_dependencies():
        print(error("Dependency check failed, aborting tests"))
        return False
    
    if not run_build_script():
        print(error("Build failed, aborting tests"))
        return False
    
    test_cases = parse_test_cases("main.odin")
    if not test_cases:
        print(warning("No test cases found"))
        return False
    
    lldb_output = run_lldb(test_cases)
    
    print_line("end")
    
    results = parse_lldb_output(lldb_output, test_cases)
    
    failed = 0
    
    for test_case in test_cases:
        actual_output = results.get(test_case.variable_name)
        if not run_test_case(test_case, actual_output):
            failed += 1
    
    print(f"\n{highlight('Test Results:')}")

    if failed == 0:
        print(success("All tests passed! 🎉"))
        return True
    else:
        print(error(f"  Failed: {failed}/{len(test_cases)}"))
        return False


if __name__ == "__main__":
    test_success = run_tests()
    sys.exit(0 if test_success else 1)
