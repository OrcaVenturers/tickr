import signal
from loguru import logger as logging
import redis

def get_redis_client():
    r = redis.Redis(
        host="51.12.58.178",
        port=6379,
        decode_responses=True  # Ensures responses are strings instead of bytes
    )
    try:
        r.ping()
        logging.success("Connected to Redis successfully!")
        return r
    except redis.ConnectionError as e:
        logging.error(f"Failed to connect to Redis: {e}")

client = get_redis_client()
pubsub = client.pubsub()
pubsub.subscribe("market_data")  # Listen to the channel
# Flag to control the loop
running = True

def signal_handler(sig, frame):
    global running
    logging.warning("\nShutting down subscriber gracefully...")
    running = False

# Handle Ctrl+C
signal.signal(signal.SIGINT, signal_handler)
logging.info("Listening for price stream...")
try:
    while running:
        message = pubsub.get_message(timeout=1)  # Use get_message with a timeout
        if message:  # If there's a message
            if message["type"] == "message":
                logging.info(f"Received: {message['data']}")
except Exception as e:
    logging.error(f"Error occurred: {e}")
finally:
    pubsub.close()  # Ensure Redis PubSub connection is closed
    client.close()  # Ensure Redis client connection is closed
    logging.success("Subscriber closed.")