#!/usr/bin/env python3
"""Extract relevant EDR sections by keyword — lazy fetch for swarm-review Phase 2.

Avoids loading full .mdx files into agent context. Shortlists EDRs, maps headers,
and emits a constraints digest capped by --max-edrs and --max-lines-per-edr.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$")
FRONT_MATTER_RE = re.compile(r"^---\s*$")

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "api": ["api", "endpoint", "handler", "error", "code", "response"],
    "connector": ["connector", "lifecycle", "behavior", "schema", "status"],
    "service": ["package", "service", "structure", "module"],
    "infra": ["pulumi", "stack", "gke", "otel", "infrastructure", "kubernetes"],
    "pipeline": ["prefect", "pipeline", "ingestion", "gold", "layer"],
    "query": ["datafusion", "query", "sql"],
}

EDR_ID_RE = re.compile(r"EDR[-\s]?(\d{4})", re.IGNORECASE)


@dataclass(frozen=True)
class Section:
    """A markdown section bounded by headers."""

    level: int
    title: str
    start: int
    end: int
    body: str

    @property
    def line_count(self) -> int:
        return self.body.count("\n") + 1 if self.body else 0


@dataclass
class EdRFile:
    """Parsed EDR document."""

    path: Path
    title: str = ""
    description: str = ""
    preamble: str = ""
    sections: list[Section] = field(default_factory=list)

    @property
    def stem(self) -> str:
        return self.path.stem

    @property
    def edr_id(self) -> str | None:
        for source in (self.title, self.stem, self.path.name):
            match = EDR_ID_RE.search(source)
            if match:
                return f"EDR-{match.group(1)}"
        return None

    @property
    def display_name(self) -> str:
        if self.title:
            return self.title
        if self.edr_id:
            return self.edr_id
        return self.stem


def parse_front_matter(lines: list[str]) -> tuple[dict[str, str], int]:
    """Return YAML-ish front matter key/values and the line index after the closing ---."""
    if not lines or not FRONT_MATTER_RE.match(lines[0]):
        return {}, 0

    meta: dict[str, str] = {}
    idx = 1
    while idx < len(lines):
        if FRONT_MATTER_RE.match(lines[idx]):
            return meta, idx + 1
        line = lines[idx].strip()
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"').strip("'")
        idx += 1
    return meta, 0


def parse_sections(lines: list[str], body_start: int) -> tuple[str, list[Section]]:
    """Split document body into preamble and sections."""
    headers: list[tuple[int, int, int, str]] = []
    for i in range(body_start, len(lines)):
        match = HEADER_RE.match(lines[i])
        if match:
            level = len(match.group(1))
            headers.append((i, level, len(lines), match.group(2).strip()))

    if not headers:
        preamble = "\n".join(lines[body_start:]).strip()
        return preamble, []

    preamble = "\n".join(lines[body_start : headers[0][0]]).strip()
    sections: list[Section] = []

    for idx, (start, level, _, title) in enumerate(headers):
        end = len(lines)
        for next_start, next_level, _, _ in headers[idx + 1 :]:
            if next_level <= level:
                end = next_start
                break
        body = "\n".join(lines[start:end]).strip()
        sections.append(Section(level=level, title=title, start=start, end=end, body=body))

    return preamble, sections


def load_edr(path: Path) -> EdRFile:
    """Load and parse one EDR file."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    meta, body_start = parse_front_matter(lines)
    preamble, sections = parse_sections(lines, body_start)
    return EdRFile(
        path=path,
        title=meta.get("title", ""),
        description=meta.get("description", ""),
        preamble=preamble,
        sections=sections,
    )


def normalize_keywords(raw: list[str]) -> list[str]:
    """Lowercase, dedupe, drop empties."""
    seen: set[str] = set()
    result: list[str] = []
    for item in raw:
        for part in re.split(r"[,;\s]+", item):
            word = part.strip().lower()
            if word and word not in seen:
                seen.add(word)
                result.append(word)
    return result


def expand_domains(domains: list[str]) -> list[str]:
    """Expand --domain presets into keywords."""
    keywords: list[str] = []
    for domain in domains:
        key = domain.strip().lower()
        if key in DOMAIN_KEYWORDS:
            keywords.extend(DOMAIN_KEYWORDS[key])
        else:
            keywords.append(key)
    return keywords


