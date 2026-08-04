import hashlib
import secrets
import random


def hash_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def gen_seed() -> str:
    return secrets.token_hex(32)


def rng_for(server_seed: str, client_seed: str, round_no: int) -> random.Random:
    digest = hash_hex(f"{server_seed}:{client_seed}:{round_no}")
    return random.Random(digest)