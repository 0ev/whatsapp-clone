from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql+asyncpg://postgres:password@postgres:5432/wp-clone"

# Create the database engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create a session factory
SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

# Base class for models
Base = declarative_base()

# Dependency to get the database session
async def get_db():
    async with SessionLocal() as session:
        yield session
