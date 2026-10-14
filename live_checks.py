"""Development checks: allow only the exact read-only commands requested here."""
from agent import chat_turn, new_conversation
from check_api import load_settings, show_usage

ALLOWED = {
    'Get-ChildItem -Name',
    'doesnotexist',
}


def approve(command):
    decision = command.strip() in ALLOWED
    print('APPROVED' if decision else 'DENIED', command, flush=True)
    return decision


def emit(kind, data):
    if kind == 'usage':
        show_usage({'usage': data})
    else:
        print(kind, data, flush=True)


if __name__ == '__main__':
    settings = load_settings()
    messages = new_conversation()
    tasks = [
        'What files are in this folder? Use exactly: Get-ChildItem -Name',
        'Run exactly doesnotexist once and explain the error. Do not retry it.',
    ]
    for task in tasks:
        print('\nTASK:', task, flush=True)
        chat_turn(settings, messages, task, approve, emit)
