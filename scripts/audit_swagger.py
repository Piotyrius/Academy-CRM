#!/usr/bin/env python
"""
Swagger Documentation Audit Script
Scans all view files to identify endpoints missing @extend_schema decorators
and generates a comprehensive report.
"""
import os
import sys
import ast
import re
from pathlib import Path
from collections import defaultdict

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

os.chdir(project_root)

# View files to audit
VIEW_FILES = [
    'accounts/views.py',
    'catalog/views.py',
    'admissions/views.py',
    'payments/views.py',
    'attendance/views.py',
    'assessment/views.py',
    'certificates/views.py',
    'documents/views.py',
    'gallery/views.py',
    'storage/views.py',
    'reporting/views.py',
    'timekeeping/views.py',
    'subscriptions/views.py',
    'ops/views.py',
    'notifications/views.py',
]

def find_endpoints_in_file(file_path):
    """Parse a view file and find all endpoints."""
    endpoints = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return endpoints
    
    # Parse AST to find class definitions and methods
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return endpoints
    
    current_class = None
    current_viewset = None
    
    for node in ast.walk(tree):
        # Find ViewSet classes
        if isinstance(node, ast.ClassDef):
            # Check if it's a ViewSet or APIView
            bases = [base.id if isinstance(base, ast.Name) else '' for base in node.bases]
            is_viewset = any('ViewSet' in base or 'APIView' in base for base in bases)
            
            if is_viewset:
                current_class = node.name
                current_viewset = {
                    'name': node.name,
                    'file': str(file_path),
                    'actions': [],
                    'has_extend_schema': False,
                }
        # Find @action decorators
        elif isinstance(node, ast.FunctionDef):
            # Check for @action decorator
            has_action = False
            has_extend_schema = False
            action_methods = []
            
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Name) and decorator.func.id == 'action':
                        has_action = True
                        # Extract methods from action decorator
                        for keyword in decorator.keywords:
                            if keyword.arg == 'methods':
                                if isinstance(keyword.value, ast.List):
                                    action_methods = [elt.s if isinstance(elt, ast.Constant) else str(elt) for elt in keyword.value.elts]
                elif isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Name) and decorator.func.id == 'extend_schema':
                        has_extend_schema = True
                elif isinstance(decorator, ast.Name):
                    if decorator.id == 'extend_schema':
                        has_extend_schema = True
            
            if has_action and current_viewset:
                current_viewset['actions'].append({
                    'name': node.name,
                    'methods': action_methods or ['get'],
                    'has_extend_schema': has_extend_schema,
                    'line': node.lineno,
                })
            elif not has_action and current_viewset:
                # Check if it's a standard ViewSet method (list, create, retrieve, etc.)
                standard_methods = ['list', 'create', 'retrieve', 'update', 'partial_update', 'destroy']
                if node.name in standard_methods:
                    # Check if it has extend_schema
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                            if decorator.func.id == 'extend_schema':
                                has_extend_schema = True
                                break
                        elif isinstance(decorator, ast.Name) and decorator.id == 'extend_schema':
                            has_extend_schema = True
                            break
    
    # Also use regex to find @action and @extend_schema patterns
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    endpoints_found = []
    current_class_name = None
    in_class = False
    
    for i, line in enumerate(lines, 1):
        # Track class definitions
        class_match = re.search(r'class\s+(\w+).*ViewSet|class\s+(\w+).*APIView', line)
        if class_match:
            current_class_name = class_match.group(1) or class_match.group(2)
            in_class = True
            continue
        
        # Track @action decorators
        if '@action' in line or '@api_view' in line:
            # Find the method name on next few lines
            method_name = None
            method_line = None
            for j in range(i, min(i + 10, len(lines))):
                method_match = re.search(r'def\s+(\w+)\(', lines[j])
                if method_match:
                    method_name = method_match.group(1)
                    method_line = j + 1  # Line numbers are 1-indexed
                    break
            
            if method_name and method_line:
                # Check if @extend_schema exists before this method (look back up to 100 lines)
                # Some decorators can be quite far back, especially with multi-line schemas
                has_extend_schema = False
                # Look backwards from the @action line to catch decorators before @action
                for k in range(max(0, i - 100), i):
                    if '@extend_schema' in lines[k]:
                        has_extend_schema = True
                        break
                # Also check between @action and method definition (decorators can be between them)
                if not has_extend_schema:
                    for k in range(i, min(method_line, len(lines))):
                        if '@extend_schema' in lines[k]:
                            has_extend_schema = True
                            break
                
                endpoints_found.append({
                    'class': current_class_name or 'Unknown',
                    'method': method_name,
                    'line': i,
                    'has_extend_schema': has_extend_schema,
                    'type': 'action' if '@action' in line else 'api_view',
                })
    
    return endpoints_found

def main():
    """Main audit function."""
    print("=" * 80)
    print("SWAGGER DOCUMENTATION AUDIT")
    print("=" * 80)
    print()
    
    all_endpoints = defaultdict(list)
    missing_docs = []
    file_upload_endpoints = []
    
    for view_file in VIEW_FILES:
        file_path = project_root / view_file
        if not file_path.exists():
            continue
        
        print(f"Scanning {view_file}...")
        endpoints = find_endpoints_in_file(file_path)
        
        for endpoint in endpoints:
            all_endpoints[view_file].append(endpoint)
            
            if not endpoint['has_extend_schema']:
                missing_docs.append({
                    'file': view_file,
                    'class': endpoint['class'],
                    'method': endpoint['method'],
                    'line': endpoint['line'],
                    'type': endpoint['type'],
                })
            
            # Check for file upload endpoints
            if 'upload' in endpoint['method'].lower() or 'file' in endpoint['method'].lower():
                file_upload_endpoints.append({
                    'file': view_file,
                    'class': endpoint['class'],
                    'method': endpoint['method'],
                    'line': endpoint['line'],
                    'has_extend_schema': endpoint['has_extend_schema'],
                })
    
    print()
    print("=" * 80)
    print("AUDIT RESULTS")
    print("=" * 80)
    print()
    
    print(f"Total endpoints found: {sum(len(eps) for eps in all_endpoints.values())}")
    print(f"Endpoints missing @extend_schema: {len(missing_docs)}")
    print(f"File upload endpoints: {len(file_upload_endpoints)}")
    print()
    
    if missing_docs:
        print("MISSING DOCUMENTATION:")
        print("-" * 80)
        for item in missing_docs:
            print(f"  {item['file']}:{item['line']} - {item['class']}.{item['method']} ({item['type']})")
        print()
    
    if file_upload_endpoints:
        print("FILE UPLOAD ENDPOINTS:")
        print("-" * 80)
        for item in file_upload_endpoints:
            status = "✅ Documented" if item['has_extend_schema'] else "❌ Missing docs"
            print(f"  {status} - {item['file']}:{item['line']} - {item['class']}.{item['method']}")
        print()
    
    # Group by file
    print("BREAKDOWN BY FILE:")
    print("-" * 80)
    for view_file, endpoints in sorted(all_endpoints.items()):
        documented = sum(1 for ep in endpoints if ep.get('has_extend_schema', False))
        missing = len(endpoints) - documented
        print(f"  {view_file}: {len(endpoints)} endpoints ({documented} documented, {missing} missing)")
    
    print()
    print("=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()

