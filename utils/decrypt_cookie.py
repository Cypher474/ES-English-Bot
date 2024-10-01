import base64
import urllib.parse
from Crypto.Cipher import AES
from fastapi import HTTPException

def decrypt_esdubai_student_id(cookies: str):
    def get_cookie_value(cookies, cookie_name):
        cookies_dict = dict(cookie.strip().split('=', 1) for cookie in cookies.split(';'))
        return cookies_dict.get(cookie_name)

    def fix_base64_padding(value):
        missing_padding = len(value) % 4
        if missing_padding != 0:
            value += '=' * (4 - missing_padding)
        return value

    def unpad(s):
        padding_len = s[-1]
        return s[:-padding_len]

    key = b'key'.ljust(16, b'\0')  # Replace 'key' with the actual key

    encrypted_value = get_cookie_value(cookies, 'ESDUBAI_STUDENT_ID')
    if not encrypted_value:
        return None

    encrypted_value = urllib.parse.unquote(encrypted_value)
    encrypted_value = fix_base64_padding(encrypted_value)

    try:
        encrypted_value = base64.b64decode(encrypted_value)
    except Exception as e:
        print(f"Error during base64 decoding: {e}")
        return None

    cipher = AES.new(key, AES.MODE_ECB)
    decrypted_value = cipher.decrypt(encrypted_value)

    try:
        decrypted_value = unpad(decrypted_value)
        return decrypted_value.decode('utf-8')
    except Exception as e:
        print(f"Error during decryption: {e}")
        return None
