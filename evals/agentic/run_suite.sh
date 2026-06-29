#!/bin/bash
# Run the agentic eval suite against ONE llm-local profile (served one at a time).
# Quality outputs are deterministic at temperature=0, so this is reproducible.
#
# Usage:  ./run_suite.sh <profile> <port> [think|nothink]
# Example: ./run_suite.sh ornith-35b 8020 nothink
#          ./run_suite.sh ornith-35b-think 8028 think
#
# After it finishes, grade the objective half with:
#   python3 grade_personal.py <profile>
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
LLM="${LLM_LOCAL:-llm-local}"
profile="${1:?usage: run_suite.sh <profile> <port> [think|nothink]}"
port="${2:?need a port}"
mode="${3:-nothink}"
base="http://127.0.0.1:${port}"

echo ">>> serving $profile on :$port"
"$LLM" stop >/dev/null 2>&1; sleep 2
"$LLM" serve "$profile" >/dev/null 2>&1
for i in $(seq 1 120); do
  c=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 -H "Content-Type: application/json" \
        -d '{"model":"default","messages":[{"role":"user","content":"hi"}],"max_tokens":1}' \
        "$base/v1/chat/completions" 2>/dev/null)
  [ "$c" = "200" ] && break; sleep 5
done

if [ "$mode" = "think" ]; then
  # Thinking path: Anthropic endpoint, reasoning kept separate. 12k ceiling
  # (raise per profile's --max-tokens; A3B-think is capped at 8k by its config).
  python3 "$HERE/run_think.py" "$profile" "$base" scenarios_personal.json ALL 12000
  python3 "$HERE/run_think.py" "$profile" "$base" scenarios_cowork.json ALL 12000
else
  python3 "$HERE/run_personal.py" "$profile" "$base" default          # 20 objective exercises
fi
python3 "$HERE/tool_call_test.py" "$profile" "$base"                   # 8 tool-calling scenarios
python3 "$HERE/speed_probe.py"   "$profile" "$base" 800 3              # decode tok/s (best of 3)

"$LLM" stop >/dev/null 2>&1
echo ">>> done. Grade objective half:  python3 $HERE/grade_personal.py $profile"
