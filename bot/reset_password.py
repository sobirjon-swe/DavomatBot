import bcrypt, asyncio
from database.session import AsyncSessionLocal
from database.models import AccessPassword
from sqlalchemy import update

async def reset():
    hashed = bcrypt.hashpw(b'1234', bcrypt.gensalt()).decode()
    async with AsyncSessionLocal() as s:
        await s.execute(update(AccessPassword).where(AccessPassword.id==1).values(password_hash=hashed))
        await s.commit()
        print('Yangilandi:', hashed)

asyncio.run(reset())
