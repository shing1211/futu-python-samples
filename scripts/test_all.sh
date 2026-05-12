#!/usr/bin/env bash
# Test all examples — quick smoke test, exits 0 if all pass
set -e

EXAMPLES=$(find examples -name 'main.py' -not -path '*/.*' | sort)
FAILED=0

for f in $EXAMPLES; do
  echo -n "Testing $f ... "
  if timeout 10 python3 "$f" 2>&1 | grep -iE "error|traceback" > /dev/null 2>&1; then
    echo "FAIL"
    FAILED=$((FAILED+1))
  else
    echo "OK"
  fi
done

echo ""
if [ $FAILED -eq 0 ]; then
  echo "All examples passed"
else
  echo "$FAILED example(s) had errors"
fi
exit $FAILED
