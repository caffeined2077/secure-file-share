from argon2 import PasswordHasher

ph = PasswordHasher()


def hash_password(password):
    return ph.hash(password)


def verify_password(password, password_hash):
    try:
        ph.verify(password_hash, password)
        return True
    except:
        return False


