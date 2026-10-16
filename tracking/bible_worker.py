# SPDX-License-Identifier: GPL-2.0-or-later
"""Continuous offline speech-to-Bible worker using operator-selected OBS audio."""
import base64
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time
from bible_index import BibleIndex


def verse_data(verse):
    return dict(asdict(verse), title=verse.title)


class SpeechSession:
    def __init__(self, index, recognizer, clock=time.monotonic):
        self.index=index
        self.recognizer=recognizer
        self.clock=clock
        self.history=[]
        self.last=None
        self.last_time=0

    def audio(self, pcm):
        if not isinstance(pcm,bytes) or len(pcm)>64000 or len(pcm)%2:
            raise ValueError('Expected bounded mono 16 kHz signed 16-bit PCM')
        if not self.recognizer.AcceptWaveform(pcm): return None
        result=json.loads(self.recognizer.Result())
        text=str(result.get('text','')).strip()
        if not text: return None
        self.history=(self.history+[text])[-3:]
        resolved=self.index.resolve(text)
        if resolved['kind']=='none': resolved=self.index.resolve(' '.join(self.history)[-500:])
        if resolved['kind']!='none': self.history=[]
        event={'transcript':text,'kind':resolved['kind'],'translation':self.index.translation}
        if resolved['verse']:
            signature=resolved['verse'].title
            if signature==self.last and self.clock()-self.last_time<10: return {'transcript':text,'kind':'duplicate'}
            self.last,self.last_time=signature,self.clock()
            event['verse']=verse_data(resolved['verse'])
        event['suggestions']=[dict(verse_data(verse),score=round(score,3)) for score,verse in resolved['suggestions']]
        return event


def emit(**event):
    print(json.dumps(event,ensure_ascii=True),flush=True)


def main():
    from vosk import Model, KaldiRecognizer, SetLogLevel
    SetLogLevel(-1)
    first=sys.stdin.readline(65537)
    config=json.loads(first)
    bible=Path(config['bible'])
    if bible.stat().st_size>32*1024*1024: raise ValueError('Bible file too large')
    index=BibleIndex(json.loads(bible.read_text(encoding='utf-8-sig')))
    model=Model(str(config['model']))
    recognizer=KaldiRecognizer(model,16000)
    session=SpeechSession(index,recognizer)
    emit(status='A ouvir continuamente a fonte selecionada.',ready=True)
    for line in sys.stdin:
        if len(line)>100000: continue
        try:
            command=json.loads(line)
            action=command.get('action')
            if action=='quit': break
            if action=='audio':
                pcm=base64.b64decode(command.get('pcm',''),validate=True)
                event=session.audio(pcm)
                if event: emit(**event)
        except (ValueError,TypeError,KeyError):
            emit(status='Bloco de áudio inválido; a escuta continua.')


if __name__=='__main__':
    try:
        if '--self-test' in sys.argv:
            from vosk import Model, KaldiRecognizer, SetLogLevel
            SetLogLevel(-1)
            root=Path(getattr(sys,'_MEIPASS',Path(__file__).parent/'models'))
            model=Model(str(root/'speech-model'))
            recognizer=KaldiRecognizer(model,16000)
            recognizer.AcceptWaveform(bytes(32000))
            assert not json.loads(recognizer.FinalResult()).get('text')
            emit(status='Packaged speech model loads and handles silence.')
        else:
            main()
    except Exception:
        emit(error=True,status='Não foi possível iniciar a Bíblia por voz. Verifique o modelo e o JSON da tradução.')
        sys.exit(1)
