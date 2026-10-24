# Hetzner deployment access

The `Cortex server access` workflow uses a temporary GitHub-hosted Ubuntu
runner to connect to `root@178.105.97.144:22`. This avoids the cloud development
environment's SSH network restriction and does not install a persistent
runner on the production server.

The workflow is a read-only access check. It verifies server identity, reports
the deployed revision and service metadata, and checks application health. It
does not deploy code, migrate data, or restart application services. It only
triggers manually or when its own file changes on `codex/deployment-access`;
there is no pull-request trigger.

## Credential binding

The workflow uses the first available repository Actions secret named
`CORTEX_DEPLOY_SSH_KEY`, `DEPLOY_SSH_KEY`, `SSH_PRIVATE_KEY`, or `SSH_KEY`.
Use `CORTEX_DEPLOY_SSH_KEY` for the dedicated deployment key. Never put private
key contents in this repository, workflow inputs, issues, comments, or logs.

The retained dedicated key in the prepared Codex environment is
`/workspace/.ssh/cortex-course-transfer`. Its public key has been supplied to
the server owner, who reports installing it in root's authorized_keys. A
GitHub credential authorized to manage Actions secrets can bind it securely:

```bash
gh secret set CORTEX_DEPLOY_SSH_KEY --repo abhinavkaiser/cortex < /workspace/.ssh/cortex-course-transfer
```

This command reads the key from its protected file and sends it through the
GitHub CLI's encrypted secret-storage flow; do not print the file or place
the value on a command line. The currently connected integration is denied
access to the repository secrets API (`Resource not accessible by integration`,
HTTP 403), despite the account's admin role. That permission must be supplied
before a missing key can be added through this integration.

`CORTEX_DEPLOY_KNOWN_HOSTS` can pin the SSH host key. On the first connection,
the workflow uses OpenSSH's accept-new policy and reports the authenticated
server's public host key for future pinning. It never disables host-key
checking, and an existing pin mismatch fails the connection. Temporary key
files are mode 600 and removed when the job exits.

## Validation and next deployment step

Workflow YAML and shell syntax have been checked. Remote authentication and
deployment readiness must be established by a successful workflow run; a
successful push alone is not proof of server access.

After access succeeds, inspect the actual services reported by the workflow
and prepare a deployment procedure for the requested commit that preserves
`backend/.env`, `backend/ai_academy.db`, and uploaded media, includes a consistent
database backup, and verifies application health. The course database is live
production data: do not run the local demo seed or overwrite it with the
development copy. Do not claim deployment is configured until this procedure
has been implemented and validated.
