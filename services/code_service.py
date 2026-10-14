import secrets
import string


CODE_LENGTH = 8


def generate_file_code():
    characters = string.ascii_uppercase + string.digits

    code = "".join(
        secrets.choice(characters)
        for _ in range(CODE_LENGTH)
    )

    return code