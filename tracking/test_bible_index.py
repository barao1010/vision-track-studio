# SPDX-License-Identifier: GPL-2.0-or-later
import unittest
from bible_index import BibleIndex


class BibleLookupTests(unittest.TestCase):
    def document(self):
        return {'translation':'Fixture authored for tests','license':'CC0 fixture', 'verses':[
            {'book':'João','chapter':3,'verse':16,'text':'Frase de teste sobre amor esperança vida e mundo'},
            {'book':'1 Coríntios','chapter':13,'verse':4,'text':'Frase de teste sobre paciência bondade e amor'},
            {'book':'Salmos','chapter':23,'verse':1,'text':'Uma frase diferente usada para identificar o pastor'}]}

    def test_spoken_reference_and_abbreviation(self):
        index=BibleIndex(self.document())
        self.assertEqual(index.reference('Abra João capítulo 3 versículo 16').title,'João 3:16')
        self.assertEqual(index.reference('sl 23:1').title,'Salmos 23:1')
        self.assertEqual(index.reference('João capítulo três versículo dezasseis').title,'João 3:16')
        self.assertEqual(index.reference('Salmos vinte e três versículo um').title,'Salmos 23:1')
        self.assertEqual(index.reference('primeira corintios 13 4').title,'1 Coríntios 13:4')

    def test_missing_reference_is_not_invented(self):
        self.assertIsNone(BibleIndex(self.document()).reference('João 3:999'))

    def test_quotation_search(self):
        result=BibleIndex(self.document()).resolve('Uma frase diferente usada para identificar o pastor')
        self.assertEqual(result['kind'],'quotation')
        self.assertEqual(result['verse'].title,'Salmos 23:1')

    def test_unique_exact_excerpt_recognizes_a_verse_with_editorial_prefix(self):
        data=self.document()
        data['verses'][2]['text']='Título editorial. Uma frase diferente usada para identificar o pastor.'
        result=BibleIndex(data).resolve('Uma frase diferente usada para identificar o pastor')
        self.assertEqual(result['kind'],'quotation')
        self.assertEqual(result['verse'].title,'Salmos 23:1')

    def test_ambiguous_quotation_requires_selection(self):
        data=self.document(); row=dict(data['verses'][0]);row['verse']=17;data['verses'].append(row)
        result=BibleIndex(data).resolve(row['text'])
        self.assertEqual(result['kind'],'ambiguous')
        self.assertIsNone(result['verse'])

    def test_license_and_duplicate_validation(self):
        data=self.document();data['license']=''
        with self.assertRaises(ValueError): BibleIndex(data)
        data=self.document();data['verses'].append(data['verses'][0])
        with self.assertRaises(ValueError): BibleIndex(data)
