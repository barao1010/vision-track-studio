# SPDX-License-Identifier: GPL-2.0-or-later
import json
import unittest
from bible_index import BibleIndex
from bible_worker import SpeechSession


class Recognizer:
    def __init__(self,results): self.results=iter(results);self.current=None
    def AcceptWaveform(self,pcm): self.current=next(self.results);return self.current is not None
    def Result(self): return json.dumps({'text':self.current})


class SpeechSessionTests(unittest.TestCase):
    def index(self):
        return BibleIndex({'translation':'Fixture','license':'CC0 authored fixture','verses':[
            {'book':'João','chapter':3,'verse':16,'text':'Teste do reconhecimento contínuo de uma passagem'}]})

    def test_silence_does_not_stop_next_recognition(self):
        session=SpeechSession(self.index(),Recognizer([None,'','João três dezasseis']))
        self.assertIsNone(session.audio(b'\0'*3200))
        self.assertIsNone(session.audio(b'\0'*3200))
        self.assertEqual(session.audio(b'\0'*3200)['verse']['title'],'João 3:16')

    def test_reference_split_across_utterances(self):
        session=SpeechSession(self.index(),Recognizer(['João capítulo três','versículo dezesseis']))
        self.assertEqual(session.audio(b'\0'*3200)['kind'],'none')
        self.assertEqual(session.audio(b'\0'*3200)['verse']['title'],'João 3:16')

    def test_repeated_reference_is_throttled(self):
        session=SpeechSession(self.index(),Recognizer(['João 3 16']*2),clock=lambda:1)
        self.assertIn('verse',session.audio(b'\0'*3200))
        self.assertEqual(session.audio(b'\0'*3200)['kind'],'duplicate')

    def test_unrelated_speech_does_not_replay_old_reference(self):
        session=SpeechSession(self.index(),Recognizer(['João 3 16','agora vamos falar de um assunto diferente']),clock=lambda:20)
        self.assertIn('verse',session.audio(b'\0'*3200))
        self.assertEqual(session.audio(b'\0'*3200)['kind'],'none')

    def test_malformed_audio_is_rejected(self):
        session=SpeechSession(self.index(),Recognizer([]))
        for pcm in [b'x',b'\0'*64002]:
            with self.assertRaises(ValueError): session.audio(pcm)
