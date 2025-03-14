import functools
import inspect
import time
from utilities.decorators.base import get_class_that_defined_method
from utilities.logger import config_logging

logger = config_logging(__name__)


def time_it(func=None, step_name=None, step_name_format=None):
    """
    Saves the runtime metric of the decorated function
    :param func: function obj to run
    :param step_name: name of step to override function name for logging
    :param step_name_format: specify names of args to be included in step_name
    :return: returns the return value of the function
    """

    def generate_step_name_from_format(*args, **kwargs):
        """
        Function to generate a string of args that should be tracked along the function name
        :param args: list of args to track
        :param kwargs: dict of kwargs to track
        """
        generated_step_name = ""
        try:
            if step_name_format:
                call_args = inspect.getcallargs(func, *args, **kwargs)
                generated_step_name = "_".join(
                    str(call_args[arg_name]) for arg_name in step_name_format
                )
        except Exception as e:
            logger.warning(f"Failed to generate step name from format {e}")
        return generated_step_name

    def decorator(func):
        @functools.wraps(func)
        def wrapper_timer(*args, **kwargs):
            inner_step_name = step_name or func.__name__
            class_name = get_class_that_defined_method(func)

            if class_name:  # if function inside a class wrap the class name before it
                inner_step_name = f"{class_name.__name__}-{inner_step_name}"

            args_names = generate_step_name_from_format(*args, **kwargs)
            if args_names:
                inner_step_name = f"{inner_step_name}-{args_names}"

            start_time = time.time()
            value = func(*args, **kwargs)
            end_time = time.time()
            run_time = end_time - start_time

            logger.info(f"@time_it: Finished {inner_step_name} in {run_time:.2f} secs")
            return value

        return wrapper_timer

    if func:
        return decorator(func)
    else:
        return decorator
