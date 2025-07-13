from pathlib import Path

class Typer:
    def __init__(self):
        self._commands = {}

    def command(self, name=None):
        def decorator(func):
            self._commands[name or func.__name__] = func
            return func
        return decorator

    def __call__(self, *args, **kwargs):
        pass

class colors:
    BLUE = 'blue'
    CYAN = 'cyan'
    MAGENTA = 'magenta'
    GREEN = 'green'


def echo(*args, **kwargs):
    pass


def secho(*args, **kwargs):
    pass


def Option(*args, **kwargs):
    return None


def Argument(*args, **kwargs):
    return None


import types

testing = types.ModuleType("testing")

class CliRunner:
    def invoke(self, app: Typer, args):
        cmd = args[0]
        func = app._commands[cmd]
        params = {}
        positionals = []
        it = iter(args[1:])
        for item in it:
            if item.startswith("--"):
                key = item.lstrip("-").replace('-', '_')
                try:
                    val = next(it)
                except StopIteration:
                    val = None
                params[key] = val
            else:
                positionals.append(item)
        try:
            func(*positionals, **params)
            return type('Result', (), {'exit_code': 0, 'stdout': '', 'stderr': ''})
        except SystemExit as e:
            return type('Result', (), {'exit_code': e.code, 'stdout': '', 'stderr': ''})

testing.CliRunner = CliRunner
