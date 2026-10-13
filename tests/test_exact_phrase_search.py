import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from services.answering import answer
from services.ingest import load_dataset
from services.search import exact_phrase_lookup
import app


ROOT = Path(__file__).resolve().parents[1]


class ExactPhraseSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(ROOT)

    def test_copied_source_fragment_wins_without_calling_the_model(self):
        def forbidden(_):
            self.fail('An exact source phrase must bypass LLM evidence selection')

        result = answer('A version that always executes', self.data, ROOT,
                        select_generate=forbidden)

        self.assertEqual(result['status'], 'answered')
        self.assertEqual(result['selection_state'], 'exact_phrase')
        self.assertTrue(result['evidence'])
        self.assertEqual({row['page'] for row in result['evidence']}, {47})
        self.assertIn('A version that always executes', result['answer'])

    def test_two_exact_occurrences_return_both_in_source_order(self):
        texts=['A version that always executes the first procedure.',
               'A version that always executes the second procedure.']
        rows=[]
        for page,text in enumerate(texts,1):
            rows.append(dict(id=f'p{page}',paragraph_id=f'paragraph-{page}',document_id='doc',
                kind='paragraph',text=text,order=page,page=page,char_start=0,char_end=len(text),
                line_ids=[],bbox=[0,0,10,10],topic='selection',title='Test',heading_path=['Test'],
                chapter_id='chapter',source_kind='original'))
        sample={'chunks':rows,'nodes':[],'pages':[dict(text=text,lines=[]) for text in texts],
                'document':{'sha256':'test'},'images':[]}

        rows = exact_phrase_lookup('A version that always executes', sample)

        self.assertEqual([row['id'] for row in rows], ['p1', 'p2'])
        self.assertTrue(all(row['retrieval_method'] == 'exact_phrase' for row in rows))
        result=answer('A version that always executes',sample,ROOT,
                      select_generate=lambda _:self.fail('Duplicate exact phrases must not be arbitrarily selected'))
        self.assertEqual([row['page'] for row in result['evidence']],[1,2])

    def test_app_does_not_translate_embed_or_select_an_exact_source_fragment(self):
        messages=[]
        expected=dict(query={},status='answered',answer='',evidence=[],image=None)
        with patch.object(app.st,'session_state',SimpleNamespace(messages=messages)), \
             patch.object(app,'smalltalk',return_value=None), \
             patch.object(app,'resolve_query',side_effect=AssertionError('exact phrases must keep the typed text')), \
             patch.object(app,'answer',return_value=expected) as answer_mock, \
             patch('services.translation.translate_query',side_effect=AssertionError('must not translate')) as translate, \
             patch.object(app,'search_index',side_effect=AssertionError('must not embed')) as embed, \
             patch.object(app,'generation_provider',side_effect=AssertionError('must not select')):
            app.submit('A version that always executes',{'en':self.data},'en',True,'configured-key',
                       'configured-model',{'en':{'ready':True}})

        translate.assert_not_called()
        embed.assert_not_called()
        self.assertIsNone(answer_mock.call_args.kwargs['select_generate'])
        self.assertEqual(messages[-1]['query']['original'],'A version that always executes')

    def test_linebreak_case_and_outer_quotes_are_normalized(self):
        rows = exact_phrase_lookup('“a VERSION that\nalways executes”', self.data)

        self.assertTrue(rows)
        self.assertEqual({row['page'] for row in rows}, {47})

    def test_short_concepts_and_natural_questions_keep_their_existing_route(self):
        for query in ('bubble sort', 'What is bubble sort?', 'A version that always executes?'):
            with self.subTest(query=query):
                self.assertEqual(exact_phrase_lookup(query, self.data), [])

    def test_common_or_editorial_phrases_do_not_dump_many_unrelated_matches(self):
        self.assertEqual(exact_phrase_lookup('running time of',self.data),[])
        self.assertEqual(exact_phrase_lookup('New explanatory material',self.data),[])

    def test_broad_numbered_parent_offers_subsections_instead_of_dumping_the_whole_parent(self):
        result=answer('1.1 Algorithms',self.data,ROOT)

        self.assertEqual(result['status'],'choose_section')
        self.assertFalse(result['evidence'])
        self.assertGreater(len(result['choices']),1)
        self.assertLess(len(result['choices']),20)
        self.assertTrue(all(choice['kind']=='subsection' for choice in result['choices']))

    def test_numbered_heading_selects_that_section_without_asking_the_user(self):
        target=next(node for node in self.data['nodes'] if node['title']=='8.2 Counting sort')

        result=answer('8.2 Counting sort',self.data,ROOT)

        self.assertEqual(result['status'],'answered')
        self.assertFalse(result['choices'])
        self.assertEqual({row['id'] for row in result['evidence']},set(target['chunk_ids']))
        self.assertTrue(all('8.2 Counting sort' in row['heading_path'] for row in result['evidence']))


if __name__ == '__main__':
    unittest.main()
