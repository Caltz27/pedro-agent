"""The small agent loop, independent of its chat interface."""
import json
import os
from pathlib import Path
import subprocess

from check_api import TOOL, request_completion

ROOT = Path(__file__).resolve().parent


def new_conversation():
    return [{'role': 'system', 'content': (ROOT / 'system_prompt.md').read_text(encoding='utf-8')}]


def run_command(command):
    shell = ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command'] if os.name == 'nt' else ['bash', '-lc']
    try:
        result = subprocess.run(shell + [command], cwd=ROOT, capture_output=True,
                                text=True, errors='replace', timeout=60)
        output = result.stdout + result.stderr
        return json.dumps({'output': output[-10000:], 'exit_code': result.returncode,
                           'truncated': len(output) > 10000})
    except subprocess.TimeoutExpired:
        return json.dumps({'output': 'Command timed out after 60 seconds.', 'exit_code': None})
    except OSError as error:
        return json.dumps({'output': str(error), 'exit_code': None})


def chat_turn(settings, messages, user_text, approve, emit):
    """approve(command) returns a boolean; emit(kind, data) updates the UI."""
    messages.append({'role': 'user', 'content': user_text})
    for round_number in range(21):
        # 1. Resend the whole conversation and the one tool definition.
        result = request_completion(settings, messages=messages, tools=[TOOL])
        emit('usage', result.get('usage') or {})
        reply = result['choices'][0]['message']
        calls = reply.get('tool_calls') or []
        # 2. Save the assistant reply, including IDs for any requested tools.
        message = {'role': 'assistant', 'content': reply.get('content')}
        if calls:
            message['tool_calls'] = calls
        messages.append(message)
        if reply.get('content'):
            emit('assistant', reply['content'])
        # 3. A reply with no tool calls ends this turn.
        if not calls:
            return
        # 4. Approve each command, run it, and append its matching tool result.
        for call in calls:
            try:
                command = json.loads(call['function']['arguments'])['command']
                if call['function']['name'] != 'bash' or not isinstance(command, str):
                    raise ValueError('Invalid bash call')
                if round_number == 20:
                    output = 'Tool round limit reached. No command executed.'
                elif approve(command):
                    emit('command', command)
                    output = run_command(command)
                else:
                    emit('command', command + '\n[Denied]')
                    output = 'The user declined to run this command.'
            except (ValueError, KeyError, TypeError):
                output = 'Invalid tool arguments. Expected bash with a string command.'
            emit('tool', output)
            messages.append({'role': 'tool', 'tool_call_id': call['id'], 'content': output})
        # 5. Loop again so the model sees the tool results.
        if round_number == 20:
            emit('assistant', 'Stopped after 20 tool rounds. Send another message to continue.')
            return
