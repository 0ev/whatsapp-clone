from fastapi import FastAPI, WebSocket, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.crud import get_user_by_username, create_user, send_message, get_messages_between_users
from app.tools.encryption import hash_password, verify_password
from app.tools.token import create_access_token, verify_jwt_token

app = FastAPI()

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
    
    message = await send_message(db, token_payload["id"],send_message_request["receiver_id"], send_message_request["content"])
    return {"message": "Message is sent succesfully"}

@app.get("/messages")
async def messages(messages_body: dict, response: Response, db: AsyncSession = Depends(get_db)):
    if "token" not in messages_body:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token is missing")
    token_payload=verify_jwt_token(messages_body["token"])
    if "partner_id" not in messages_body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="partner_id is missing")
    
    messages = await get_messages_between_users(db, token_payload["id"], messages_body["partner_id"])
    print(messages)
    return {"messages":messages}
    
