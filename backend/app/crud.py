from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Message
from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession


# async def get_user_by_username(db: AsyncSession, username: str):
#     result = await db.execute(select(User).where(User.username == username))
#     return result.scalar_one_or_none()
async def get_user_by_username(db: AsyncSession, username: str):
    try:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()  # This returns a single User object or None
        return user
    except Exception as e:
        # Optionally log the exception here if needed
        return None

async def get_user_by_id(db: AsyncSession, user_id: int):
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()  # This returns a single User object or None
        return user
    except Exception as e:
        # Optionally log the exception here if needed
        return None

async def get_username_by_id(db: AsyncSession, id: int):
    result = await db.execute(select(User).where(User.id == id))
    return result.scalar_one_or_none().username

async def create_user(db: AsyncSession, username: str, password: str):
    new_user = User(username=username, password=password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def send_message_db(db: AsyncSession, sender_id: int, recipient_id: int, content: str) -> Message:
    new_message = Message(
        sender_id=sender_id,
        recipient_id_user=recipient_id,
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

from sqlalchemy import select, case, func
from sqlalchemy.orm import aliased

async def get_latest_messages_overview(db: AsyncSession, user_id: int):
    # Alias the User table for the recipient
    recipient_alias = aliased(User)

    stmt = (
        select(
            # Conditionally select either the sender's or recipient's name
            case(
                (Message.sender_id == user_id, recipient_alias.username),  # If the user is the sender, get the recipient's name
                else_=User.username  # If the user is the recipient, get the sender's name
            ).label('partner_name'),
            case(
                (Message.sender_id == user_id, recipient_alias.id),  # If the user is the sender, get the recipient's id
                else_=User.id  # If the user is the recipient, get the sender's id
            ).label('partner_id'),
            # Use the MAX function to get the most recent message's timestamp
            func.max(Message.timestamp).label('latest_timestamp')
        )
        .select_from(Message)
        .join(User, User.id == Message.sender_id)  # Join User to get sender's info
        .join(recipient_alias, recipient_alias.id == Message.recipient_id_user)  # Join the alias for recipient's info
        .where(
            (Message.sender_id == user_id) | (Message.recipient_id_user == user_id)  # Ensure we're only fetching relevant messages
        )
        .group_by(
            User.username,
            recipient_alias.username,
            User.id,
            recipient_alias.id,
            Message.sender_id,  # Group by sender_id as well
            Message.recipient_id_user  # Group by recipient_id_user
        )
        .order_by(
            func.max(Message.timestamp).desc()  # Order by most recent message's timestamp
        )
    )

    result = await db.execute(stmt)
    print("selected")

    # Fetch the results
    conversations = [
        {"partner_name": row.partner_name,
         "partner_id": row.partner_id}
        for row in result.unique().all()
    ]

    return conversations
