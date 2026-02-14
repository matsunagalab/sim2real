#!/bin/bash
# parse_latex_errors.sh - Extract errors and warnings from LaTeX log
# Usage: ./scripts/parse_latex_errors.sh [logfile]

LOGFILE="${1:-main.log}"
OUTFILE="build_errors.md"

if [ ! -f "$LOGFILE" ]; then
    echo "Log file not found: $LOGFILE"
    exit 1
fi

# Count errors first (outside the subshell)
ERROR_COUNT=$(grep -c "^!" "$LOGFILE" 2>/dev/null | tr -d '\n' || echo "0")
WARN_COUNT=$(grep -ci "warning" "$LOGFILE" 2>/dev/null | tr -d '\n' || echo "0")

# Create error report
{
    echo "# LaTeX Build Errors"
    echo ""
    echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # Check for errors
    ERRORS=$(grep -n "^!" "$LOGFILE" | head -20)
    if [ -n "$ERRORS" ]; then
        echo "## Errors"
        echo ""
        echo '```'
        echo "$ERRORS"
        echo '```'
        echo ""
    fi

    # Check for undefined references
    UNDEF=$(grep -i "undefined" "$LOGFILE" | grep -v "^(" | head -10)
    if [ -n "$UNDEF" ]; then
        echo "## Undefined References"
        echo ""
        echo '```'
        echo "$UNDEF"
        echo '```'
        echo ""
    fi

    # Check for BibTeX errors
    if [ -f "main.blg" ]; then
        BIBERR=$(grep -E "(Error|error|Warning--)" "main.blg" | head -10)
        if [ -n "$BIBERR" ]; then
            echo "## BibTeX Issues"
            echo ""
            echo '```'
            echo "$BIBERR"
            echo '```'
            echo ""
        fi
    fi

    # Check for overfull/underfull boxes (optional)
    BOXES=$(grep -E "(Overfull|Underfull)" "$LOGFILE" | head -5)
    if [ -n "$BOXES" ]; then
        echo "## Box Warnings (optional)"
        echo ""
        echo '```'
        echo "$BOXES"
        echo '```'
        echo ""
    fi

    # Summary
    echo "## Summary"
    echo ""
    echo "- Errors: $ERROR_COUNT"
    echo "- Warnings: $WARN_COUNT"

} > "$OUTFILE"

echo "Error report written to: $OUTFILE"

# Exit with error code if there were errors
if [ "$ERROR_COUNT" -gt 0 ] 2>/dev/null; then
    cat "$OUTFILE"
    exit 1
fi

exit 0
