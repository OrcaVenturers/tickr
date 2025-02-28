import time
from functools import wraps

def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()  # High-precision start time
        result = func(*args, **kwargs)
        end_time = time.perf_counter()  # High-precision end time
        elapsed_time = end_time - start_time
        print(f"{func.__name__} executed in {elapsed_time:.6f} seconds")
        return result
    return wrapper
