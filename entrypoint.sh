#!/usr/bin/env bash
set -euo pipefail

# If LOCAL_UID/GID are provided, ensure the container developer user matches them (helpful for mounted workspaces)
if [ -n "${LOCAL_UID:-}" ] && [ -n "${LOCAL_GID:-}" ]; then
  if id -u developer >/dev/null 2>&1; then
    CURRENT_UID=$(id -u developer)
    if [ "$CURRENT_UID" != "$LOCAL_UID" ]; then
      # recreate user with desired uid/gid
      sudo userdel -r developer || true
      groupadd -g "$LOCAL_GID" developer || true
      useradd -m -u "$LOCAL_UID" -g "$LOCAL_GID" -s /bin/bash developer || true
    fi
  else
    groupadd -g "$LOCAL_GID" developer || true
    useradd -m -u "$LOCAL_UID" -g "$LOCAL_GID" -s /bin/bash developer || true
  fi
  sudo chown -R "$LOCAL_UID:$LOCAL_GID" /workspace || true
fi

# If no command was passed, open an interactive bash shell as developer
if [ $# -eq 0 ]; then
  exec su - developer -s /bin/bash -c "bash"
else
  exec su - developer -s /bin/bash -c "$*"
fi
