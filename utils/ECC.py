import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
import aiohttp
import asyncio
from decouple import config


class ECC:
    def __init__(self):
        pass

    async def get_token_information(self):
        ecc_url = config("ECC_URL")
        ecc_token = config("ECC_TOKEN")

        async with aiohttp.ClientSession() as session:
            async with session.get(ecc_url + "/instance/" + ecc_token) as response:
                return await response.json()

    def decrypt_token(self, encrypted_token: str):
        rsa_cert = config("RSA_CERT")

        priv_key = RSA.import_key(rsa_cert.replace("\\n", "\n"))
        ciphertext = base64.b64decode(encrypted_token)
        cipher = PKCS1_OAEP.new(priv_key, hashAlgo=SHA256)
        plaintext = cipher.decrypt(ciphertext)

        return plaintext.decode("utf-8")
