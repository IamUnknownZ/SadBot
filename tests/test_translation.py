import unittest
from services import translation

class TranslationTests(unittest.TestCase):
    def test_masks_use_ascii_markers_that_a_text_model_can_copy_exactly(self):
        masked,kept=translation.mask_source(dict(
            text='Read A[i] only after the boundary check. Strict > keeps stability.',
            protected_spans=[]))
        self.assertIn('__KEEP_0__', masked)
        self.assertTrue(all(marker.startswith('__KEEP_') for marker,_ in kept))
        self.assertIn('>', [value for _,value in kept])

    def test_dropped_or_changed_protected_content_falls_back_to_source(self):
        row=dict(id='one',text='It needs 10 comparisons and O(n) time.',kind='paragraph',protected_spans=['O(n)'])
        result=translation.translate_passages([row],generate=lambda prompt:{'translations':[{'id':'one','text':'ใช้เวลาเร็วมาก'}]})
        self.assertEqual(result['one']['text'],row['text'])
        self.assertFalse(result['one']['translated'])

    def test_valid_translation_restores_exact_numbers_and_formulas(self):
        row=dict(id='one',text='It needs 10 comparisons and O(n) time.',kind='paragraph',protected_spans=['O(n)'])
        def generate(prompt):
            import json
            data=json.loads(prompt);text=data['passages'][0]['text']
            return {'translations':[{'id':'one','text':text.replace('It needs','ต้องใช้').replace('comparisons and','การเปรียบเทียบ และ').replace('time.','เวลา.')}]}
        result=translation.translate_passages([row],generate=generate)
        self.assertTrue(result['one']['translated'])
        self.assertIn('10',result['one']['text']);self.assertIn('O(n)',result['one']['text'])

    def test_code_table_formula_and_uncertain_encoding_remain_verbatim(self):
        rows=[dict(id=kind,text='for i = 1 to 10\n  A[i] = 0',kind=kind,protected_spans=[]) for kind in ['code','table','formula']]
        rows.append(dict(id='bad',text='AŒj\x8d D key',kind='paragraph',protected_spans=[]))
        def forbidden(prompt):self.fail('Must not translate code or uncertain math glyphs')
        result=translation.translate_passages(rows,generate=forbidden)
        for row in rows:self.assertEqual(result[row['id']]['text'],row['text'])

    def test_labels_from_figures_remain_verbatim_and_are_not_sent_for_translation(self):
        row=dict(id='figure-label',text='domain 0 1 2 3 4 5',kind='figure_label',protected_spans=[])
        calls=[]
        result=translation.translate_passages([row],generate=lambda prompt:calls.append(prompt))
        self.assertEqual(calls,[])
        self.assertEqual(result[row['id']]['text'],row['text'])
        self.assertFalse(result[row['id']]['translated'])

    def test_missing_duplicate_or_extra_ids_are_rejected(self):
        rows=[dict(id='a',text='First statement.',kind='paragraph',protected_spans=[]),dict(id='b',text='Second statement.',kind='paragraph',protected_spans=[])]
        for output in [{'translations':[]},{'translations':[{'id':'a','text':'ก'},{'id':'a','text':'ข'}]},{'translations':[{'id':'a','text':'ก'},{'id':'b','text':'ข'},{'id':'c','text':'ค'}]}]:
            result=translation.translate_passages(rows,generate=lambda p:output)
            self.assertTrue(all(not r['translated'] for r in result.values()))

    def test_invalid_batch_is_retried_one_passage_at_a_time(self):
        import json
        rows=[
            dict(id='a',text='First explanation.',kind='paragraph',protected_spans=[]),
            dict(id='b',text='Second caption.',kind='paragraph',protected_spans=[]),
        ]
        calls=[]
        def generate(prompt):
            payload=json.loads(prompt)
            calls.append(len(payload['passages']))
            if len(payload['passages'])==2:
                return {'translations':[]}
            row=payload['passages'][0]
            return {'translations':[{'id':row['id'],'text':row['text'].replace('First','คำอธิบายแรก').replace('Second','คำบรรยายที่สอง')}]}
        result=translation.translate_passages(rows,generate=generate)
        self.assertEqual(calls,[2,1,1])
        self.assertTrue(result['a']['translated'])
        self.assertTrue(result['b']['translated'])

    def test_provider_failure_does_not_repeat_each_passage_and_multiply_wait_time(self):
        rows=[
            dict(id='a',text='First explanation.',kind='paragraph',protected_spans=[]),
            dict(id='b',text='Second caption.',kind='paragraph',protected_spans=[]),
        ]
        calls=[]
        def unavailable(prompt):
            calls.append(prompt)
            raise ValueError('Model unavailable (status 503)')
        result=translation.translate_passages(rows,generate=unavailable)
        self.assertEqual(len(calls),1)
        self.assertTrue(all(not row['translated'] for row in result.values()))

if __name__=='__main__':unittest.main()

class MathMaskTests(unittest.TestCase):
    def test_math_variable_spans_do_not_mask_letters_inside_english_words(self):
        row=dict(text='constant numbers n c1n2 2n2',protected_spans=[' n',' c','2n'])
        masked,kept=translation.mask_source(row)
        self.assertIn('constant numbers',masked)
        self.assertIn('2n2',[v for k,v in kept])

class QueryTranslationTests(unittest.TestCase):
    def test_fallback_translates_query_without_changing_numeric_input(self):
        self.assertEqual(translation.translate_query('เรียง [9,7,4]',generate=lambda p:{'english_query':'sort [1,2,3]'}),'เรียง [9,7,4]')
        self.assertEqual(translation.translate_query('ความเร็วเครื่องมีผลแค่ไหน',generate=lambda p:{'english_query':'How does computer speed affect efficiency?'}),'How does computer speed affect efficiency?')
