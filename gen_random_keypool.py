import pickle
from Crypto.Random import get_random_bytes

keypool = list()

for i in range(32):
    key = get_random_bytes(16)
    keypool.append(key)

with open('keypool', 'wb') as keypoolfile:
    pickle.dump(keypool, keypoolfile)
