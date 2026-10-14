"""Focused checks for approval, tool-result IDs, errors, and multi-call history."""
import json
import unittest
from unittest.mock import patch

import agent


def tool_reply(identity, command):
    return {'choices': [{'message': {'role': 'assistant', 'content': None,
        'tool_calls': [{'id': identity, 'type': 'function', 'function': {
            'name': 'bash', 'arguments': json.dumps({'command': command})}}]}}]}


class LoopTests(unittest.TestCase):
    def test_approval_and_history(self):
        replies = [tool_reply('one', 'echo hello'), tool_reply('two', 'doesnotexist'),
                   {'choices': [{'message': {'content': 'Done'}}]}]
        history = agent.new_conversation()
        with patch('agent.request_completion', side_effect=replies) as request, patch(
                'agent.run_command', return_value='hello') as run:
            decisions = iter([True, False])
            agent.chat_turn({}, history, 'Try commands', lambda _: next(decisions), lambda *_: None)
        run.assert_called_once_with('echo hello')
        self.assertEqual(request.call_count, 3)
        results = [m for m in history if m['role'] == 'tool']
        self.assertEqual([m['tool_call_id'] for m in results], ['one', 'two'])
        self.assertIn('declined', results[1]['content'])
        self.assertEqual(history[-1]['content'], 'Done')

    def test_failed_command(self):
        result = json.loads(agent.run_command('doesnotexist'))
        self.assertNotEqual(result['exit_code'], 0)
        self.assertTrue(result['output'])

    def test_output_limit(self):
        command = "Write-Output ('x' * 12000)" if agent.os.name == 'nt' else "printf '%12000s' x"
        result = json.loads(agent.run_command(command))
        self.assertEqual(len(result['output']), 10000)
        self.assertTrue(result['truncated'])


if __name__ == '__main__':
    unittest.main()
