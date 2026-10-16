# SPDX-License-Identifier: GPL-2.0-or-later
"""Drive both unmodified OBS and Vision through their native WebSocket API.
No production calls run under a Lua timer/event mutex.
"""
import base64
import hashlib
import json
from pathlib import Path
import time
import uuid
import websocket
from measure import measure

ROOT = Path(__file__).resolve().parent


class OBSClient:
    def __init__(self, password):
        deadline = time.monotonic()+60
        while True:
            try:
                self.socket = websocket.create_connection('ws://127.0.0.1:4455', timeout=10, http_no_proxy=['127.0.0.1'])
                break
            except OSError:
                if time.monotonic() > deadline: raise
                time.sleep(1)
        hello = json.loads(self.socket.recv())
        assert hello['op'] == 0, hello
        identify = {'rpcVersion':1,'eventSubscriptions':0}
        auth = hello['d'].get('authentication')
        if auth:
            secret = base64.b64encode(hashlib.sha256((password+auth['salt']).encode()).digest()).decode()
            identify['authentication'] = base64.b64encode(hashlib.sha256((secret+auth['challenge']).encode()).digest()).decode()
        self.socket.send(json.dumps({'op':1,'d':identify}))
        assert json.loads(self.socket.recv())['op'] == 2

    def call(self, name, **data):
        request_id = str(uuid.uuid4())
        self.socket.send(json.dumps({'op':6,'d':{'requestType':name,'requestId':request_id,'requestData':data}}))
        while True:
            message=json.loads(self.socket.recv())
            if message['op'] == 7 and message['d']['requestId'] == request_id:
                response=message['d']
                assert response['requestStatus']['result'], (name,response['requestStatus'])
                return response.get('responseData',{})

    def close(self):
        self.socket.close()


def exercise():
    config=json.loads((ROOT/'rpc-secret.json').read_text())
    client=OBSClient(config['password'])
    try:
        assert client.call('GetVersion')['obsWebSocketVersion']
        names={s['sceneName'] for s in client.call('GetSceneList')['scenes']}
        assert {'Parity 1','Parity 2','Parity 3'} <= names
        inputs={s['inputName'] for s in client.call('GetInputList')['inputs']}
        expected={'Parity Color','Parity Image','Parity Browser','Parity Audio'}
        assert expected <= inputs, inputs
        for mode in ['normal','studio']:
            result_dir=ROOT/'results'/mode
            recordings=result_dir/'recordings'
            recordings.mkdir(parents=True,exist_ok=True)
            client.call('SetStudioModeEnabled',studioModeEnabled=mode=='studio')
            assert client.call('GetStudioModeEnabled')['studioModeEnabled'] == (mode=='studio')
            client.call('SetCurrentSceneTransition',transitionName='Fade')
            client.call('SetCurrentSceneTransitionDuration',transitionDuration=300)
            assert client.call('GetCurrentSceneTransition')['transitionKind']=='fade_transition'
            client.call('SetInputMute',inputName='Parity Audio',inputMuted=True)
            assert client.call('GetInputMute',inputName='Parity Audio')['inputMuted']
            client.call('SetInputMute',inputName='Parity Audio',inputMuted=False)
            client.call('SetCurrentProgramScene',sceneName='Parity 1')
            time.sleep(1)
            client.call('StartRecord')
            try:
                time.sleep(3.5)
                assert client.call('GetRecordStatus')['outputActive']
                client.call('SetCurrentProgramScene',sceneName='Parity 2')
                time.sleep(3.5)
                client.call('SetCurrentProgramScene',sceneName='Parity 3')
                time.sleep(3.5)
            finally:
                stopped=client.call('StopRecord')
            assert not client.call('GetRecordStatus')['outputActive']
            output=Path(stopped['outputPath'])
            assert output.exists(), output
            output.replace(recordings/'exercise.mkv')
            results={k:True for k in ['color','image','browser','audio','fade','recording','stopped']}
            (result_dir/'exercise.json').write_text(json.dumps(results))
            report=measure(result_dir)
            (result_dir/'measurements.json').write_text(json.dumps(report,indent=2))
            print(mode,json.dumps(report),flush=True)
    finally:
        client.close()


if __name__=='__main__':
    exercise()
