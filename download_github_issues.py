#!/usr/bin/env python3
from pathlib import Path
import os, math, re
from tqdm import tqdm
from github import Github, GithubException

# ─── config ──────────────────────────────────────────────────────────────
REPO          = "trilogy-group/eng-maintenance"
PRODUCT_LABEL = "Product:Aurea ACRM"         # what you filter by
FILES_WANTED  = 3
# ──────────────────────────────────────────────────────────────────────────

# make a safe folder name, e.g.  Product:Aurea ACRM → aurea_acrm_github_issues
slug = re.sub(r"[^A-Za-z0-9]+", "_", PRODUCT_LABEL.split(":")[-1]).strip("_").lower()
OUTPUT_DIR = Path(f"{slug}_github_issues")

# ──────────────────────────────────────────────────────────────────────────

def main():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Set GITHUB_TOKEN env‑var first!")

    gh   = Github(token, per_page=100)
    q    = f'repo:{REPO} label:"{PRODUCT_LABEL}" is:issue'
    print("Querying GitHub for:", q)

    try:
        issues = list(tqdm(
            gh.search_issues(q, sort="created", order="asc"),
            desc="Fetching issues",
        ))
    except GithubException as e:
        raise SystemExit(f"GitHub API error: {e.data.get('message', e)}")

    if not issues:
        raise SystemExit("Nothing found – check label / repo spelling.")

    print(f"Retrieved {len(issues)} issues")

    per_file = math.ceil(len(issues) / FILES_WANTED)
    OUTPUT_DIR.mkdir(exist_ok=True)

    for i in range(0, len(issues), per_file):
        chunk   = issues[i : i + per_file]
        idx     = i // per_file + 1
        outpath = OUTPUT_DIR / f"issues_{idx:02d}.md"

        with outpath.open("w", encoding="utf-8") as f:
            for iss in chunk:
                assignees = ", ".join(a.login for a in iss.assignees) or "–"
                labels    = ", ".join(l.name for l in iss.labels)
                state     = "closed" if iss.state == "closed" else "open"
                f.write(
                    f"\n\n---\n"
                    f"## #{iss.number} · {iss.title}\n"
                    f"*{state}* · opened {iss.created_at:%Y-%m-%d} "
                    f"by **{iss.user.login}** · assignees: {assignees}\n\n"
                    f"Labels: {labels}\n\n"
                    f"{iss.body or '*No description*'}\n"
                )
                for c in iss.get_comments():
                    f.write(
                        f"\n> **{c.user.login}** commented "
                        f"{c.created_at:%Y-%m-%d}:\n>\n"
                        + "\n> ".join(c.body.splitlines()) + "\n"
                    )
        print(f"Wrote {len(chunk)} issues → {outpath}")

    print("\nDone!  Files are in", OUTPUT_DIR.resolve())

if __name__ == "__main__":
    main()
