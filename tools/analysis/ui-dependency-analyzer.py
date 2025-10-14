#!/usr/bin/env python3
"""
UI Dependency Analyzer

This tool performs comprehensive dependency analysis on the monolithic ui.py file
to identify function dependencies, coupling patterns, and extraction complexity
for the Internal Assistant UI refactoring project.

The analyzer uses AST (Abstract Syntax Tree) parsing to create:
- Function dependency maps
- Variable usage patterns
- Gradio component interaction tracking
- Cross-function coupling analysis
- Extraction risk assessment

Author: Internal Assistant Team
Version: 1.0.0
"""

import ast
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class FunctionInfo:
    """Information about a function in the codebase."""

    name: str
    line_start: int
    line_end: int
    calls: Set[str]
    variables_read: Set[str]
    variables_written: Set[str]
    gradio_components: Set[str]
    complexity_score: int = 0


@dataclass
class DependencyEdge:
    """Represents a dependency relationship between functions."""

    source: str
    target: str
    dependency_type: str  # 'function_call', 'variable_shared', 'gradio_component'
    strength: int  # 1-10 scale


class UIDependencyAnalyzer:
    """
    Comprehensive analyzer for UI dependencies and coupling patterns.
    """

    def __init__(self, ui_file_path: str):
        """
        Initialize the analyzer with the UI file path.

        Args:
            ui_file_path: Path to the ui.py file to analyze
        """
        self.ui_file_path = Path(ui_file_path)
        self.tree = None
        self.functions: Dict[str, FunctionInfo] = {}
        self.dependencies: List[DependencyEdge] = []
        self.global_variables: Set[str] = set()
        self.gradio_events: Dict[str, List[str]] = defaultdict(list)

    def analyze(self) -> Dict[str, Any]:
        """
        Perform complete dependency analysis.

        Returns:
            Dictionary containing all analysis results
        """
        logger.info(f"Starting dependency analysis of {self.ui_file_path}")

        # Parse the AST
        self._parse_ast()

        # Extract function information
        self._extract_functions()

        # Analyze dependencies
        self._analyze_dependencies()

        # Calculate coupling scores
        self._calculate_coupling_scores()

        # Generate analysis report
        results = self._generate_report()

        logger.info("Dependency analysis completed")
        return results

    def _parse_ast(self):
        """Parse the UI file into an AST."""
        try:
            with open(self.ui_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.tree = ast.parse(content)
            logger.info("AST parsing successful")
        except Exception as e:
            logger.error(f"Failed to parse {self.ui_file_path}: {e}")
            raise

    def _extract_functions(self):
        """Extract all function definitions and their basic info."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                func_info = FunctionInfo(
                    name=node.name,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    calls=set(),
                    variables_read=set(),
                    variables_written=set(),
                    gradio_components=set(),
                )

                # Analyze function body
                self._analyze_function_body(node, func_info)

                self.functions[node.name] = func_info

        logger.info(f"Extracted {len(self.functions)} functions")

    def _analyze_function_body(self, node: ast.FunctionDef, func_info: FunctionInfo):
        """Analyze the body of a function for dependencies."""
        for child in ast.walk(node):
            # Function calls
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    func_info.calls.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    # Handle method calls like gr.Button()
                    if isinstance(child.func.value, ast.Name):
                        if child.func.value.id == "gr":
                            func_info.gradio_components.add(child.func.attr)
                        else:
                            func_info.calls.add(
                                f"{child.func.value.id}.{child.func.attr}"
                            )

            # Variable assignments
            elif isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        func_info.variables_written.add(target.id)

            # Variable reads
            elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                func_info.variables_read.add(child.id)

    def _analyze_dependencies(self):
        """Analyze dependencies between functions."""
        for func_name, func_info in self.functions.items():
            # Function call dependencies
            for called_func in func_info.calls:
                if called_func in self.functions:
                    edge = DependencyEdge(
                        source=func_name,
                        target=called_func,
                        dependency_type="function_call",
                        strength=5,
                    )
                    self.dependencies.append(edge)

            # Variable sharing dependencies
            for other_func_name, other_func_info in self.functions.items():
                if func_name != other_func_name:
                    shared_vars = func_info.variables_read.intersection(
                        other_func_info.variables_written
                    )
                    shared_vars.update(
                        func_info.variables_written.intersection(
                            other_func_info.variables_read
                        )
                    )

                    if shared_vars:
                        strength = min(len(shared_vars) * 2, 10)
                        edge = DependencyEdge(
                            source=func_name,
                            target=other_func_name,
                            dependency_type="variable_shared",
                            strength=strength,
                        )
                        self.dependencies.append(edge)

            # Gradio component dependencies
            for other_func_name, other_func_info in self.functions.items():
                if func_name != other_func_name:
                    shared_components = func_info.gradio_components.intersection(
                        other_func_info.gradio_components
                    )
                    if shared_components:
                        strength = min(len(shared_components) * 3, 10)
                        edge = DependencyEdge(
                            source=func_name,
                            target=other_func_name,
                            dependency_type="gradio_component",
                            strength=strength,
                        )
                        self.dependencies.append(edge)

    def _calculate_coupling_scores(self):
        """Calculate coupling scores for each function."""
        coupling_scores = defaultdict(int)

        for edge in self.dependencies:
            coupling_scores[edge.source] += edge.strength
            coupling_scores[edge.target] += edge.strength

        for func_name, func_info in self.functions.items():
            func_info.complexity_score = coupling_scores.get(func_name, 0)

    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        # High coupling functions (score > 7)
        high_coupling = {
            name: info
            for name, info in self.functions.items()
            if info.complexity_score > 7
        }

        # Function size analysis
        large_functions = {
            name: info
            for name, info in self.functions.items()
            if (info.line_end - info.line_start) > 100
        }

        # Gradio component usage
        gradio_usage = Counter()
        for func_info in self.functions.values():
            gradio_usage.update(func_info.gradio_components)

        # Dependency graph data
        dependency_graph = {
            "nodes": [
                {
                    "id": name,
                    "label": name,
                    "size": info.line_end - info.line_start,
                    "coupling_score": info.complexity_score,
                    "gradio_components": list(info.gradio_components),
                }
                for name, info in self.functions.items()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.dependency_type,
                    "strength": edge.strength,
                }
                for edge in self.dependencies
            ],
        }

        # Extraction risk assessment
        extraction_risks = {}
        for func_name, func_info in self.functions.items():
            risk_level = "LOW"
            if func_info.complexity_score > 15:
                risk_level = "HIGH"
            elif func_info.complexity_score > 7:
                risk_level = "MEDIUM"

            extraction_risks[func_name] = {
                "risk_level": risk_level,
                "coupling_score": func_info.complexity_score,
                "line_count": func_info.line_end - func_info.line_start,
                "dependencies": len(
                    [e for e in self.dependencies if e.source == func_name]
                ),
                "gradio_components": len(func_info.gradio_components),
            }

        return {
            "summary": {
                "total_functions": len(self.functions),
                "total_dependencies": len(self.dependencies),
                "high_coupling_functions": len(high_coupling),
                "large_functions": len(large_functions),
                "gradio_components_used": len(gradio_usage),
            },
            "high_coupling_functions": {
                name: {
                    "coupling_score": info.complexity_score,
                    "line_range": f"{info.line_start}-{info.line_end}",
                    "dependencies": len(
                        [e for e in self.dependencies if e.source == name]
                    ),
                }
                for name, info in high_coupling.items()
            },
            "large_functions": {
                name: {
                    "line_count": info.line_end - info.line_start,
                    "coupling_score": info.complexity_score,
                    "line_range": f"{info.line_start}-{info.line_end}",
                }
                for name, info in large_functions.items()
            },
            "gradio_component_usage": dict(gradio_usage.most_common()),
            "dependency_graph": dependency_graph,
            "extraction_risks": extraction_risks,
            "recommendations": self._generate_recommendations(
                high_coupling, large_functions
            ),
        }

    def _generate_recommendations(
        self,
        high_coupling: Dict[str, FunctionInfo],
        large_functions: Dict[str, FunctionInfo],
    ) -> List[str]:
        """Generate extraction recommendations based on analysis."""
        recommendations = []

        if high_coupling:
            recommendations.append(
                f"[HIGH] HIGH PRIORITY: {len(high_coupling)} functions have high coupling scores "
                f"(>7). These should be extracted together or refactored before extraction."
            )

        if large_functions:
            recommendations.append(
                f"[SIZE] SIZE WARNING: {len(large_functions)} functions exceed 100 lines. "
                f"Consider breaking these into smaller functions before extraction."
            )

        # Check for _build_ui_blocks specifically
        if "_build_ui_blocks" in self.functions:
            build_func = self.functions["_build_ui_blocks"]
            line_count = build_func.line_end - build_func.line_start
            recommendations.append(
                f"[MAIN] MAIN TARGET: _build_ui_blocks ({line_count} lines, "
                f"coupling score: {build_func.complexity_score}) is the primary "
                f"refactoring target."
            )

        return recommendations


def main():
    """Main entry point for the dependency analyzer."""
    ui_file_path = "internal_assistant/ui/ui.py"

    if not Path(ui_file_path).exists():
        logger.error(f"UI file not found: {ui_file_path}")
        sys.exit(1)

    # Create analyzer and run analysis
    analyzer = UIDependencyAnalyzer(ui_file_path)
    results = analyzer.analyze()

    # Save results to JSON file
    output_file = "tools/analysis/dependency-analysis-results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    # Print summary to console
    print("\n" + "=" * 60)
    print("UI DEPENDENCY ANALYSIS SUMMARY")
    print("=" * 60)

    summary = results["summary"]
    print(f"[DATA] Total Functions: {summary['total_functions']}")
    print(f"[DEPS] Total Dependencies: {summary['total_dependencies']}")
    print(f"[WARN] High Coupling Functions: {summary['high_coupling_functions']}")
    print(f"[SIZE] Large Functions (>100 lines): {summary['large_functions']}")
    print(f"[UI] Gradio Components Used: {summary['gradio_components_used']}")

    print("\n[RECS] RECOMMENDATIONS:")
    for rec in results["recommendations"]:
        print(f"   {rec}")

    print(f"\n[FILE] Detailed results saved to: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
