import lmdb
import pickle

env = lmdb.open("strategy.fibonacci.retracement.lmdb", map_size=10**8, max_dbs=1)

# Save a key-value pair
def save_value(key, value):
    with env.begin(write=True) as txn:
        txn.put(key.encode(), pickle.dumps(value))

# Load a key-value pair
def load_value(key):
    with env.begin() as txn:
        value = txn.get(key.encode())
        return pickle.loads(value) if value else None

# Example usage
save_value("BTC", 50000)
save_value("ETH", 3500)
print(load_value("BTC"))