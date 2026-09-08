import uuid
import bcrypt
import hashlib

async def create_token():
    token = str(uuid.uuid4())
    return token


#密码加密
def get_hash_password(password:str):
    # 先sha256摘要，固定输出32字节，完美避开bcrypt72字节限制
    raw = hashlib.sha256(password.encode("utf‑8")).digest()
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(raw, salt).decode()

#密码校验
def verify_password(plain_password:str,hashed_password:str):
    raw = hashlib.sha256(plain_password.encode("utf‑8")).digest()
    return bcrypt.checkpw(raw, hashed_password.encode("utf‑8"))