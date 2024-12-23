from fastapi import FastAPI, WebSocket, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.crud import get_user_by_username, create_user, send_message_db, get_messages_between_users, get_username_by_id , get_latest_messages_overview

from app.tools.encryption import hash_password, verify_password
from app.tools.token import create_access_token, verify_jwt_token
from app.tools.misc import sort_and_convert_to_string

from kafka import KafkaConsumer, TopicPartition, KafkaProducer

import json
from datetime import datetime

KAFKA_BROKER = 'kafka:9093'

app = FastAPI()
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)
@app.post("/register")
async def create_new_user(user: dict, db: AsyncSession = Depends(get_db)):
    existing_user = await get_user_by_username(db, user["username"])
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = await create_user(db, user["username"], hash_password(user["password"]))
    return {"message": "Registration successful"}

@app.post("/login")
async def login_user(login_request: dict, response: Response, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_username(db, login_request["username"])
    if not user or not verify_password(login_request["password"], user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    response.set_cookie(key="token", value=create_access_token({"id":user.id, "username":user.username}), httponly=True)
    return {"message": "Login successful"}

@app.post("/send")
async def send_message(send_message_request: dict, response: Response, db: AsyncSession = Depends(get_db)):
    if "token" not in send_message_request:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token is missing")
    token_payload=verify_jwt_token(send_message_request["token"])
    if "receiver_id" not in send_message_request:
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail="sender_id is missing")
    if "content" not in send_message_request:
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail="content is missing")

    message = await send_message_db(db, token_payload["id"], send_message_request["receiver_id"], send_message_request["content"])
    
    payload={
        "sender_id":message.sender_id,
        "receiver_id":message.recipient_id_user,
        "content":message.content,
        "timestamp":message.timestamp.isoformat()
    }
    #topic=sort_and_convert_to_string(message.sender_id, message.recipient_id_user)
    
    producer.send(str(message.recipient_id_user), value=payload)

    return {"message": "Message is sent succesfully", "message_sent":message}

@app.get("/messages")
async def messages(messages_body: dict, response: Response, db: AsyncSession = Depends(get_db)):
    if "token" not in messages_body:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token is missing")
    token_payload=verify_jwt_token(messages_body["token"])
    if "partner_id" not in messages_body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="partner_id is missing")

    partner_id= messages_body["partner_id"]
    user_id=token_payload["id"]
    topic = str(user_id)
    print("before kafka")
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_BROKER,
        group_id=topic,
        auto_offset_reset='latest',
        enable_auto_commit=True,
        consumer_timeout_ms=1000,
    )
    consumer.subscribe([topic])  # Ensure the consumer is subscribed
    print("after kafka")

    timeout_ms = 10  # Set a small timeout to avoid blocking
    while not consumer.assignment():
        print("Waiting for partition assignment...")
        consumer.poll(timeout_ms=500)  # Increase timeout to 500ms or more

    # Once partitions are assigned, seek to the end (latest offset) for each partition
    for partition in consumer.assignment():
        consumer.seek_to_end(partition)
    consumer.close()

    messages = await get_messages_between_users(db, user_id, partner_id)
    partner_username=await get_username_by_id(db,partner_id)
    print(messages)
    return {"messages":messages, "partner_username":partner_username, "user_username":token_payload["username"]}

    
@app.get("/messages/overview")
async def messages_overview(messages_body: dict, db: AsyncSession = Depends(get_db)):
    if "token" not in messages_body:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token is missing")

    token_payload = verify_jwt_token(messages_body["token"])

    # Validate user_id in token payload
    user_id = token_payload.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token payload")

    conversations = await get_latest_messages_overview(db, user_id)

    return {"conversations": conversations}


@app.get("/refresh")
async def refresh (request_body: dict, response: Response, db: AsyncSession = Depends(get_db)):
    if "token" not in request_body:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token is missing")
    token_payload=verify_jwt_token(request_body["token"])
    if "partner_id" not in request_body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="partner_id is missing")

    user_id=token_payload["id"]
    partner_id=request_body["partner_id"]
    consumer = KafkaConsumer(
        str(user_id),
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset='earliest',
        group_id=str(user_id)
    )

    messages = []
    timeout = 250
    while True:
        msg_batch = consumer.poll(timeout_ms=timeout)
        consumer.commit()

        if msg_batch:
            for partition, messages_list in msg_batch.items():
                for msg in messages_list:

                    message_content = msg.value.decode('utf-8')  # Assuming the message is UTF-8 encoded

                    try:
                        message_json = json.loads(message_content)
                        if message_json.get("sender_id")!=partner_id:
                            continue
                        print(message_content)
                        content=message_json.get('content')
                        timestamp=message_json.get('timestamp')

                        message={"content":content,
                            "timestamp":timestamp
                        }

                    except json.JSONDecodeError:
                        print(f"Failed to parse message as JSON: {message_content}")

                    messages.append(message)
                    print(f"Consumed message: {message}")
        
        else:  # No messages in the batch, meaning no more messages left to consume
            print("No more messages available.")
            break

    consumer.close()
    print(messages)
    return {"messages":messages}


@app.get("/search_db")
async def search_user(search_body: dict, db: AsyncSession = Depends(get_db)):
    if "token" not in search_body:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is missing")
    token_payload = verify_jwt_token(search_body["token"])

    user_id = token_payload.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token payload")
    username = search_body.get("username")
    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is required")

    user = await get_user_by_username(db, username)
    # if not users:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Username {username} not found")
    if user:
        return {"results": [{"id": user.id, "username": user.username}]}
    else:
        return {"results": []}
    # return {"results": [{"id": user.id, "username": user.username} for user in users]}


@app.get("/user/{user_id}")
async def user_by_id(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {"id": user.id, "name": user.username}

