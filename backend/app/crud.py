from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Message

async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, username: str, password: str):
    new_user = User(username=username, password=password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def send_message(db: AsyncSession, sender_id: int, recipient_id: int, content: str) -> Message:
    new_message = Message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        content=content
    )
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    return new_message

async def get_messages_between_users(db: AsyncSession, user1_id: int, user2_id: int) -> list:
    stmt = (
        select(Message, User)
        .join(User, User.id == Message.sender_id)  # Join User to get the sender's username
        .where(
            (
                (Message.sender_id == user1_id) & (Message.recipient_id_user == user2_id)
            )
            | (
                (Message.sender_id == user2_id) & (Message.recipient_id_user == user1_id)
            )
        )
        .order_by(Message.timestamp)
    )
    result = await db.execute(stmt)
    messages = result.fetchall()

    # Prepare the result with sender's username and message content
    messages_with_names = [
        {
            'sender_name': message[1].username,  # message[1] is the User object (sender)
            'content': message[0].content,       # message[0] is the Message object
            'timestamp': message[0].timestamp,   # Timestamp of the message
        }
        for message in messages
    ]
    
    return messages_with_names

from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

async def get_latest_messages_overview(db: AsyncSession, user_id: int):
    stmt = (
        select(
            Message.content,
            Message.timestamp,
            User.username.label('sender_name')  # Get the sender's username
        )
        .join(User, User.id == Message.sender_id)  # Join User table to get the sender's name
        .where(
            (Message.sender_id == user_id) | (Message.recipient_id_user == user_id)
        )
        .group_by(
            Message.sender_id, Message.recipient_id_user
        )
        .order_by(
            Message.timestamp.desc()
        )
    )
    
    result = await db.execute(stmt)
    
    # Collect the results as a list of dictionaries with message details
    conversations = []
    for message in result.unique().all():
        conversations.append({
            "sender_name": message.sender_name,  # Include the sender's name
            "content": message.content,
            "timestamp": message.timestamp
        })
    
    return conversations
