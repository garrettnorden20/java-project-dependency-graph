import re
import json
import sys
from pathlib import Path
from collections import defaultdict

PACKAGE_RE = re.compile(r'^\s*package\s+([\w\.]+);')
IMPORT_RE = re.compile(r'^\s*import\s+([\w\.]+);')

IGNORED_IMPORT_PREFIXES = (
    'java.',
    'javax.',
    'jakarta.',
    'org.apache.',
    'org.springframework.'
)

def is_internal_import(import_str):
    return not import_str.startswith(IGNORED_IMPORT_PREFIXES)

def extract_package_and_imports(file_path):
    package = None
    imports = set()
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not package:
                match = PACKAGE_RE.match(line)
                if match:
                    package = match.group(1)
            match = IMPORT_RE.match(line)
            if match:
                imports.add(match.group(1))
    return package, imports

def build_java_dependency_graph(project_root: Path):
    java_files = list(project_root.rglob('*.java'))
    file_to_package = {}
    package_to_file = {}

    # First pass: map packages to files
    for file in java_files:
        pkg, _ = extract_package_and_imports(file)
        if pkg:
            rel_path = str(file.relative_to(project_root))
            file_to_package[rel_path] = pkg
            package_to_file[pkg] = rel_path

    # Second pass: build graph
    graph = defaultdict(set)
    for file in java_files:
        rel_path = str(file.relative_to(project_root))
        pkg, imports = extract_package_and_imports(file)
        for imp in imports:
            if not is_internal_import(imp):
                continue  # skip external libs
            imp_root = imp.split('.')[0]  # First segment
            if imp in package_to_file:
                graph[rel_path].add(package_to_file[imp])
            elif imp_root in package_to_file:
                graph[rel_path].add(package_to_file[imp_root])
            else:
                # External lib or unresolved
                graph[rel_path].add(imp)
    return graph

def export_graph_to_json(graph, output_path='graph.json'):
    nodes = {name for name in graph.keys()}
    links = []
    for source, targets in graph.items():
        for target in targets:
            links.append({"source": source, "target": target})
            nodes.add(target)
    json_data = {
        "nodes": [{"id": name} for name in nodes],
        "links": links
    }
    with open(output_path, 'w') as f:
        json.dump(json_data, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Error: You must provide the path to the Java project directory.")
        print("Usage: main.py /path/to/my_proj")
        sys.exit(1)

    project_path = Path(sys.argv[1]).resolve()

    print(f"Analyzing Java files in: {project_path}")
    graph = build_java_dependency_graph(project_path)
    export_graph_to_json(graph, "graph.json")
    print("Java dependency graph saved as graph.json")
