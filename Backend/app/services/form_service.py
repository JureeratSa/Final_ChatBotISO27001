"""
TUH Chatbot AI — Forms Service
แยกจาก app/routers/admin_forms.py (เดิมอยู่ใน Backend/app/routers/admin.py)
"""
from typing import List


def _parse_pages(page_str: str, total_pages: int) -> List[int]:
    """Parse page specification like '1,3,5' or '2-5' or '1-3,7' into sorted 0-indexed page list."""
    pages = set()
    parts = page_str.replace(' ', '').split(',')
    for part in parts:
        if not part:
            continue
        if '-' in part:
            bounds = part.split('-', 1)
            try:
                start = int(bounds[0]) - 1
                end = int(bounds[1]) - 1
            except ValueError:
                continue
            for p in range(start, end + 1):
                if 0 <= p < total_pages:
                    pages.add(p)
        else:
            try:
                p = int(part) - 1
                if 0 <= p < total_pages:
                    pages.add(p)
            except ValueError:
                continue
    return sorted(pages)
