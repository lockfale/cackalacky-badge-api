import base64
import logging

logger = logging.getLogger("s3logger")

XOR_KEY = 0x69


def encoder(value):
    logger.info(f"Encoding: {value}")
    bytes_list = [chr(ord(char) ^ XOR_KEY) for char in value]
    encoded_bytes = "".join(bytes_list).encode("utf-8")
    encoded_str = base64.b64encode(encoded_bytes).decode("utf-8")
    logger.info(f"Encoded value: {encoded_str}")
    return encoded_str


def decoder(value):
    logger.info(f"Decoding: {value}")
    base64_value = base64.b64decode(value).decode("utf-8")
    bytes_list = [chr(ord(char) ^ XOR_KEY) for char in base64_value]
    decoded_str = "".join(bytes_list)
    logger.info(decoded_str)
    return decoded_str
