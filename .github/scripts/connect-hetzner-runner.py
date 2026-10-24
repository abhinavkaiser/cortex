#!/usr/bin/env python3
"""One-time Mac bridge: register and install the Hetzner runner automatically.

Uses the Mac's own GitHub login and SSH connection. Registration tokens travel
only in memory and over SSH stdin; they are never printed or committed.
"""
import hashlib
import json
import os
import platform
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

REPOSITORY = 'abhinavkaiser/cortex'
HOST = 'root@178.105.97.144'

REMOTE_INSTALLER = r'''#!/usr/bin/env bash
set -euo pipefail
set +x
umask 077
test "$(id -u)" = 0
test "$(hostname)" = ubuntu-4gb-fsn1-1
test "$(uname -m)" = x86_64
test -d /opt/cortex/backend
IFS= read -r runner_token
test -n "$runner_token"
runner_dir=/opt/cortex-github-runner
if [ -f "$runner_dir/.runner" ]; then
  python3 - "$runner_dir/.runner" <<'VERIFY'
import json, sys
metadata = json.load(open(sys.argv[1]))
if metadata.get('gitHubUrl', '').rstrip('/') != 'https://github.com/abhinavkaiser/cortex':
    raise SystemExit('Existing runner belongs to another repository; refusing to change it')
VERIFY
  unset runner_token
  cd "$runner_dir"
  ./svc.sh start
  ./svc.sh status
  exit 0
fi
if [ -e "$runner_dir" ]; then
  echo 'Runner directory already exists without completed registration; refusing to overwrite it.' >&2
  exit 1
fi
if [ "$(df --output=avail -k /opt | tail -1 | tr -d ' ')" -lt 2097152 ]; then
  echo 'Runner installation needs at least 2 GiB of free space.' >&2
  exit 1
fi
temporary_dir=$(mktemp -d /tmp/cortex-runner-install.XXXXXXXX)
trap 'unset runner_token; rm -rf -- "$temporary_dir"' EXIT
echo 'Downloading the official Linux runner and verifying its SHA-256 digest...'
curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
  https://api.github.com/repos/actions/runner/releases/latest > "$temporary_dir/release.json"
python3 - "$temporary_dir/release.json" "$temporary_dir/asset.txt" <<'ASSET'
import json, re, sys
release = json.load(open(sys.argv[1]))
assets = [a for a in release['assets'] if re.fullmatch(r'actions-runner-linux-x64-[0-9.]+\.tar\.gz', a['name'])]
if len(assets) != 1:
    raise SystemExit('Expected one official Linux x64 runner archive')
asset = assets[0]
digest = asset.get('digest') or ''
if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
    raise SystemExit('No official SHA-256 digest; refusing an unverified download')
url = asset['browser_download_url']
if not url.startswith('https://github.com/actions/runner/releases/download/'):
    raise SystemExit('Unexpected artifact source')
with open(sys.argv[2], 'w') as output:
    output.write(url + '\n' + digest.split(':', 1)[1] + '\n')
ASSET
mapfile -t asset_metadata < "$temporary_dir/asset.txt"
curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
  "${asset_metadata[0]}" --output "$temporary_dir/runner.tar.gz"
printf '%s  %s\n' "${asset_metadata[1]}" "$temporary_dir/runner.tar.gz" | sha256sum --check --status
mkdir -m 700 "$runner_dir"
tar --extract --gzip --file "$temporary_dir/runner.tar.gz" --directory "$runner_dir" --no-same-owner
cd "$runner_dir"
DEBIAN_FRONTEND=noninteractive ./bin/installdependencies.sh
export RUNNER_ALLOW_RUNASROOT=1
echo 'Registering the repository-specific runner...'
./config.sh --unattended --url https://github.com/abhinavkaiser/cortex --token "$runner_token" \
  --name "cortex-cloud-$(hostname)" --labels cortex-production --work _work
unset runner_token
./svc.sh install root
./svc.sh start
./svc.sh status
echo 'Runner service installed. Application files, data and services were not changed.'
'''

REMOTE_BOOTSTRAP = r'''
import json, os, subprocess, sys, tempfile
from pathlib import Path
os.umask(0o077)
bundle = json.load(sys.stdin)
with tempfile.TemporaryDirectory(prefix='cortex-runner-bootstrap-') as directory:
    script = Path(directory) / 'install.sh'
    script.write_text(bundle['script'])
    result = subprocess.run(['bash', str(script)], input=bundle['token'] + '\n', text=True)
    raise SystemExit(result.returncode)
'''


