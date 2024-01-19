import json
from typing import TypedDict
from pydantic import BaseModel

class Event(TypedDict):
    body: str

class Chat(BaseModel):
    id: int

class Message(BaseModel):
    chat: Chat
    text: str

class EventBody(BaseModel):
    message: Message | None


async def handler(event: Event, context):
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
            'text':  _body.message.text
        }),
        'statusCode': 200,
    }
