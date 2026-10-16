# SPDX-License-Identifier: GPL-2.0-or-later
import unittest
from unittest.mock import patch, Mock
from exercise import OBSClient


class ClientReadinessTests(unittest.TestCase):
    def test_startup_not_ready_is_retried_then_returns_real_response(self):
        client=object.__new__(OBSClient)
        client._call_once=Mock(side_effect=[
            {'requestStatus':{'result':False,'code':207}},
            {'requestStatus':{'result':True,'code':100},'responseData':{'obsWebSocketVersion':'5.7.6'}}])
        with patch('exercise.time.sleep'):
            result=client.call('GetVersion')
        self.assertEqual(result['obsWebSocketVersion'],'5.7.6')
        self.assertEqual(client._call_once.call_count,2)

    def test_other_errors_are_not_retried_or_hidden(self):
        client=object.__new__(OBSClient)
        client._call_once=Mock(return_value={'requestStatus':{'result':False,'code':601}})
        with self.assertRaises(AssertionError): client.call('SetCurrentProgramScene',sceneName='Missing')
        self.assertEqual(client._call_once.call_count,1)

    def test_readiness_timeout_remains_a_failure(self):
        client=object.__new__(OBSClient)
        client._call_once=Mock(return_value={'requestStatus':{'result':False,'code':207}})
        with patch('exercise.time.monotonic',side_effect=[0,31]):
            with self.assertRaises(AssertionError): client.call('GetVersion')
