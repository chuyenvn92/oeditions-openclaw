#!/usr/bin/env bash
# Shared shell helpers for wrapper scripts.

load_env_file() {
  local file="${1:-}"
  [ -n "$file" ] && [ -f "$file" ] || return 0

  local line key value
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [ -n "$line" ] || continue
    case "$line" in \#*) continue ;; esac
    case "$line" in *=*) ;; *) continue ;; esac

    key="${line%%=*}"
    value="${line#*=}"
    key="${key%"${key##*[![:space:]]}"}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"

    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue

    case "$value" in
      \"*\") value="${value#\"}"; value="${value%\"}" ;;
      \'*\') value="${value#\'}"; value="${value%\'}" ;;
    esac

    export "$key=$value"
  done < "$file"
}

load_standard_env() {
  local root="${1:?load_standard_env requires repo root}"
  load_env_file "$HOME/.openclaw/secrets.env"
  load_env_file "$root/.env"
}
