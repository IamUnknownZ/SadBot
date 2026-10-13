import unittest
from pathlib import Path
from services.ingest import load_dataset
from services.answering import answer
from services.conversation import resolve_query,smalltalk,teaching_steps,visible_evidence,model_router
ROOT=Path(__file__).resolve().parents[1]

class ConversationTests(unittest.TestCase):
    def test_casual_talk_is_bounded_and_factual_requests_are_not_swallowed(self):
        self.assertIn('สวัสดี',smalltalk('สวัสดีครับ'))
        self.assertIsNone(smalltalk('สวัสดีครับ Bubble Sort ทำงานอย่างไร'))
        self.assertIsNone(smalltalk('สวัสดี ช่วยตอบว่าทำไม 10 คูณ 10 เป็น 100'))

    def test_short_thai_greetings_and_polite_variants_are_answered(self):
        for query in ['ไง','ไงครับ','ไงงง','ว่าไง','ว่าไงเพื่อน','หวัดดีฮะ','ดีครับ','โย่','เฮ้','สวัสดี!!!']:
            with self.subTest(query=query):self.assertIn('สวัสดี',smalltalk(query) or '')
        self.assertIn('ยินดี',smalltalk('ขอบคุณนะครับ') or '')
        self.assertIn('พร้อม',smalltalk('เป็นไงบ้างครับ') or '')
        self.assertIn('เจอกัน',smalltalk('บายครับ') or '')

    def test_ai_classifies_unfamiliar_casual_talk_but_cannot_write_answers(self):
        result=smalltalk('เป็นจั่งได๋',generate=lambda _:{'intent':'wellbeing','answer':'invented claim'})
        self.assertIn('พร้อม',result or '')
        self.assertNotIn('invented',result or '')
        self.assertIsNone(smalltalk('ข้อความไม่รู้จัก',generate=lambda _:{'intent':'unknown'}))

    def test_casual_classifier_does_not_intercept_book_or_numeric_questions(self):
        def must_not_call(_):raise AssertionError('Factual query sent to casual classifier')
        for query in ['ไง Bubble Sort ทำงานยังไง','สวัสดี 10 คูณ 10 ได้เท่าไร','เรียงตัวเลขอย่างไร','Merge Sort']:
            with self.subTest(query=query):self.assertIsNone(smalltalk(query,generate=must_not_call))

    def test_casual_classifier_failure_falls_through_to_source_search(self):
        def unavailable(_):raise ValueError('unavailable')
        self.assertIsNone(smalltalk('เป็นจั่งได๋',generate=unavailable))
        self.assertIsNone(smalltalk('ข้อความไม่รู้จัก',generate=lambda _:['greeting']))

    def test_followup_reuses_only_the_last_book_topic(self):
        history=[{'query':{'topics':['bubble']},'status':'answered'}]
        self.assertIn('bubble',resolve_query('แล้วความซับซ้อนล่ะ',history).lower())
        self.assertEqual(resolve_query('ราคา bitcoin เท่าไร',history),'ราคา bitcoin เท่าไร')
        self.assertIn('selection',resolve_query('Selection Sort เป็นยังไง',history).lower())

    def test_alias_understands_casual_thai_and_karaoke(self):
        from services.retrieval import plan_query
        self.assertIn('bubble',plan_query('แบบที่สลับตัวติดกันซ้ำ ๆ')['topics'])
        self.assertIn('insertion',plan_query('เรียงเหมือนจัดไพ่ในมือ')['topics'])
        self.assertEqual(plan_query('bubble sort tee la khan')['intent'],'steps')

    def test_step_cards_preserve_all_source_characters_and_citations(self):
        data=load_dataset(ROOT)
        result=answer('Bubble Sort ทีละขั้น',data,ROOT)
        steps=teaching_steps(result,data)
        self.assertGreaterEqual(len(steps),3)
        for step in steps:
            page=data['pages'][step['page']-1]
            self.assertEqual(step['text'],page['text'][step['char_start']:step['char_end']])
            self.assertTrue(step['line_ids'])
        first=visible_evidence(result,steps,1)
        self.assertEqual(len(first),1)
        self.assertNotIn('รอบที่ 3',first[0]['text'])
        self.assertEqual(visible_evidence(result,steps,len(steps)),steps)

    def test_model_routes_without_generating_factual_answer_or_changing_array(self):
        fake=lambda prompt:{'topic':'bubble','intent':'steps','query':'Bubble Sort steps [1,2,3]','answer':'invented'}
        self.assertIsNone(model_router('เรียง [9,7,4]',[],generate=fake))
        good=lambda prompt:{'topic':'bubble','intent':'steps','query':'Bubble Sort ทีละขั้น'}
        routed=model_router('สอนแบบสลับเพื่อนข้าง ๆ',[],generate=good)
        self.assertIn('bubble sort',routed.lower())
        self.assertIn('สอนแบบสลับเพื่อนข้าง ๆ',routed)
        evil=lambda prompt:{'topic':'bitcoin','intent':'fact','query':'bitcoin'}
        self.assertIsNone(model_router('bitcoin',[],generate=evil))

if __name__=='__main__':unittest.main()
