#!/bin/bash
#
# Compare this branch with another to assess duplicate work
#
# Usage:
#   ./compare-branches.sh <other-branch-name>
#
# Example:
#   ./compare-branches.sh feature/mobile-review
#

set -e

OTHER_BRANCH=${1:-main}
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "========================================"
echo "Branch Comparison Tool"
echo "========================================"
echo "Current branch: $CURRENT_BRANCH"
echo "Comparing with: $OTHER_BRANCH"
echo "========================================"
echo ""

# Check if other branch exists
if ! git rev-parse --verify "$OTHER_BRANCH" >/dev/null 2>&1; then
    echo "❌ Branch '$OTHER_BRANCH' not found"
    echo ""
    echo "Available branches:"
    git branch -a | grep -v "HEAD"
    exit 1
fi

# Files unique to current branch
echo "📁 Files ONLY in current branch ($CURRENT_BRANCH):"
echo "----------------------------------------"
git diff --name-only "$OTHER_BRANCH"..."$CURRENT_BRANCH" | grep -v "^D" || echo "(none)"
echo ""

# Files unique to other branch
echo "📁 Files ONLY in other branch ($OTHER_BRANCH):"
echo "----------------------------------------"
git diff --name-only "$CURRENT_BRANCH"..."$OTHER_BRANCH" | grep -v "^D" || echo "(none)"
echo ""

# Commits unique to current branch
echo "📝 Commits in current branch but not in other:"
echo "----------------------------------------"
git log --oneline "$OTHER_BRANCH".."$CURRENT_BRANCH" || echo "(none)"
echo ""

# Commits unique to other branch
echo "📝 Commits in other branch but not in current:"
echo "----------------------------------------"
git log --oneline "$CURRENT_BRANCH".."$OTHER_BRANCH" || echo "(none)"
echo ""

# File statistics
echo "📊 File Statistics:"
echo "----------------------------------------"
echo "Current branch files:"
git ls-tree -r --name-only "$CURRENT_BRANCH" mobile/ 2>/dev/null | wc -l || echo "0"

echo "Other branch files:"
git ls-tree -r --name-only "$OTHER_BRANCH" mobile/ 2>/dev/null | wc -l || echo "0"
echo ""

# Check for mobile-related keywords in commit messages
echo "🔍 Mobile-related commits in other branch:"
echo "----------------------------------------"
git log "$CURRENT_BRANCH".."$OTHER_BRANCH" --oneline --grep="mobile\|security\|pwa\|lambda" -i || echo "(none found)"
echo ""

# Check if security fixes are present in other branch
echo "🔒 Security-related files comparison:"
echo "----------------------------------------"
echo "SECURITY.md:"
if git ls-tree -r --name-only "$OTHER_BRANCH" mobile/SECURITY.md >/dev/null 2>&1; then
    echo "  ✅ Exists in $OTHER_BRANCH"
else
    echo "  ❌ Missing in $OTHER_BRANCH"
fi

echo "generate_password_hash.py:"
if git ls-tree -r --name-only "$OTHER_BRANCH" mobile/generate_password_hash.py >/dev/null 2>&1; then
    echo "  ✅ Exists in $OTHER_BRANCH"
else
    echo "  ❌ Missing in $OTHER_BRANCH"
fi
echo ""

# Check for bcrypt in mobile_api.py
echo "🔐 Password hashing implementation:"
echo "----------------------------------------"
if git show "$OTHER_BRANCH:src/review/mobile_api.py" 2>/dev/null | grep -q "bcrypt\|passlib"; then
    echo "  ✅ Bcrypt/passlib found in $OTHER_BRANCH"
else
    echo "  ❌ Bcrypt/passlib NOT found in $OTHER_BRANCH"
fi
echo ""

# Recommendation
echo "========================================"
echo "📋 Quick Assessment"
echo "========================================"

FILES_CURRENT=$(git ls-tree -r --name-only "$CURRENT_BRANCH" mobile/ 2>/dev/null | wc -l || echo "0")
FILES_OTHER=$(git ls-tree -r --name-only "$OTHER_BRANCH" mobile/ 2>/dev/null | wc -l || echo "0")
COMMITS_CURRENT=$(git log --oneline "$OTHER_BRANCH".."$CURRENT_BRANCH" | wc -l || echo "0")
COMMITS_OTHER=$(git log --oneline "$CURRENT_BRANCH".."$OTHER_BRANCH" | wc -l || echo "0")

echo "Mobile files: $FILES_CURRENT (current) vs $FILES_OTHER (other)"
echo "Unique commits: $COMMITS_CURRENT (current) vs $COMMITS_OTHER (other)"
echo ""

if [ "$FILES_OTHER" -eq 0 ] && [ "$COMMITS_OTHER" -eq 0 ]; then
    echo "✅ RECOMMENDATION: No duplicate work detected"
    echo "   → Safe to merge current branch"
elif [ "$FILES_CURRENT" -gt "$FILES_OTHER" ] && [ "$COMMITS_CURRENT" -gt 0 ]; then
    echo "⚠️  RECOMMENDATION: Current branch appears more complete"
    echo "   → Review other branch for unique features"
    echo "   → Consider using current branch as base"
else
    echo "🔄 RECOMMENDATION: Potential duplicate work detected"
    echo "   → Manual review required"
    echo "   → Compare feature completeness"
    echo "   → See BRANCH_ASSESSMENT.md for checklist"
fi

echo ""
echo "For detailed diff:"
echo "  git diff $OTHER_BRANCH...$CURRENT_BRANCH"
echo ""
echo "For merge preview:"
echo "  git merge --no-commit --no-ff $OTHER_BRANCH"
echo "  git merge --abort  # to undo preview"
