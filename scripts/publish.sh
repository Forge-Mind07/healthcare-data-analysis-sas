#!/usr/bin/env bash
# Authenticated, conservative helper. Never force-push or replace existing work.
set -euo pipefail
repo='Forge-Mind07/healthcare-data-analysis-sas'
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
command -v gh >/dev/null || { echo 'Install the official GitHub CLI and authenticate first.' >&2; exit 1; }
gh auth status
python3 -m unittest discover -s tests -v
python3 validation/check_repository.py
test -z "$(git status --porcelain)" || { echo 'Review and commit validated files before publication.' >&2; exit 1; }
if git ls-files data | rg -q '\.(csv|zip)$'; then
    echo 'Patient-level source must not be published.' >&2; exit 1
fi
tmp_error=$(mktemp)
trap 'rm -f "$tmp_error"' EXIT
if gh api "repos/$repo" >/dev/null 2>"$tmp_error"; then
    # Inspect remote metadata and tree without touching its files.
    gh repo view "$repo" --json nameWithOwner,url,isEmpty,defaultBranchRef
    gh api "repos/$repo/contents" --jq '.[].path'
    echo 'Existing repository found. Inspect and merge its work before pushing; this helper stops here.' >&2
    exit 2
elif rg -q 'HTTP 404' "$tmp_error"; then
    gh repo create "$repo" --public --description 'Base SAS 9.4 healthcare data validation and descriptive analytics with independently verified reference results'
else
    cat "$tmp_error" >&2
    echo 'Existence check was inconclusive; no repository created.' >&2; exit 1
fi
if git remote get-url origin >/dev/null 2>&1; then
    test "$(git remote get-url origin)" = "https://github.com/$repo.git" || { echo 'Unexpected origin URL; inspect before publishing.' >&2; exit 1; }
else
    git remote add origin "https://github.com/$repo.git"
fi
git push -u origin main
gh repo view "$repo" --json url
gh api "repos/$repo/git/trees/main?recursive=1" --jq '.tree[].path'
remote_sha=$(gh api "repos/$repo/commits/main" --jq '.sha')
test "$remote_sha" = "$(git rev-parse HEAD)" || { echo 'Remote commit mismatch.' >&2; exit 1; }
echo 'Remote main commit and tree verified.'
