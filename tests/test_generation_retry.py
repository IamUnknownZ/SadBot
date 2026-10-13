import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from services.conversation import generation_provider


class ProviderFailure(Exception):
    def __init__(self, code):
        self.code = code


class GenerationRetryTests(unittest.TestCase):
    def test_transient_service_error_retries_gemini_and_returns_its_json(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.models.generate_content.side_effect = [ProviderFailure(503), SimpleNamespace(text='{"mode":"direct"}')]
        with patch('google.genai.Client', return_value=client), patch('time.sleep'):
            result = generation_provider('test-key', 'test-model')('question')
        self.assertEqual(result, {'mode': 'direct'})
        self.assertEqual(client.models.generate_content.call_count, 2)

    def test_permanent_error_is_not_retried_or_exposed_with_sensitive_details(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.models.generate_content.side_effect = ProviderFailure(403)
        with patch('google.genai.Client', return_value=client):
            with self.assertRaisesRegex(ValueError, r'Model unavailable \(status 403\)'):
                generation_provider('test-key', 'test-model')('question')
        self.assertEqual(client.models.generate_content.call_count, 1)

    def test_transient_retries_stop_after_two_attempts(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.models.generate_content.side_effect = ProviderFailure(503)
        with patch('google.genai.Client', return_value=client), patch('time.sleep'):
            with self.assertRaisesRegex(ValueError, 'status 503'):
                generation_provider('test-key', 'test-model')('question')
        self.assertEqual(client.models.generate_content.call_count, 2)

    def test_fallback_key_runs_the_same_model_after_primary_key_cannot_reach_gemini(self):
        primary = MagicMock()
        primary.__enter__.return_value = primary
        primary.models.generate_content.side_effect = ProviderFailure(503)
        fallback = MagicMock()
        fallback.__enter__.return_value = fallback
        fallback.models.generate_content.return_value = SimpleNamespace(text='{"mode":"interpret"}')
        def client_for_key(*, api_key, http_options):
            return primary if api_key == 'primary-key' else fallback
        with patch('google.genai.Client', side_effect=client_for_key), patch('time.sleep'):
            result = generation_provider('primary-key', 'test-model', fallback_key='backup-key')('question')
        self.assertEqual(result, {'mode': 'interpret'})
        self.assertEqual(primary.models.generate_content.call_count, 2)
        self.assertEqual(fallback.models.generate_content.call_count, 1)

    def test_fast_translation_policy_tries_each_key_once_with_short_timeout(self):
        primary = MagicMock()
        fallback = MagicMock()
        primary.__enter__.return_value = primary
        fallback.__enter__.return_value = fallback
        primary.models.generate_content.side_effect = ProviderFailure(503)
        fallback.models.generate_content.return_value = SimpleNamespace(text='{"translations":[]}')
        options=[]
        def client_for_key(*, api_key, http_options):
            options.append(http_options)
            return primary if api_key == 'primary-key' else fallback
        with patch('google.genai.Client', side_effect=client_for_key):
            result = generation_provider('primary-key', 'test-model', fallback_key='backup-key',
                timeout_ms=15000, transient_attempts=1)('translate')
        self.assertEqual(result, {'translations': []})
        self.assertEqual(primary.models.generate_content.call_count, 1)
        self.assertEqual(fallback.models.generate_content.call_count, 1)
        self.assertTrue(all(option.timeout == 15000 for option in options))

    def test_flash_lite_2_5_disables_thinking_for_fast_structured_work(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.models.generate_content.return_value = SimpleNamespace(text='{"ok":true}')
        with patch('google.genai.Client', return_value=client):
            generation_provider('test-key', 'gemini-2.5-flash-lite')('question')
        config=client.models.generate_content.call_args.kwargs['config']
        self.assertEqual(config.thinking_config.thinking_budget,0)
