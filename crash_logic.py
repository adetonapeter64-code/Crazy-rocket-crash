"""
crash_logic.py
This file decides the crash point for each round.
"""
import random
import hashlib
import hmac
import secrets

def generate_server_seed():
    """Create a secret random seed. This is our 'promise' for the round."""
    return secrets.token_hex(32)

def hash_seed(seed):
    """Publish a hash of the seed BEFORE the round starts.
    Players can't reverse this to find the seed, but after the round
    we reveal the seed and they can check the hash matches. That's
    what makes it 'provably fair' - we can't change our mind mid-round."""
    return hashlib.sha256(seed.encode()).hexdigest()

def seed_to_float(server_seed, client_seed, nonce):
    """Combine server seed + client seed + round number into one
    random-looking number between 0 and 1, using HMAC (a keyed hash)."""
    message = f"{client_seed}:{nonce}"
    h = hmac.new(server_seed.encode(), message.encode(), hashlib.sha256).hexdigest()
    # take first 13 hex chars, turn into a big integer, scale to [0,1)
    int_value = int(h[:13], 16)
    return int_value / float(16**13)

def generate_crash_point(server_seed, client_seed, nonce, house_edge=0.01):
    """The main function: turns the seeds into a crash multiplier."""
    r = seed_to_float(server_seed, client_seed, nonce)
    if r < house_edge:
        return 1.00  # instant crash, gives the house its edge
    crash = (1 - house_edge) / (1 - r)
    return max(1.00, round(crash, 2))
