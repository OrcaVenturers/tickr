import hashlib
import pickle
from enum import Enum


def generate_cache_key_for_function(func, args, kwargs):
    """Generate a cache key that will be consistent between runs. hash() is NOT CONSISTENT! Sample terminal session:

    (venv) ->  dashsync git:(staging) python
    Python 3.7.4 (default, Jul  9 2019, 18:13:23)
    [Clang 10.0.1 (clang-1001.0.46.4)] on darwin
    Type "help", "copyright", "credits" or "license" for more information.
    >>> hash('foo')
    -4268220770207819208
    >>>
    (venv) ->  dashsync git:(staging) python
    Python 3.7.4 (default, Jul  9 2019, 18:13:23)
    [Clang 10.0.1 (clang-1001.0.46.4)] on darwin
    Type "help", "copyright", "credits" or "license" for more information.
    >>> hash('foo')
    -4488366444344858763
    >>>

    That is why this function exists and does not just hash() args and kwargs.

    Make your function name globally unique across the project or else function names in different projects will
    clash with one another and overwrite one another's data!"""

    return (
        func.__name__
        + hashlib.md5(pickle.dumps(args + tuple(kwargs.items()))).hexdigest()
    )