def score_text(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    """Score text by keyword hits; return (score, matched keywords)."""
    lowered = text.lower()
    matched: list[str] = []
    score = 0
    for kw in keywords:
        if kw in lowered:
            matched.append(kw)
            score += lowered.count(kw)
    return score, matched


def score_edr(edr: EdRFile, keywords: list[str]) -> tuple[int, list[str]]:
    """Rank whole EDR files for shortlisting."""
    score = 0
    matched: list[str] = []

    for text, weight in (
        (edr.stem, 8),
        (edr.path.name, 6),
        (edr.title, 10),
        (edr.description, 6),
        (edr.preamble[:500], 2),
    ):
        hits, kws = score_text(text, keywords)
        if hits:
            score += hits * weight
            matched.extend(kws)

    for section in edr.sections:
        header_score, header_kws = score_text(section.title, keywords)
        body_score, body_kws = score_text(section.body[:2000], keywords)
        if header_score:
            score += header_score * 12
            matched.extend(header_kws)
        if body_score:
            score += body_score * 3
            matched.extend(body_kws)

    return score, sorted(set(matched))


def score_section(section: Section, keywords: list[str]) -> tuple[int, list[str]]:
    """Rank sections within an EDR."""
    header_score, header_kws = score_text(section.title, keywords)
    body_score, body_kws = score_text(section.body, keywords)
    total = header_score * 15 + body_score * 4
    if header_score == 0 and body_score == 0:
        return 0, []
    return total, sorted(set(header_kws + body_kws))


def discover_edr_dir(explicit: Path | None) -> Path:
    """Resolve EDR directory from flag, env, or common repo layouts."""
    if explicit is not None:
        return explicit

    candidates = [
        Path("docs/internal/edr"),
        Path("docs/edr"),
        Path("edr"),
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    msg = (
        "EDR directory not found. Pass --edr-dir (e.g. docs/internal/edr) "
        "or run from a repo root that contains docs/internal/edr/."
    )
    raise SystemExit(msg)


def list_edr_files(edr_dir: Path) -> list[Path]:
    """Return sorted .mdx files."""
    return sorted(edr_dir.glob("*.mdx"))


def truncate_section_body(body: str, max_lines: int) -> tuple[str, bool]:
    """Truncate section body to max_lines (including header line)."""
    lines = body.splitlines()
    if len(lines) <= max_lines:
        return body, False
    truncated = "\n".join(lines[:max_lines])
    return f"{truncated}\n\n… ({len(lines) - max_lines} lines truncated)", True


def format_headers(edr: EdRFile) -> str:
    """Format section header map for one EDR."""
    lines = [f"### {edr.display_name}", f"`{edr.path}`", ""]
    if not edr.sections:
        lines.append("_No sections found._")
        return "\n".join(lines)

    for section in edr.sections:
        indent = "  " * (section.level - 1)
        lines.append(f"{indent}- {'#' * section.level} {section.title} ({section.line_count} lines)")
    return "\n".join(lines)


def extract_digest(
    edr_dir: Path,
    keywords: list[str],
    *,
    max_edrs: int,
    max_lines_per_edr: int,
    max_sections_per_edr: int,
    min_edr_score: int,
) -> str:
    """Build constraints digest for matching EDRs."""
    if not keywords:
        raise SystemExit("No keywords provided. Use --keywords or --domain.")

    files = list_edr_files(edr_dir)
    if not files:
        raise SystemExit(f"No .mdx files in {edr_dir}")

    ranked: list[tuple[int, list[str], EdRFile]] = []
    for path in files:
        edr = load_edr(path)
        score, matched = score_edr(edr, keywords)
        if score >= min_edr_score:
            ranked.append((score, matched, edr))

    ranked.sort(key=lambda item: item[0], reverse=True)
    shortlisted = ranked[:max_edrs]

    out: list[str] = [
        "# EDR Constraints Digest",
        "",
        f"**Directory**: `{edr_dir}`",
        f"**Keywords**: {', '.join(keywords)}",
        f"**Budget**: ≤{max_edrs} EDRs, ≤{max_lines_per_edr} lines/EDR",
        "",
    ]

    if not shortlisted:
        out.append("_No EDRs matched. Lower --min-edr-score or broaden keywords._")
        return "\n".join(out)

    out.append(f"**Matched**: {len(shortlisted)} of {len(files)} EDRs")
    out.append("")

    for edr_score, edr_matched, edr in shortlisted:
        out.append(f"## {edr.display_name}")
        out.append(f"**File**: `{edr.path.name}` | **Score**: {edr_score}")
        if edr_matched:
            out.append(f"**Hits**: {', '.join(edr_matched)}")
        if edr.description:
            out.append(f"**Summary**: {edr.description[:200]}{'…' if len(edr.description) > 200 else ''}")
        out.append("")

        section_ranked: list[tuple[int, list[str], Section]] = []
        for section in edr.sections:
            sec_score, sec_matched = score_section(section, keywords)
            if sec_score > 0:
                section_ranked.append((sec_score, sec_matched, section))

        section_ranked.sort(key=lambda item: item[0], reverse=True)
        if not section_ranked and edr.preamble:
            preamble_lines = edr.preamble.splitlines()[:max_lines_per_edr]
            out.append("### Preamble (no section headers matched)")
            out.append("")
            out.append("\n".join(preamble_lines))
            out.append("")
            continue

        lines_used = 0
        sections_emitted = 0
        for sec_score, sec_matched, section in section_ranked:
            if sections_emitted >= max_sections_per_edr:
                break
            remaining = max_lines_per_edr - lines_used
            if remaining <= 0:
                out.append(f"_Line budget reached — {len(section_ranked) - sections_emitted} more sections skipped._")
                break

            hit_note = f" (hits: {', '.join(sec_matched)})" if sec_matched else ""
            out.append(f"### {section.title}{hit_note}")
            out.append("")
            body, was_truncated = truncate_section_body(section.body, remaining)
            out.append(body)
            out.append("")
            lines_used += min(section.line_count, remaining)
            sections_emitted += 1
            if was_truncated:
                out.append("_Section truncated to respect line budget._")
                out.append("")
                break

        out.append("---")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    """CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Lazy EDR extraction for swarm-review — shortlist and pull matching sections only.",
    )
    parser.add_argument(
        "--edr-dir",
        type=Path,
        default=None,
        help="Path to EDR directory (default: docs/internal/edr under cwd)",
    )
    parser.add_argument(
        "--keywords",
        "-k",
        action="append",
        default=[],
        help="Keywords to match (repeatable or comma-separated)",
    )
    parser.add_argument(
        "--domain",
        "-d",
        action="append",
        default=[],
        choices=sorted(DOMAIN_KEYWORDS),
        help="Expand a domain preset from swarm-review (repeatable)",
    )
    parser.add_argument(
        "--max-edrs",
        type=int,
        default=3,
        help="Max EDR files to include (default: 3)",
    )
    parser.add_argument(
        "--max-lines-per-edr",
        type=int,
        default=30,
        help="Max lines extracted per EDR (default: 30)",
    )
    parser.add_argument(
        "--max-sections-per-edr",
        type=int,
        default=3,
        help="Max sections per EDR (default: 3)",
    )
    parser.add_argument(
        "--min-edr-score",
        type=int,
        default=4,
        help="Minimum match score to shortlist an EDR (default: 4)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all EDRs with title and description (no extraction)",
    )
    parser.add_argument(
        "--headers-only",
        action="store_true",
        help="Print section header map for shortlisted EDRs (cheap pass)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        action="append",
        default=[],
        help="Extract from specific .mdx file(s) instead of auto-shortlisting",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    edr_dir = discover_edr_dir(args.edr_dir)
    if not edr_dir.is_dir():
        print(f"EDR directory does not exist: {edr_dir}", file=sys.stderr)
        return 1

    if args.list:
        for path in list_edr_files(edr_dir):
            edr = load_edr(path)
            edr_id = edr.edr_id or "?"
            desc = edr.description[:120] + ("…" if len(edr.description) > 120 else "")
            print(f"{edr_id:10}  {path.name:45}  {desc}")
        return 0

    keywords = normalize_keywords(expand_domains(args.domain) + args.keywords)

    if args.headers_only:
        if not keywords and not args.file:
            print("Provide --keywords/--domain or --file for --headers-only", file=sys.stderr)
            return 2

        paths = args.file if args.file else []
        if not paths:
            files = list_edr_files(edr_dir)
            ranked = []
            for path in files:
                edr = load_edr(path)
                score, _ = score_edr(edr, keywords)
                if score >= args.min_edr_score:
                    ranked.append((score, edr))
            ranked.sort(key=lambda item: item[0], reverse=True)
            paths = [edr.path for _, edr in ranked[: args.max_edrs]]

        if not paths:
            print("No EDRs matched keywords.")
            return 0

        print("# EDR Section Headers\n")
        for path in paths:
            edr = load_edr(path if path.is_absolute() else edr_dir / path.name)
            print(format_headers(edr))
            print()
        return 0

    if args.file:
        digest_parts = [
            "# EDR Constraints Digest",
            "",
            f"**Directory**: `{edr_dir}`",
            f"**Keywords**: {', '.join(keywords) if keywords else '(none — explicit files)'}",
            "",
        ]
        for path in args.file:
            resolved = path if path.is_absolute() else edr_dir / path.name
            edr = load_edr(resolved)
            if keywords:
                section_ranked = []
                for section in edr.sections:
                    sec_score, sec_matched = score_section(section, keywords)
                    if sec_score > 0:
                        section_ranked.append((sec_score, sec_matched, section))
                section_ranked.sort(key=lambda item: item[0], reverse=True)
                digest_parts.append(f"## {edr.display_name}")
                digest_parts.append(f"**File**: `{edr.path.name}`")
                digest_parts.append("")
                lines_used = 0
                for _, sec_matched, section in section_ranked[: args.max_sections_per_edr]:
                    remaining = args.max_lines_per_edr - lines_used
                    if remaining <= 0:
                        break
                    hit_note = f" (hits: {', '.join(sec_matched)})" if sec_matched else ""
                    digest_parts.append(f"### {section.title}{hit_note}")
                    digest_parts.append("")
                    body, _ = truncate_section_body(section.body, remaining)
                    digest_parts.append(body)
                    digest_parts.append("")
                    lines_used += min(section.line_count, remaining)
            else:
                digest_parts.append(format_headers(edr))
                digest_parts.append("")
        print("\n".join(digest_parts).rstrip() + "\n")
        return 0

    print(
        extract_digest(
            edr_dir,
            keywords,
            max_edrs=args.max_edrs,
            max_lines_per_edr=args.max_lines_per_edr,
            max_sections_per_edr=args.max_sections_per_edr,
            min_edr_score=args.min_edr_score,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
