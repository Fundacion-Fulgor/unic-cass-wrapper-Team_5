#!/usr/bin/env bash
set -u

cd "$(dirname "$0")"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "================================================="
echo "Starting Local RTL Verification (Cocotb)"
echo "================================================="

FAILED_TESTS=()

for dir in */; do
  test_name="${dir%/}"
  if [ ! -e "$dir/Makefile" ] && [ ! -e "$dir/makefile" ]; then
    continue
  fi
  case " ${SKIP_TESTS:-gls} " in
    *" $test_name "*)
      echo -e "\nSkipping ${GREEN}$test_name${NC} (gate level, run it by hand)"
      continue
      ;;
  esac
  echo -e "\nRunning tests in: ${GREEN}$test_name${NC}"
  echo "-------------------------------------------------"
  if make -C "$dir"; then
    echo -e "${GREEN}SUCCESS:${NC} $test_name passed."
  else
    echo -e "${RED}FAILURE:${NC} $test_name failed."
    FAILED_TESTS+=("$test_name")
  fi
done

echo -e "\n================================================="
echo "Verification Summary"
echo "================================================="

if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
  echo -e "${GREEN}All tests passed successfully!${NC}"
  exit 0
else
  echo -e "${RED}Errors were found in the following modules:${NC}"
  for failed in "${FAILED_TESTS[@]}"; do
    echo "  - ❌ $failed"
  done
  exit 1
fi
