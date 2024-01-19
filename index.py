import os
import json
import requests
import datetime
from typing import Literal, TypedDict
from pydantic import BaseModel

YA_GPT_API_TOKEN = os.environ['YA_GPT_API_TOKEN']
FOLDER_ID = 'b1gac1g0nm3qptu01u57'

class Event(TypedDict):
    body: str

class Chat(BaseModel):
    id: int

class Message(BaseModel):
    chat: Chat
    text: str

class EventBody(BaseModel):
    message: Message | None


class CompletionOptions(TypedDict):
    stream: bool
    temperature: float
    maxTokens: int

class MessageGPT(TypedDict):
    role: Literal['system', 'user']
    text: str

class RequestGTP(TypedDict):
    modelUri: str
    completionOptions: CompletionOptions
    messages: list[MessageGPT]

SYSTEM_PROMT = f'''
Сегодня {datetime.date.today()}.
Таймзона МСК.
Выходной формат для даты YYYY-MM-DD HH:MM:SS
Вытащи из сообщения пользователя ключи: "summary", "start", "end" и предоставь ответ в виде json
'''

async def handler(event: Event, context):
    body: dict = json.loads(event['body'])
    _body = EventBody(**body)

    if not _body.message:
        return {
            'statusCode': 200,
        }

    promt: RequestGTP = {
        'modelUri': f'gpt://{FOLDER_ID}/yandexgpt-lite',
        'completionOptions': {
            'stream': False,
            'temperature': 0.0,
            'maxTokens': 2000
        },
        'messages': [
            {
                'role': 'system',
                'text': SYSTEM_PROMT
            },
            {
                'role': 'user',
                'text': _body.message.text
            }
        ]
    }

    response: requests.Response = requests.post(
        url='https://llm.api.cloud.yandex.net/foundationModels/v1/completion',
        json=promt,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {YA_GPT_API_TOKEN}"
        }
    )

    message = f'{response.status_code}\n'
    message += '```response\n' + response.text + '```'

    return {
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'method': 'sendMessage',
            'chat_id': _body.message.chat.id,
            'text':  message,
            'parse_mode': 'html'
        }),
        'statusCode': 200,
    }
