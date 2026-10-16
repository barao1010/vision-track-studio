# SPDX-License-Identifier: GPL-2.0-or-later
"""Update only this native distribution, using HTTPS and GitHub asset SHA-256."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import urllib.parse
import urllib.request

REPOSITORY='barao1010/vision-track-studio'
ASSET='Vision-Track-Studio-Setup-preview.exe'
API=f'https://api.github.com/repos/{REPOSITORY}/releases?per_page=100'
MAX_SIZE=1024*1024*1024


def valid_asset(url, digest):
    parsed=urllib.parse.urlsplit(url)
    prefix=f'/{REPOSITORY}/releases/download/'
    parts=parsed.path.removeprefix(prefix).split('/')
    return (parsed.scheme=='https' and parsed.netloc=='github.com' and not parsed.query and not parsed.fragment
            and parsed.path.startswith(prefix) and len(parts)==2
            and re.fullmatch(r'v0\.1\.0-preview\.\d+',parts[0]) is not None and parts[1]==ASSET
            and re.fullmatch(r'sha256:[0-9a-f]{64}',digest) is not None)


def select_release(releases, current):
    choices=[]
    for release in releases:
        if release.get('draft'): continue
        tag=release.get('tag_name','')
        match=re.fullmatch(r'v0\.1\.0-preview\.(\d+)',tag)
        if not match or int(match[1])<=current: continue
        for asset in release.get('assets',[]):
            url,digest=asset.get('browser_download_url',''),asset.get('digest','') or ''
            if asset.get('name')==ASSET and valid_asset(url,digest) and 0<int(asset.get('size',0))<=MAX_SIZE:
                choices.append({'build':int(match[1]),'version':tag,'url':url,'digest':digest,'size':int(asset['size'])})
    return max(choices,key=lambda r:r['build']) if choices else None


class SecureRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme!='https': raise ValueError('Insecure update redirect')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def open_https(url):
    request=urllib.request.Request(url,headers={'User-Agent':'VisionTrackStudio-Updater','Accept':'application/vnd.github+json'})
    return urllib.request.build_opener(SecureRedirect).open(request,timeout=30)


def check(current):
    with open_https(API) as response: data=response.read(4*1024*1024+1)
    if len(data)>4*1024*1024: raise ValueError('Release metadata exceeds limit')
    releases=json.loads(data)
    if not isinstance(releases,list): raise ValueError('Invalid release metadata')
    offer=select_release(releases,int(current))
    return {'offer':offer,'status':'Atualização disponível.' if offer else 'Nenhuma atualização nativa verificada disponível.'}


def download(url,digest,opener=open_https):
    if not valid_asset(url,digest): raise ValueError('Invalid update asset')
    folder=Path(tempfile.mkdtemp(prefix='vision-track-update-'))
    path=folder/ASSET
    try:
        sha=hashlib.sha256()
        total=0
        with opener(url) as response, path.open('xb') as output:
            while True:
                block=response.read(1024*1024)
                if not block: break
                total+=len(block)
                if total>MAX_SIZE: raise ValueError('Update exceeds size limit')
                sha.update(block)
                output.write(block)
        if total==0 or 'sha256:'+sha.hexdigest()!=digest: raise ValueError('Update checksum mismatch')
        return {'installer':str(path),'status':'Atualização verificada. Pronta para instalar.'}
    except Exception:
        shutil.rmtree(folder,ignore_errors=True)
        raise
