import functools
import inspect
from abc import ABC, abstractmethod


def get_class_that_defined_method(meth):
    """
    Function to extract the class name of a certain function. This function handles bound and unbound methods
    :param meth: method to retrieve class for
    :return: class if found, None otherwise
    """
    if inspect.ismethod(meth):
        for cls in inspect.getmro(meth.__self__.__class__):
            if cls.__dict__.get(meth.__name__) is meth:
                return cls
        meth = meth.__func__  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        cls = getattr(
            inspect.getmodule(meth),
            meth.__qualname__.split(".<locals>", 1)[0].rsplit(".", 1)[0],
        )
        if isinstance(cls, type):
            return cls
    if isinstance(meth, BaseDecorator):
        cls = get_class_that_defined_method(meth.func)
        return cls
    return getattr(meth, "__objclass__", None)  # handle special descriptor objects


class PartialInstanceCaller:
    """
    Partial wrapper to func. Instance is injected to func calls as self and attributes are fetched from func
    This helper makes sure that we can access decorator attributes from decorated methods
    Example:
        class TestDecorator:
            @Cache.to_memory
            def decorated_method(self, key):
                pass

        when we do:
            obj = TestDecorator()
            obj.decorated_method
        Cache.to_memory.__get__ it's called with:
            - self = the current to_memory instance
            - instance (parameter) = obj

        In the __get__ method, we then return a PartialInstanceCaller to ensure the self in "decorated_method" is obj
        and not the "to_memory" instance
    """

    def __init__(self, decorator, instance):
        self.decorator = decorator
        self.instance = instance
        functools.update_wrapper(self, decorator, updated=())
        self.__wrapped__ = decorator.__wrapped__

    def __getattr__(self, item):
        """
        Attrs should come from the decorator
        :param item:
        :return:
        """
        return getattr(self.decorator, item)

    def __call__(self, *args, **kwargs):
        """
        Calling this instance should instead call the decorator with self.instance as self
        :param args:
        :param kwargs:
        :return:
        """
        return self.decorator(self.instance, *args, **kwargs)


class BaseDecorator(ABC):
    def __init__(self, func=None):
        self.func = func
        self.__wrapped__ = func
        if func:
            self.do_wrap(func)

    def do_wrap(self, func):
        """
        Function called when wrapping func
        Useful if one wants to access attributes of func during construction
        :param func:
        :return:
        """
        if not func:
            raise RuntimeError("Invalid decorating function")

        self.func = func

        # we cannot update __dict__ here, it will lose all this instance attributes
        functools.update_wrapper(self, func, updated=())
        self.__wrapped__ = func

    @staticmethod
    def shared_func(func_name: str):
        """
        Decorator to handle calling all the shared funcs from the previous decorators (if they exist) and
        the one wrapped. This function will recursively call the nested decorator containing functions named func_name
        and retrieve the results of these functions into the results dict
        :param func_name: str name of the shared functions to call
        :return: dict containing the result of all nested func_name functions for any parent of this decorator
        """

        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                """
                :param self: has to be a base decorator instance
                :param args:
                :param kwargs:
                :return:
                """
                if not isinstance(self, BaseDecorator):
                    raise RuntimeError(
                        "'shared_func' decorator can only be used with instances of BaseDecorator"
                    )

                # call the wrapped func and store the result
                results = {self.__class__.__name__: func(self, *args, **kwargs)}

                wrapped = self.__wrapped__

                if not hasattr(wrapped, func_name):
                    # no reason to continue if previous decorators dont have this method
                    return results

                shared_func = getattr(wrapped, func_name)

                if getattr(shared_func, "__is_shared_func__", None):
                    results.update(shared_func(*args, **kwargs))
                else:
                    name = get_class_that_defined_method(shared_func)
                    results[name] = shared_func(*args, **kwargs)

                return results

            wrapper.__is_shared_func__ = True
            return wrapper

        return decorator

    @abstractmethod
    def wrapper(self, *args, **kwargs):
        """
        Decorator implementation. Override this function to implement the decorator, the subclass is responsible for
        calling self.func with proper args
        :param args:
        :param kwargs:
        :return:
        """
        raise NotImplementedError

    def __get__(self, instance, owner=None):
        """
        Wrapper around methods, this will add "self" of the caller in the arg list
        :param instance:
        :param owner:
        :return:
        """
        ret = PartialInstanceCaller(self, instance)
        return ret

    def __call__(self, *args, **kwargs):
        """
        Wrapped handle. If the decorator is not initialized yet, the first call will be from the decorator
        Subsequent calls will be wrapping calls
        :param args:
        :param kwargs:
        :return:
        """
        args = list(args)
        if not self.func:
            func = args.pop(0)
            self.do_wrap(func)
            return self

        return self.wrapper(*args, **kwargs)
