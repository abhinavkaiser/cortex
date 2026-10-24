# Hetzner deployment runner

The `Cortex server access` workflow uses a repository-specific self-hosted
runner on `ubuntu-4gb-fsn1-1` (`178.105.97.144`). The runner runs as root,
matching the server deployment access requested by the owner. It is managed
by systemd and stays connected to GitHub after the setup SSH session closes.

Only trusted repository writers can trigger the configured workflow: it runs
manually or when setup files change on `codex/deployment-access`. There is no
pull-request trigger. Keep untrusted pull-request code off this production
runner.

## One-time automatic connection

Run `.github/scripts/connect-hetzner-runner.py` on the owner's Mac, where SSH
to the server works. The script:

1. Uses the existing GitHub CLI login, or opens its supported browser login.
   If needed, downloads a private copy of the official Mac CLI and verifies
   its SHA-256 against the official release metadata.
2. Creates the temporary runner registration token through the Mac's GitHub
   login. No registration token or private key needs to be copied.
3. Uses the Mac's SSH connection to install and register the official Linux
   runner in `/opt/cortex-github-runner`, verifying the official artifact digest.
4. Installs and starts its root systemd service and checks that GitHub reports
   the `cortex-production` runner online.

The token travels in memory through SSH stdin, not command history or this
repository. Existing runner files are preserved; a conflicting or incomplete
installation is rejected. The installer checks the expected server identity,
available disk space and repository binding. It does not change the app
checkout, database or nginx configuration, or explicitly restart app services.
The root runner is the persistent deployment connection the owner requested.

The existing Codex integration cannot create runner registration tokens:
GitHub returns HTTP 403 `Resource not accessible by integration`. The one-time
Mac bridge uses the owner's own authorized GitHub login for this operation.
After registration, Codex's existing integration can trigger and monitor
workflow runs without copying that Mac credential into the cloud environment.
The previously requested `CORTEX_GITHUB_SECRETS_TOKEN` and SSH repository
secrets are not needed for this runner approach.

## Readiness check

The first workflow checks out the trusted setup revision in the runner's own
workspace, outside `/opt/cortex`. It executes
`.github/scripts/deployment_inventory.py`, which verifies root/server identity
and reports the deployed revision, service metadata, runtime executable paths
and production health. It does not dump environment files or command arguments.
The report is also emitted as a GitHub check notice so the existing integration
can inspect it through the API without a separate log-download route.

A successful online status and workflow run are required before claiming
deployment access is verified. The setup script and workflow have been
validated locally, but the Mac/server installation has not been executed from
the cloud environment.

Once the report is available, prepare the deployment procedure for the exact
requested commit and actual server services. Preserve `backend/.env`,
`backend/ai_academy.db` and uploaded media; make a consistent database backup
and verify application health after deployment. Do not seed production or
overwrite its database with the local development copy. The access-check
workflow itself does not deploy application changes.
