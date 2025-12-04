#!/bin/bash
set -e

echo "🔄 Waiting for database to be ready..."

# Ждём пока база данных будет доступна
python << EOF
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

async def wait_for_db():
    db_url = os.getenv("DATABASE_URL")
    engine = create_async_engine(db_url)
    
    for i in range(30):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            print("✅ Database is ready!")
            await engine.dispose()
            return True
        except Exception as e:
            print(f"⏳ Waiting for database... ({i+1}/30)")
            await asyncio.sleep(2)
    
    print("❌ Database connection failed!")
    await engine.dispose()
    sys.exit(1)

asyncio.run(wait_for_db())
EOF

echo "🔄 Waiting for Redis to be ready..."

# Ждём пока Redis будет доступен
python << EOF
import asyncio
import sys
import os
import redis.asyncio as redis

async def wait_for_redis():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    for i in range(30):
        try:
            client = redis.from_url(redis_url)
            await client.ping()
            await client.close()
            print("✅ Redis is ready!")
            return True
        except Exception as e:
            print(f"⏳ Waiting for Redis... ({i+1}/30)")
            await asyncio.sleep(2)
    
    print("❌ Redis connection failed!")
    sys.exit(1)

asyncio.run(wait_for_redis())
EOF

echo "🔄 Running database migrations..."
alembic upgrade head

echo "🚀 Starting bot..."
exec python main.py