def github_cli():
    existing = shutil.which('gh')
    if existing:
        return existing
    cache = Path.home() / '.local' / 'share' / 'cortex-deployment'
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    binary = cache / 'gh'
    if binary.exists():
        return str(binary)
    machine = platform.machine()
    architecture = {'arm64': 'arm64', 'x86_64': 'amd64'}.get(machine)
    if not architecture:
        raise SystemExit('Unsupported Mac architecture: ' + machine)
    print('Installing a private copy of the official GitHub CLI...', flush=True)
    request = urllib.request.Request('https://api.github.com/repos/cli/cli/releases/latest', headers={'User-Agent': 'cortex-deployment-setup'})
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.load(response)
    assets = [a for a in release['assets'] if a['name'].endswith('_macOS_' + architecture + '.zip')]
    if len(assets) != 1:
        raise SystemExit('Could not identify the official macOS GitHub CLI archive')
    asset = assets[0]
    digest = asset.get('digest') or ''
    if not digest.startswith('sha256:') or len(digest) != 71:
        raise SystemExit('Official CLI asset has no SHA-256 digest; refusing unverified installation')
    if not asset['browser_download_url'].startswith('https://github.com/cli/cli/releases/download/'):
        raise SystemExit('Unexpected CLI artifact source')
    with tempfile.TemporaryDirectory(prefix='cortex-gh-') as directory:
        archive = Path(directory) / 'gh.zip'
        with urllib.request.urlopen(asset['browser_download_url'], timeout=90) as response, archive.open('wb') as output:
            shutil.copyfileobj(response, output)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != digest.split(':', 1)[1]:
            raise SystemExit('CLI artifact checksum mismatch')
        with zipfile.ZipFile(archive) as package:
            members = [m for m in package.infolist() if m.filename.endswith('/bin/gh')]
            if len(members) != 1 or '..' in PurePosixPath(members[0].filename).parts or members[0].filename.startswith('/'):
                raise SystemExit('Unexpected CLI archive structure')
            binary.write_bytes(package.read(members[0]))
        binary.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    return str(binary)


def main():
    if sys.platform != 'darwin':
        raise SystemExit('Run this one-time bridge on your Mac, where GitHub and SSH authentication are available.')
    gh = github_cli()
    environment = os.environ.copy()
    environment.pop('GH_DEBUG', None)
    environment['GH_PAGER'] = 'cat'
    environment.pop('GH_PROMPT_DISABLED', None)
    if subprocess.run([gh, 'auth', 'status', '--hostname', 'github.com'], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        print('Approve the GitHub CLI browser login if prompted. No token needs to be copied.', flush=True)
        subprocess.run([gh, 'auth', 'login', '--hostname', 'github.com', '--web', '--git-protocol', 'https', '--scopes', 'repo'], env=environment, check=True)

    def api(endpoint, method='GET', allow_browser_login=False):
        result = subprocess.run([gh, 'api', '--method', method, endpoint], env=environment, capture_output=True, text=True)
        if result.returncode:
            try:
                error = json.loads(result.stdout)
                detail = str(error.get('status', '')) + ': ' + error.get('message', 'request failed')
            except (json.JSONDecodeError, AttributeError):
                detail = 'request failed; verify the local GitHub login has repository administration access'
            if allow_browser_login:
                print('GitHub needs runner administration permission. Approve the GitHub CLI browser login to continue.', flush=True)
                environment.pop('GH_TOKEN', None)
                environment.pop('GITHUB_TOKEN', None)
                subprocess.run([gh, 'auth', 'login', '--hostname', 'github.com', '--web', '--git-protocol', 'https', '--scopes', 'repo'], env=environment, check=True)
                return api(endpoint, method)
            raise SystemExit('GitHub operation failed: ' + endpoint + ' (' + detail + ')')
        return json.loads(result.stdout) if result.stdout.strip() else {}

    repository = api('repos/' + REPOSITORY)
    if not repository.get('permissions', {}).get('admin'):
        raise SystemExit('The Mac GitHub login must administer ' + REPOSITORY + ' to register its runner.')
    print('Registering the runner through your Mac GitHub login...', flush=True)
    registration = api('repos/' + REPOSITORY + '/actions/runners/registration-token', 'POST', allow_browser_login=True)
    bundle = json.dumps({'script': REMOTE_INSTALLER, 'token': registration['token']})
    remote_command = shlex.join(['python3', '-c', REMOTE_BOOTSTRAP])
    print('Connecting to Hetzner. Enter your SSH password locally if asked.', flush=True)
    subprocess.run(['ssh', '-o', 'ConnectTimeout=20', '-o', 'StrictHostKeyChecking=accept-new', HOST, remote_command], input=bundle, text=True, check=True)
    del bundle, registration
    for attempt in range(30):
        runners = api('repos/' + REPOSITORY + '/actions/runners')['runners']
        matching = [r for r in runners if r['status'] == 'online' and any(label['name'] == 'cortex-production' for label in r['labels'])]
        if matching:
            print('GitHub runner is ONLINE: ' + ', '.join(r['name'] for r in matching), flush=True)
            print('Setup is complete. Codex can now verify and use the queued server-access workflow.', flush=True)
            return
        if attempt % 5 == 0:
            print('Waiting for GitHub to report the runner online...', flush=True)
        time.sleep(2)
    raise SystemExit('Runner service was installed, but GitHub has not reported it online yet. Share this status with Codex; do not share credentials.')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit('Setup command failed with exit code ' + str(error.returncode))
