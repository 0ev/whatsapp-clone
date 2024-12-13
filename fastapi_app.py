from fastapi import FastAPI, WebSocket
from kafka import KafkaConsumer
import asyncio
import json

app = FastAPI()

# Kafka consumer setup
consumer = KafkaConsumer(
    'message_topic',
    bootstrap_servers='localhost:9093',
    api_version=(0, 10, 1),
    group_id='message_group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        # Consume Kafka messages
        message = consumer.poll(timeout_ms=1000)
        if message:
            for msg in message.values():
                for m in msg:
                    await websocket.send_text(f"New message: {m.value['message']}")
        await asyncio.sleep(1)