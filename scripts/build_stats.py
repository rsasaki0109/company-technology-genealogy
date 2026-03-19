#!/usr/bin/env python3
"""Generate stats.json from domain YAMLs."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from company_technology_genealogy.models import Domain, OpenSourceStatus, load_all_domains

DOMAINS_DIR = Path(__file__).parent.parent / "domains"
OUTPUT_DIR = Path(__file__).parent.parent / "docs"


def build_stats(domains: list[Domain]) -> dict:
    """Build statistics dictionary from loaded domains."""
    all_methods = [m for d in domains for m in d.methods]
    total_methods = len(all_methods)
    total_domains = len(domains)

    # Methods per domain (sorted descending)
    methods_per_domain = sorted(
        [{"domain": d.name, "count": len(d.methods)} for d in domains],
        key=lambda x: x["count"],
        reverse=True,
    )

    # Methods per year
    year_counts = Counter(m.year for m in all_methods)
    methods_per_year = [
        {"year": y, "count": year_counts[y]} for y in sorted(year_counts)
    ]

    # OSS breakdown
    oss_counts = Counter(m.inferred_open_source.value for m in all_methods)
    oss_breakdown = {
        status.value: oss_counts.get(status.value, 0) for status in OpenSourceStatus
    }

    # Top 20 methods by GitHub stars
    starred = [m for m in all_methods if m.stars]
    starred.sort(key=lambda m: m.stars, reverse=True)
    top_by_stars = [
        {
            "name": m.name,
            "stars": m.stars,
            "code": m.code or "",
            "year": m.year,
        }
        for m in starred[:20]
    ]

    return {
        "total_methods": total_methods,
        "total_domains": total_domains,
        "methods_per_domain": methods_per_domain,
        "methods_per_year": methods_per_year,
        "oss_breakdown": oss_breakdown,
        "top_by_stars": top_by_stars,
    }


def generate_stats_json(domains: list[Domain], output_dir: Path | None = None) -> Path:
    """Generate stats.json and return the output path."""
    out = output_dir or OUTPUT_DIR
    out.mkdir(exist_ok=True)
    stats = build_stats(domains)
    stats_path = out / "stats.json"
    with stats_path.open("w") as f:
        json.dump(stats, f, indent=2)
    return stats_path


def main() -> None:
    print("Loading domains...")
    domains = load_all_domains(DOMAINS_DIR)
    stats_path = generate_stats_json(domains)
    print(f"  stats.json: {stats_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
