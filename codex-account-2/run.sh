#!/usr/bin/env bash
set -euo pipefail

readonly ACCOUNT_ROOT="/home/galbot/lizekai/RSI/codex-account-2"
readonly ACCOUNT_CODEX_HOME="${ACCOUNT_ROOT}/home"
readonly ACCOUNT_WORKSPACE="${ACCOUNT_ROOT}/workspace"

mkdir -p "${ACCOUNT_WORKSPACE}" "${ACCOUNT_ROOT}/logs"
chmod 700 "${ACCOUNT_ROOT}" "${ACCOUNT_CODEX_HOME}" \
  "${ACCOUNT_WORKSPACE}" "${ACCOUNT_ROOT}/logs"

if [[ ! -f "${ACCOUNT_CODEX_HOME}/auth.json" ]] ||
   [[ $(stat -c '%s' "${ACCOUNT_CODEX_HOME}/auth.json") -le 3 ]]; then
  echo "第二账号的 auth.json 尚未填入。" >&2
  exit 2
fi

chmod 600 "${ACCOUNT_CODEX_HOME}/auth.json"

cd "${ACCOUNT_WORKSPACE}"
exec env \
  -u CODEX_ACCESS_TOKEN \
  -u CODEX_API_KEY \
  -u OPENAI_API_KEY \
  -u OPENAI_ADMIN_KEY \
  CODEX_HOME="${ACCOUNT_CODEX_HOME}" \
  codex "$@"
