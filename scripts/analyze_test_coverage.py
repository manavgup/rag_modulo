#!/usr/bin/env python3
"""Analyze test coverage and complexity before converting to atomic tests."""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set
import argparse


class TestAnalyzer:
    """Analyze test files to determine coverage and complexity."""

    def __init__(self, test_file: str):
        self.test_file = test_file
        self.source_file = self._find_source_file()
        self.test_ast = self._parse_file(test_file)
        self.source_ast = self._parse_file(self.source_file) if self.source_file else None

    def _find_source_file(self) -> str:
        """Find the corresponding source file for a test file."""
        # Map test file patterns to source files
        test_patterns = {
            'test_llm_parameters_service.py': 'rag_solution/services/llm_parameters_service.py',
            'test_llm_provider_service.py': 'rag_solution/services/llm_provider_service.py',
            'test_llm_model_service.py': 'rag_solution/services/llm_model_service.py',
            'test_collection_service.py': 'rag_solution/services/collection_service.py',
            'test_user_service.py': 'rag_solution/services/user_service.py',
            'test_team_service.py': 'rag_solution/services/team_service.py',
            'test_search_service.py': 'rag_solution/services/search_service.py',
            'test_pipeline_service.py': 'rag_solution/services/pipeline_service.py',
            'test_question_service.py': 'rag_solution/services/question_service.py',
            'test_prompt_template_service.py': 'rag_solution/services/prompt_template_service.py',
        }

        test_name = os.path.basename(self.test_file)
        return test_patterns.get(test_name, None)

    def _parse_file(self, file_path: str) -> ast.AST:
        """Parse a Python file and return its AST."""
        if not file_path or not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return ast.parse(content)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def analyze_test_complexity(self) -> Dict:
        """Analyze test file complexity and coverage indicators."""
        if not self.test_ast:
            return {"error": "Could not parse test file"}

        analysis = {
            "test_file": self.test_file,
            "source_file": self.source_file,
            "test_functions": [],
            "imports": [],
            "fixtures": [],
            "external_dependencies": [],
            "test_complexity_score": 0,
            "coverage_indicators": [],
            "recommendation": ""
        }

        # Analyze test functions
        for node in ast.walk(self.test_ast):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                test_func = self._analyze_test_function(node)
                analysis["test_functions"].append(test_func)
                analysis["test_complexity_score"] += test_func["complexity_score"]

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    analysis["imports"].append(alias.name)
                    if self._is_external_dependency(alias.name):
                        analysis["external_dependencies"].append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    analysis["imports"].append(full_name)
                    if self._is_external_dependency(full_name):
                        analysis["external_dependencies"].append(full_name)

            elif isinstance(node, ast.FunctionDef) and 'fixture' in node.name.lower():
                analysis["fixtures"].append(node.name)

        # Analyze source file if available
        if self.source_ast:
            source_analysis = self._analyze_source_file()
            analysis.update(source_analysis)

        # Generate recommendation
        analysis["recommendation"] = self._generate_recommendation(analysis)

        return analysis

    def _analyze_test_function(self, node: ast.FunctionDef) -> Dict:
        """Analyze a single test function."""
        complexity_score = 0
        coverage_indicators = []

        # Count lines of code
        lines = node.end_lineno - node.lineno if node.end_lineno else 1
        complexity_score += lines * 0.1

        # Count assertions
        assertions = sum(1 for n in ast.walk(node) if isinstance(n, ast.Assert))
        complexity_score += assertions * 0.5

        # Count external calls
        external_calls = 0
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Attribute):
                    if n.func.attr in ['create', 'update', 'delete', 'get', 'find']:
                        external_calls += 1
                        coverage_indicators.append(f"Service call: {n.func.attr}")
                elif isinstance(n.func, ast.Name):
                    if n.func.id in ['patch', 'mock', 'MagicMock']:
                        complexity_score += 2  # Mocking adds complexity

        complexity_score += external_calls * 1.0

        # Check for database/service operations
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Attribute):
                    if any(op in n.func.attr for op in ['create', 'update', 'delete', 'save', 'commit']):
                        coverage_indicators.append("Database operation")
                    elif any(op in n.func.attr for op in ['get', 'find', 'query', 'search']):
                        coverage_indicators.append("Data retrieval")

        return {
            "name": node.name,
            "lines": lines,
            "assertions": assertions,
            "external_calls": external_calls,
            "complexity_score": complexity_score,
            "coverage_indicators": coverage_indicators
        }

    def _analyze_source_file(self) -> Dict:
        """Analyze the source file being tested."""
        if not self.source_ast:
            return {}

        source_analysis = {
            "source_lines": 0,
            "source_functions": 0,
            "source_classes": 0,
            "source_methods": 0,
            "estimated_coverage": 0
        }

        for node in ast.walk(self.source_ast):
            if isinstance(node, ast.FunctionDef):
                source_analysis["source_functions"] += 1
                if node.lineno and node.end_lineno:
                    source_analysis["source_lines"] += node.end_lineno - node.lineno
            elif isinstance(node, ast.ClassDef):
                source_analysis["source_classes"] += 1
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        source_analysis["source_methods"] += 1

        # Estimate coverage based on test complexity vs source complexity
        if source_analysis["source_lines"] > 0:
            test_complexity = sum(func["complexity_score"] for func in self.test_functions)
            source_complexity = source_analysis["source_lines"] / 10  # Rough estimate
            source_analysis["estimated_coverage"] = min(100, (test_complexity / source_complexity) * 100)

        return source_analysis

    def _is_external_dependency(self, module_name: str) -> bool:
        """Check if a module is an external dependency."""
        external_patterns = [
            'sqlalchemy', 'pytest', 'fastapi', 'pydantic', 'requests',
            'httpx', 'aiohttp', 'redis', 'celery', 'django', 'flask',
            'numpy', 'pandas', 'scikit-learn', 'tensorflow', 'torch'
        ]
        return any(pattern in module_name.lower() for pattern in external_patterns)

    def _generate_recommendation(self, analysis: Dict) -> str:
        """Generate a recommendation based on analysis."""
        complexity_score = analysis["test_complexity_score"]
        external_deps = len(analysis["external_dependencies"])
        test_functions = len(analysis["test_functions"])

        if complexity_score < 5 and external_deps < 3:
            return "✅ GOOD CANDIDATE for atomic conversion - low complexity, minimal external dependencies"
        elif complexity_score < 15 and external_deps < 5:
            return "⚠️  MODERATE CANDIDATE - some complexity but manageable for atomic conversion"
        elif complexity_score < 30:
            return "❌ HIGH COMPLEXITY - consider breaking into smaller atomic tests"
        else:
            return "🚫 VERY HIGH COMPLEXITY - likely integration test, keep as-is or refactor significantly"

    def print_analysis(self):
        """Print a formatted analysis report."""
        analysis = self.analyze_test_complexity()

        print(f"\n{'='*80}")
        print(f"TEST COVERAGE ANALYSIS: {os.path.basename(analysis['test_file'])}")
        print(f"{'='*80}")

        print(f"📁 Test File: {analysis['test_file']}")
        print(f"📁 Source File: {analysis['source_file'] or 'Not found'}")
        print(f"🧪 Test Functions: {len(analysis['test_functions'])}")
        print(f"🔧 Fixtures: {len(analysis['fixtures'])}")
        print(f"📦 External Dependencies: {len(analysis['external_dependencies'])}")
        print(f"📊 Complexity Score: {analysis['test_complexity_score']:.1f}")

        if analysis.get('source_lines'):
            print(f"📏 Source Lines: {analysis['source_lines']}")
            print(f"📏 Source Functions: {analysis['source_functions']}")
            print(f"📏 Source Classes: {analysis['source_classes']}")
            print(f"📏 Source Methods: {analysis['source_methods']}")
            print(f"📈 Estimated Coverage: {analysis.get('estimated_coverage', 0):.1f}%")

        print(f"\n🎯 RECOMMENDATION: {analysis['recommendation']}")

        if analysis['test_functions']:
            print(f"\n📋 TEST FUNCTION BREAKDOWN:")
            for func in analysis['test_functions']:
                print(f"  • {func['name']}: {func['lines']} lines, {func['assertions']} assertions, "
                      f"complexity: {func['complexity_score']:.1f}")
                if func['coverage_indicators']:
                    print(f"    Coverage indicators: {', '.join(func['coverage_indicators'])}")

        if analysis['external_dependencies']:
            print(f"\n🔗 EXTERNAL DEPENDENCIES:")
            for dep in analysis['external_dependencies']:
                print(f"  • {dep}")

        print(f"\n{'='*80}")


def main():
    parser = argparse.ArgumentParser(description='Analyze test coverage and complexity')
    parser.add_argument('test_file', help='Path to test file to analyze')
    parser.add_argument('--backend-dir', default='backend', help='Backend directory path')

    args = parser.parse_args()

    # Adjust path if needed
    test_file = args.test_file
    if not os.path.isabs(test_file):
        test_file = os.path.join(args.backend_dir, test_file)

    if not os.path.exists(test_file):
        print(f"Error: Test file {test_file} not found")
        return 1

    analyzer = TestAnalyzer(test_file)
    analyzer.print_analysis()

    return 0


if __name__ == "__main__":
    exit(main())
