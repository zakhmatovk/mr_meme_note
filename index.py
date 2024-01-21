import os
import json
import requests
import time
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
    role: Literal['system', 'user', 'assistant']
    text: str

class RequestGTP(TypedDict):
    modelUri: str
    completionOptions: CompletionOptions
    messages: list[MessageGPT]


class ResponseAlternativeGPT(TypedDict):
    message: MessageGPT
    status: str

class ResponseResultGPT(TypedDict):
    alternatives: list[ResponseAlternativeGPT]

class ResponseGPT(TypedDict):
    result: ResponseResultGPT





CATEGORIES = [
    'Добавить задание в TODO лист',
    'Добавить событие в календарь',
    'Записать идею для подарка',
    'Записать место, куда можно сходить',
]

CATEGORY_PROMT = '''
Ты личный ассистент пользователя и тебе нужно категоризировать действие описанное в сообщении пользователя.
В ответ только напиши категорию действия

Есть следующие категории действий:

1. **Добавить задание в TODO лист**: Если у вас есть задача, которую нужно добавить в список дел, то это действие относится к категории "Добавить задание в TODO лист".
   Пример: "Купить продукты", "Позвонить клиенту", "Написать отчет".

2. **Добавить событие в календарь**: В сообщении должно содержаться название события, его дата и время.
   Пример: "В субботу в 12 будет играть Парма с Енисеем", "23 января у Насти день рождения", "Завтра пойдем с Ромой в кино".

3. **Записать идею для подарка**: В эту категорию стоит определить сообщения с идей подарка другому человеку.
   Примеры: "Подарить Оле пылесос", "Игорь мечтает о книге", "Антон говорил про щепочницу".

4. **Записать место, куда можно сходить**: Если вы задумались о месте, которое можно посетить, то это относится к категории "Записать место, куда можно сходить".
   Примеры: "В Osoo вкусная лапша", "Ресторан", "Парк".
'''

SYSTEM_PROMT = f'''
Ты отвечаешь на сообщения пользователей и добавляешь события в их календари.
В сообщении пользователя есть описание события, дата и время его начала.
Ты должен извлечь эти данные из сообщения и положить их в json-формат, который я указал ниже.
Учти, что пользователь находится в таймзоне MSK.
Учти, что сегодня {datetime.date.today().isoformat()}

Напиши в ответе только json

Пример:
Добавь в календарь в субботу Парма играет с Енисеем в 12:00
{{
    "summary": "Парма играет с Енисеем",
    "start": "2023-01-20T12:00:00+03:00",
}}
'''

def make_request(promt_text: str, message_text: str) -> requests.Response:
    promt: RequestGTP = {
        'modelUri': f'gpt://{FOLDER_ID}/yandexgpt/latest',
        'completionOptions': {
            'stream': False,
            'temperature': 0.0,
            'maxTokens': 2000
        },
        'messages': [
            {
                'role': 'system',
                'text': promt_text
            },
            {
                'role': 'user',
                'text': message_text
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
    return response

def get_text(r: ResponseGPT) -> str:
    for it in r['result']['alternatives']:
        return it['message']['text']
    return ''

def process_message(message_text: str) -> str:
    response = make_request(promt_text=CATEGORY_PROMT, message_text=message_text)
    if response.status_code != 200:
        return response.text

    message = []
    try:
        category = get_text(response.json())
        message.append('<pre language="json">')
        message.append(category)
        message.append('</pre>')
    except Exception:
        message.append('<pre language="json">')
        message.append(response.text)
        message.append('</pre>')
        return '\n'.join(map(str, message))

    if category not in CATEGORIES:
        return f'Подобрал несуществующую категорию действия:\n<pre language="json">{response.text}</pre>'

    if category == 'Добавить событие в календарь':
        response = make_request(promt_text=SYSTEM_PROMT, message_text=message_text)
        message.append(str(response.status_code))
        try:
            message.append('<pre language="json">')
            message.append(get_text(response.json()))
            message.append('</pre>')
        except Exception:
            message.append('<pre language="json">')
            message.append(response.text)
            message.append('</pre>')
        return '\n'.join(map(str, message))
    return response.text

def handler(event: Event, context):
    body: dict = json.loads(event['body'])
    _body = EventBody(**body)

    if not _body.message:
        return {
            'statusCode': 200,
        }

    return {
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'method': 'sendMessage',
            'chat_id': _body.message.chat.id,
            'text':  process_message(_body.message.text),
            'parse_mode': 'html'
        }),
        'statusCode': 200,
    }
