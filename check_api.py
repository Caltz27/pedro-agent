"""Check chat and tool calling without executing commands or printing secrets."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def load_settings():
    for line in Path(__file__).with_name('.env').read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            name, value = line.split('=', 1)
            os.environ.setdefault(name.strip(), value.strip().strip('\"\''))
    settings = {name: os.environ.get(name, '') for name in ('BASE_URL', 'API_KEY', 'MODEL')}
    if not all(settings.values()) or settings['API_KEY'] == 'replace-with-your-key':
        raise ValueError('Set BASE_URL, API_KEY, and MODEL in .env first.')
    return settings


def request_completion(settings, **payload):
    request = Request(
        settings['BASE_URL'].rstrip('/') + '/chat/completions',
        data=json.dumps({'model': settings['MODEL'], **payload}).encode(),
        headers={'Authorization': 'Bearer ' + settings['API_KEY'], 'Content-Type': 'application/json'},
        method='POST',
    )
    with urlopen(request, timeout=90) as response:
        result = json.load(response)
    if 'error' in result:
        raise ValueError('Provider returned an API error; check OpenRouter activity.')
    return result


def show_usage(result):
    usage = result.get('usage') or {}
    details = usage.get('prompt_tokens_details') or {}
    print('Tokens: input={}, cached={}, output={}'.format(
        usage.get('prompt_tokens', 'not reported'),
        details.get('cached_tokens', 'not reported'),
        usage.get('completion_tokens', 'not reported'),
    ))


TOOL = {'type': 'function', 'function': {
    'name': 'bash',
    'description': 'Run a shell command. On Windows commands use PowerShell.',
    'parameters': {'type': 'object', 'properties': {'command': {'type': 'string'}},
                   'required': ['command'], 'additionalProperties': False},
}}


def main():
    settings = load_settings()
    print('Configuration loaded. API key is hidden.')
    result = request_completion(settings, messages=[{'role': 'user', 'content': 'Reply with one short greeting.'}])
    message = result['choices'][0]['message']
    if not message.get('content'):
        raise ValueError('Plain chat check returned no text.')
    print('Plain chat: PASS (text response received)')
    show_usage(result)
    result = request_completion(settings,
        messages=[{'role': 'user', 'content': 'Use bash to print hello. Do not answer with text.'}],
        tools=[TOOL], tool_choice={'type': 'function', 'function': {'name': 'bash'}})
    calls = result['choices'][0]['message'].get('tool_calls') or []
    if not calls:
        raise ValueError('Tool check returned no tool call; choose a different model.')
    for call in calls:
        arguments = json.loads(call['function']['arguments'])
        if call['function']['name'] != 'bash' or not isinstance(arguments.get('command'), str):
            raise ValueError('Tool check returned an invalid bash call.')
    print('Tool calling: PASS (valid bash call received; no command executed)')
    show_usage(result)


if __name__ == '__main__':
    try:
        main()
    except HTTPError as error:
        print(f'API check failed: HTTP {error.code}. Check key, model, credits, or rate limits.')
        raise SystemExit(1)
    except URLError:
        print('API check failed: network connection unavailable.')
        raise SystemExit(1)
    except (ValueError, KeyError, IndexError) as error:
        print(f'API check failed: {error}')
        raise SystemExit(1)
