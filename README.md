# Environment Variables

Create a `.env` file in the project root (see `.env.example` for all required keys):

```dotenv
VITE_UX_EVENT_SINK_TYPE=openobserve
VITE_UX_EVENT_SINK_URL=http://localhost:5080/api/default/ux_events/_json
VITE_UX_EVENT_SINK_API_KEY=Basic cm9vdEBleGFtcGxlLmNvbTpDb21wbGV4UGFzcyMxMjM=

VITE_SIM_EVENT_SINK_TYPE=openobserve
VITE_SIM_EVENT_SINK_URL=http://localhost:5080/api/default/sim_events/_json
VITE_SIM_EVENT_SINK_API_KEY=Basic cm9vdEBleGFtcGxlLmNvbTpDb21wbGV4UGFzcyMxMjM=
```

These variables control the event sink type, endpoint, and authentication for both UX and simulation events.

## Observability Infrastructure (Local)

To run a local instance of OpenObserve for development:

```bash
make ds-up
```

Infrastructure remains active in the background. To stop it:

```bash
make ds-down
```

Data is persisted in a podman volume named `openobserve-data`.
# Running Tests

This project uses [Vitest](https://vitest.dev/) for testing.

To run all tests:

```
npm install
npm test
```

Or, if you want to run tests with Vitest directly:

```
npx vitest run
```

All test files are located in the `tests/` directory.
# bns — Fedora TypeScript Development Container

This repository contains a Fedora-based development container for TypeScript development, designed to be built and run with Podman.

## Quick start (Podman)

Build the image:

    make build

Run an interactive shell (mounts your workspace with SELinux label):

    make run

Notes:
- We use `:Z` on the workspace bind mount to ensure SELinux labels are correct for the container on Fedora/SELinux hosts.
- The container expects `LOCAL_UID` and `LOCAL_GID` environment variables to map file ownership to your host user (the Makefile sets these automatically).

## Using with VS Code

Open the repository in VS Code and choose **Remote - Containers: Open Folder in Container** (or the Command Palette entry). The devcontainer configuration is in `.devcontainer/devcontainer.json` and will build using the `Containerfile` at the project root.

## Files of interest
- `Containerfile` — Fedora base image, Node.js install, developer user and global tools
- `entrypoint.sh` — adjusts UID/GID when `LOCAL_UID`/`LOCAL_GID` are provided and drops into the `developer` user
- `Makefile` — convenience targets to build and run with Podman
- `.devcontainer/devcontainer.json` — VS Code devcontainer config

## License
Specify a license if you want (e.g., MIT). If you'd like, I can add a `LICENSE` file.
