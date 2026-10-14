import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

FERNET_KEY = os.getenv("FERNET_KEY")

if not FERNET_KEY:
    raise ValueError("FERNET_KEY is missing from .env")

fernet = Fernet(FERNET_KEY.encode())


def encrypt_file(file_data: bytes) -> bytes:
    return fernet.encrypt(file_data)


def decrypt_file(encrypted_data: bytes) -> bytes:
    return fernet.decrypt(encrypted_data)