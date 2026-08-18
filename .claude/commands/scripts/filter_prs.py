import json
import re
import sys
from datetime import datetime

cutoff = sys.argv[1]      # ISO-8601 cutoff
seen_json = sys.argv[2]   # JSON string of {pr_number: first_seen_date}
today_str = sys.argv[3]   # YYYY-MM-DD today
pr_file = sys.argv[4]     # path to raw gh pr list JSON

seen_prs = json.loads(seen_json)
USER = "andrew-parable"
OVERLAP = ["services/web-api/", "services/web-admin-api/", "apps/web-app/"]
TEAM_SLUGS = {"platform", "product-engineering"}

# Team-broadcast PRs in these lanes are not Andrew's daily review queue unless
# he is the explicit requested reviewer.
EXCLUDE_TITLE_RE = re.compile(
    r"(?i)"
    r"(chore\(deps\)|dependabot|"
    r"perf\(ci\)|^ci[:/]|"
    r"build daily ci|affected go modules|"
    r"docs\(edr\)|^docs:)"
)
EXCLUDE_PATH_PREFIXES = (
    ".github/",
    "scripts/ci/",
    "infrastructure/",
    "docs/edr/",
    "docs/internal/",
    "make/test.mk",
)


def size_label(adds, dels):
    size = adds + dels
    if size < 50:
        return "S"
    if size < 300:
        return "M"
    if size < 1000:
        return "L"
    return "XL"


def team_requested(review_requests):
    for rr in review_requests:
        slug = rr.get("slug") or ""
        for team in TEAM_SLUGS:
            if slug.endswith("/" + team) or slug == team or team in slug.split("/"):
                return True
    return False


def touches_overlap(files):
    return any(
        any(f["path"].startswith(prefix) for prefix in OVERLAP)
        for f in files
    )


def exclusion_reason(title, files):
    if EXCLUDE_TITLE_RE.search(title or ""):
        return "chore_ci_deps"
    if not touches_overlap(files) and any(
        f["path"].startswith(prefix)
        for f in files
        for prefix in EXCLUDE_PATH_PREFIXES
    ):
        return "infra_ci_docs"
    return None


with open(pr_file) as f:
    data = json.load(f)

results = []
for pr in data:
    author = pr["author"]["login"]
    title = pr.get("title") or ""
    files = pr.get("files") or []
    overlap = touches_overlap(files)
    review_requests = pr.get("reviewRequests") or []
    explicit = any(rr.get("login") == USER for rr in review_requests)
    team_req = team_requested(review_requests)
    excluded = exclusion_reason(title, files)

    # Never put own PRs in the review queue — shepherding is Task Log, not reviews.
    if author == USER:
        include = False
        excluded = excluded or "own_authored"
    else:
        # Tier 1: explicit personal reviewer on current PR state (from gh pr list JSON).
        # Tier 2: team broadcast only when overlap paths match and not excluded lane.
        # No tier-3 "awareness" PRs without a review request.
        include = explicit or (team_req and overlap and not excluded)

    num = str(pr["number"])
    first_seen = seen_prs.get(num, today_str)
    today = datetime.fromisoformat(today_str).date()
    days_carried = (today - datetime.fromisoformat(first_seen).date()).days

    if include:
        category = "explicit" if explicit else "team_overlap"
    else:
        category = "excluded"

    entry = {
        "number": pr["number"],
        "title": title,
        "author": author,
        "size": size_label(pr["additions"], pr["deletions"]),
        "review_requested": explicit or team_req,
        "explicit": explicit,
        "overlap": overlap,
        "category": category,
        "excluded_reason": excluded,
        "url": pr["url"],
        "updatedAt": pr["updatedAt"],
        "days_carried": days_carried,
        "first_seen": first_seen,
    }
    if include:
        results.append(entry)

new_seen = dict(seen_prs)
for r in results:
    new_seen.setdefault(str(r["number"]), today_str)

print(json.dumps({"prs": results, "seen_prs": new_seen}, indent=2))
