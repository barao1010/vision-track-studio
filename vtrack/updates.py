"""Independent-channel update discovery and checksum-verified downloads.

Only final independent-vX.Y.Z releases are eligible. Older engine previews and
experimental artifacts can never be offered by this updater.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

REPOSITORY = 'barao1010/vision-track-studio'
API = f'https://api.github.com/repos/{REPOSITORY}'


class SafeRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        if urlparse(new_url).scheme != 'https':
            raise ValueError('Redirecionamento de atualização sem HTTPS')
        redirected = super().redirect_request(request, response, code, message, headers, new_url)
        if redirected and urlparse(request.full_url).hostname != urlparse(new_url).hostname:
            redirected.remove_header('Authorization')
        return redirected


@dataclass(frozen=True)
class Update:
    version: str
    filename: str
    url: str
    sha256: str
    release_url: str


def version_tuple(value):
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)', value)
    if not match:
        raise ValueError('Versão inválida')
    return tuple(map(int, match.groups()))


class Updater:
    def __init__(self, current, token=None, fetch=None):
        self.current = current
        self.token = token if token is not None else os.environ.get('VISION_TRACK_GITHUB_TOKEN')
        self.opener = build_opener(SafeRedirects())
        self.fetch = fetch or self._fetch

    def _request(self, url, binary=False):
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname not in {'api.github.com', 'github.com'}:
            raise ValueError('Endereço de atualização não autorizado')
        headers = {'User-Agent': 'VisionTrackStudio-Updater', 'Accept': 'application/octet-stream' if binary else 'application/vnd.github+json'}
        if self.token and parsed.hostname == 'api.github.com':
            headers['Authorization'] = 'Bearer ' + self.token
        return Request(url, headers=headers)

    def _fetch(self, url, maximum=4_000_000, binary=False):
        with self.opener.open(self._request(url, binary), timeout=30) as response:
            result = response.read(maximum + 1)
        if len(result) > maximum:
            raise ValueError('Resposta de atualização demasiado grande')
        return result

    def check(self):
        releases = json.loads(self.fetch(API + '/releases?per_page=100'))
        eligible = []
        for release in releases:
            tag = release.get('tag_name', '')
            match = re.fullmatch(r'independent-v(\d+\.\d+\.\d+)', tag)
            if not match or release.get('prerelease') or release.get('draft'):
                continue
            version = match.group(1)
            if version_tuple(version) < version_tuple(self.current):
                continue
            if version_tuple(version) == version_tuple(self.current) and '-' not in self.current:
                continue
            eligible.append((version_tuple(version), version, release))
        for _, version, release in sorted(eligible, key=lambda item: item[0], reverse=True):
            filename = f'Vision-Track-Studio-{version}-Setup.exe'
            assets = {asset['name']: asset for asset in release.get('assets', [])}
            installer, sums = assets.get(filename), assets.get('SHA256SUMS.txt')
            if not installer or not sums:
                continue
            checksum_url = sums.get('url', '')
            installer_url = installer.get('url', '')
            if not checksum_url.startswith(API + '/releases/assets/') or not installer_url.startswith(API + '/releases/assets/'):
                continue
            checksums = self.fetch(checksum_url, maximum=100_000, binary=True).decode('utf-8')
            matches = re.findall(r'^([a-fA-F0-9]{64})\s+\*?' + re.escape(filename) + r'\s*$', checksums, re.MULTILINE)
            if len(matches) != 1:
                continue
            return Update(version, filename, installer_url, matches[0].lower(), release.get('html_url', ''))
        return None

    def download(self, update, folder=None):
        if not re.fullmatch(r'Vision-Track-Studio-\d+\.\d+\.\d+-Setup\.exe', update.filename):
            raise ValueError('Nome de instalador inválido')
        folder = Path(folder) if folder else Path(tempfile.gettempdir()) / 'VisionTrackStudioUpdates'
        folder.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=folder, suffix='.partial')
        temporary = Path(temporary)
        try:
            digest = hashlib.sha256()
            total = 0
            with os.fdopen(descriptor, 'wb') as output:
                with self.opener.open(self._request(update.url, binary=True), timeout=30) as response:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        total += len(block)
                        if total > 1_000_000_000:
                            raise ValueError('Instalador excede o limite de tamanho')
                        digest.update(block)
                        output.write(block)
            if digest.hexdigest() != update.sha256:
                raise ValueError('Checksum do instalador não corresponde à publicação')
            destination = folder / update.filename
            temporary.replace(destination)
            return destination
        finally:
            if temporary.exists():
                temporary.unlink()
