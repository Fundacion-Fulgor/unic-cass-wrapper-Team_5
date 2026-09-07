#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(cd "$PROJECT_DIR/.." && pwd)"
MOUNT="/home/designer/shared"
DEFAULT_IMAGE="isaiassh/unic-cass-tools:1.2.3"
CONTAINER="$(basename "$PROJECT_DIR" | tr '[:upper:]_' '[:lower:]-')-tools"

TTY_FLAGS=()
if [ -t 0 ] && [ -t 1 ]; then
    TTY_FLAGS=(-i -t)
fi

log()  { printf '\033[0;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[0;33m==>\033[0m %s\n' "$*"; }
die()  { printf '\033[0;31m==> ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
cat <<EOF
Open a shell in the UNIC-CASS tools container with this project ready to build.

The project is bind-mounted at $MOUNT, so the container always sees your
current sources. Nothing is copied, so you cannot build a stale tree.

The container is kept between sessions as '$CONTAINER'. The Makefiles build
LibreLane through nix-shell the first time, which is slow; a persistent
container means that happens once instead of on every launch.

The flow uses the IHP-Open-PDK checked out in this repository, because that is
what the Makefiles point PDK_ROOT at. Populated submodules are left exactly as
you have them, they are never reset to the recorded pins.

Usage: $(basename "$0") [--fresh] [--dry-run] [-h]

  --fresh     Delete the container and start a new one from the image
  --dry-run   Print what would run
  -h          This message

Once inside, for example:
  cd unic_cass_wrapper_digital/unic_cass_wrapper_user_project && make fft16
  cd unic_cass_wrapper_digital/unic_cass_wrapper_2x2         && make
EOF
}

resolve_image() {
    [ -n "${IMAGE:-}" ] && { printf '%s' "$IMAGE"; return; }
    local t f u i g
    t="$(find "$PARENT_DIR" -maxdepth 1 -type d -iname '*uniccass*icdesign*' 2>/dev/null | head -n1)"
    f="$t/.env"
    if [ -n "$t" ] && [ -f "$f" ]; then
        u=$(grep -E '^DOCKER_USER='  "$f" | tail -1 | cut -d= -f2-)
        i=$(grep -E '^DOCKER_IMAGE=' "$f" | tail -1 | cut -d= -f2-)
        g=$(grep -E '^DOCKER_TAG='   "$f" | tail -1 | cut -d= -f2-)
        [ -n "$u$i$g" ] && { printf '%s/%s:%s' "$u" "$i" "$g"; return; }
    fi
    printf '%s' "$DEFAULT_IMAGE"
}

patch_librelane_drc_glob() {
    local f="$PROJECT_DIR/librelane/librelane/steps/openroad.py"
    [ -f "$f" ] || return 0
    if grep -q 'rglob("\*\.drc\*")' "$f"; then
        sed -i 's|rglob("\*\.drc\*")|rglob("*.drc")|' "$f"
        warn "patched a librelane bug: DetailedRouting globs '*.drc*', which also"
        warn "matches the '*.drc.xml' it writes itself, then fails parsing it"
    fi
}

check_sources() {
    local sub state
    while read -r state sub _; do
        case "$state" in
            -*) log "initialising submodule $sub"
                git -C "$PROJECT_DIR" submodule update --init "$sub" ;;
        esac
    done < <(git -C "$PROJECT_DIR" submodule status | sed 's/^\(.\)/\1 /')

    for sub in librelane IHP-Open-PDK; do
        [ -d "$PROJECT_DIR/$sub/.git" ] || [ -f "$PROJECT_DIR/$sub/.git" ] || continue
        if [ "$(git -C "$PROJECT_DIR/$sub" rev-parse --is-shallow-repository 2>/dev/null)" = "true" ]; then
            log "unshallowing $sub, Nix needs the full history"
            git -C "$PROJECT_DIR/$sub" fetch --unshallow >/dev/null 2>&1 || true
        fi
        log "$(printf '%-14s' "$sub") $(git -C "$PROJECT_DIR/$sub" describe --tags 2>/dev/null || echo '?')"
    done

    local pdk_cfg flow_py
    pdk_cfg="$PROJECT_DIR/IHP-Open-PDK/ihp-sg13g2/libs.tech/librelane/config.tcl"
    flow_py="$PROJECT_DIR/librelane/librelane/config/flow.py"
    if grep -q '"VDD_PIN_VOLTAGE"' "$flow_py" 2>/dev/null \
       && grep -q 'IO_PIN_H_LAYER' "$pdk_cfg" 2>/dev/null; then
        warn "This librelane revision requires VDD_PIN_VOLTAGE, which this PDK"
        warn "revision no longer provides. The flow will fail loading the PDK."
        warn "Move librelane to 3.0.0rc1 or newer."
    fi

    patch_librelane_drc_glob
}

create_args() {
    printf '%s\n' \
        --name "$CONTAINER" "${TTY_FLAGS[@]+"${TTY_FLAGS[@]}"}" \
        --mount "type=bind,source=$PROJECT_DIR,target=$MOUNT" \
        -w "$MOUNT" \
        -e "SHELL=/bin/bash" \
        -e "PDK=${PDK_NAME:-ihp-sg13g2}" \
        -e "PDK_ROOT=$MOUNT/IHP-Open-PDK" \
        -e "USER_ID=$(id -u)" \
        -e "USER_GROUP=$(id -g)" \
        -e "DISPLAY=${DISPLAY:-}" \
        -e "LIBGL_ALWAYS_INDIRECT=1" \
        -e "XDG_RUNTIME_DIR=/tmp/runtime-default"
    [ -d /tmp/.X11-unix ] && printf '%s\n' -v "/tmp/.X11-unix:/tmp/.X11-unix:ro"
    [ -d /mnt/wslg ]      && printf '%s\n' -v "/mnt/wslg:/mnt/wslg"
    printf '%s\n' --net=host "$(resolve_image)"
}

main() {
    local fresh=0 dry=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --fresh) fresh=1 ;;
            --dry-run) dry=1 ;;
            -h|--help) usage; return 0 ;;
            *) die "Unknown option '$1'" ;;
        esac
        shift
    done

    command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1 \
        || die "Docker is not reachable. Docker Desktop -> Settings -> Resources -> WSL Integration."

    check_sources

    local image exists
    image="$(resolve_image)"
    docker image inspect "$image" >/dev/null 2>&1 || { log "pulling $image"; docker image pull "$image"; }

    exists="$(docker container ls -aq -f "name=^${CONTAINER}$")"
    if [ "$fresh" = "1" ] && [ -n "$exists" ]; then
        log "removing the existing container"
        docker rm -f "$CONTAINER" >/dev/null
        exists=""
    fi

    if [ -n "$exists" ]; then
        if [ "$dry" = "1" ]; then echo "docker start -ai $CONTAINER"; return 0; fi
        log "reusing container '$CONTAINER', whatever Nix already built is still there"
        log "you will land in $MOUNT; build whatever you want from there"
        docker start -ai "$CONTAINER"
    else
        local -a args
        mapfile -t args < <(create_args)
        if [ "$dry" = "1" ]; then printf 'docker run'; printf ' %q' "${args[@]}"; printf '\n'; return 0; fi
        log "creating container '$CONTAINER'"
        log "you will land in $MOUNT; build whatever you want from there"
        log "note: the first LibreLane build inside this container is slow, but it is kept"
        docker run "${args[@]}"
    fi
}

main "$@"
