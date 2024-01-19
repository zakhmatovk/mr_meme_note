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

SYSTEM_PROMT = '''
Ты отвечаешь на сообщения пользователей и добавляешь события в их календари. В сообщении пользователя есть описание события, дата и время его начала. Ты должен извлечь эти данные из сообщения и положить их в json-формат, который я указал ниже.

Напиши в ответе только json

Пример:
Добавь в календарь в субботу Парма играет с Енисеем в 12:00
{
    "summary": "Парма играет с Енисеем",
    "start": "2023-01-20T12:00:00+03:00",
}
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
    try:
        response_json = response.json()
        for it in response_json['result']['alternatives']:
            message += '<pre language="json">' + it['message']['text'] + '</pre>'
    except Exception:
        message += '<pre language="json">' + response.text + '</pre>'

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
