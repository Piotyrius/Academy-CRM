"""
Script to check for duplicate URLs and issues.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academy_crm.settings.dev')
django.setup()

from django.urls import get_resolver
from collections import defaultdict

def collect_urls(urlpatterns, prefix='', url_map=None):
    """Collect all URL patterns recursively."""
    if url_map is None:
        url_map = defaultdict(list)
    
    for pattern in urlpatterns:
        if hasattr(pattern, 'url_patterns'):
            # This is an include
            new_prefix = prefix + str(pattern.pattern)
            collect_urls(pattern.url_patterns, new_prefix, url_map)
        elif hasattr(pattern, 'pattern'):
            # This is a path
            full_path = prefix + str(pattern.pattern)
            # Normalize the path
            full_path = full_path.replace('^', '').replace('$', '')
            if full_path:
                url_map[full_path].append({
                    'pattern': str(pattern.pattern),
                    'name': getattr(pattern, 'name', None),
                    'callback': str(getattr(pattern, 'callback', 'Unknown'))
                })
    
    return url_map

# Get all URL patterns
resolver = get_resolver()
url_map = collect_urls(resolver.url_patterns)

# Check for duplicates
duplicates = {path: info for path, info in url_map.items() if len(info) > 1}

print("=" * 80)
print("URL AUDIT REPORT")
print("=" * 80)
print(f"\nTotal unique URL patterns: {len(url_map)}")
print(f"Total URL registrations: {sum(len(info) for info in url_map.values())}")

if duplicates:
    print(f"\n⚠️  FOUND {len(duplicates)} DUPLICATE URL PATTERNS:")
    print("=" * 80)
    for path, info_list in duplicates.items():
        print(f"\nPath: {path}")
        for i, info in enumerate(info_list, 1):
            print(f"  {i}. Pattern: {info['pattern']}")
            print(f"     Name: {info['name']}")
            print(f"     Callback: {info['callback']}")
else:
    print("\n✅ No duplicate URL patterns found!")

# Check for common issues
print("\n" + "=" * 80)
print("ISSUE CHECKS")
print("=" * 80)

issues = []

# Check for missing trailing slashes in non-router paths
for path, info_list in url_map.items():
    for info in info_list:
        pattern = info['pattern']
        # Router patterns don't need trailing slashes, but regular paths should
        if not any(x in pattern for x in ['<', '^', '$', '?P']):  # Not a router pattern
            if not pattern.endswith('/') and pattern != '':
                issues.append(f"Missing trailing slash: {path} (pattern: {pattern})")

if issues:
    print(f"\n⚠️  Found {len(issues)} potential issues:")
    for issue in issues[:10]:  # Show first 10
        print(f"  - {issue}")
    if len(issues) > 10:
        print(f"  ... and {len(issues) - 10} more")
else:
    print("\n✅ No trailing slash issues found!")

# List all URLs by app
print("\n" + "=" * 80)
print("URLS BY CATEGORY")
print("=" * 80)

categories = {
    'Auth': [p for p in url_map.keys() if 'auth' in p],
    'Users': [p for p in url_map.keys() if 'users' in p or '/me' in p],
    'Catalog': [p for p in url_map.keys() if 'catalog' in p],
    'Admissions': [p for p in url_map.keys() if 'admissions' in p],
    'Attendance': [p for p in url_map.keys() if 'attendance' in p],
    'Assessment': [p for p in url_map.keys() if 'assessment' in p],
    'Certificates': [p for p in url_map.keys() if 'certificates' in p],
    'Documents': [p for p in url_map.keys() if 'documents' in p],
    'Reporting': [p for p in url_map.keys() if 'reporting' in p],
    'Timekeeping': [p for p in url_map.keys() if 'timekeeping' in p],
    'Gallery': [p for p in url_map.keys() if 'gallery' in p],
    'Subscriptions': [p for p in url_map.keys() if 'subscriptions' in p],
}

for category, urls in categories.items():
    if urls:
        print(f"\n{category} ({len(urls)} URLs):")
        for url in sorted(urls)[:5]:  # Show first 5
            print(f"  - {url}")
        if len(urls) > 5:
            print(f"  ... and {len(urls) - 5} more")

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)

