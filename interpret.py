import enum
import inspect
import logging
import os
import string
import sys
from typing import Optional, Any

import rich

logger = logging.getLogger("interpret")


class Environment:
    def __init__(self, inherit: Optional["Environment"] = None):
        self.env_vars = {}
        if inherit is not None:
            self.env_vars.update(inherit.env_vars)

    @classmethod
    def base_env(cls) -> "Environment":
        target = cls()
        # Swap out the environment.
        target.env_vars = dict(os.environ)
        return target


@enum.unique
class TokenType(enum.Enum):
    COMMENT = enum.auto()
    IDENTIFIER = enum.auto()
    STRING_SQ = enum.auto()
    STRING_DQ = enum.auto()

    BLOCK_OPEN = enum.auto()
    BLOCK_CLOSE = enum.auto()
    VAR_REFERENCE = enum.auto()


class Token:
    def __init__(self, token_type: TokenType, lexeme: str, value: Optional[Any] = None):
        self.token_type = token_type
        self.lexeme = lexeme
        self.value = value

    def __repr__(self):
        if self.value is not None:
            return f"({self.token_type.name} token: {self.lexeme!r} -> {self.value!r})"
        return f"({self.token_type.name} token: {self.lexeme!r})"


class ExpectationFailed(Exception):
    def __init__(self, expect: str, actual: str, position: int):
        self.expect = expect
        self.actual = actual
        self.position = position

        stack = inspect.stack()
        stack_name = "unknown"
        for frame in stack:
            if frame.function.startswith("scan"):
                stack_name = frame.function
                break
            if frame.function == "main":
                stack_name = frame.function
                break
        self.stack_name = stack_name
        super().__init__(
            f"at position {position} doing {stack_name}: expected {expect!r}, actually {actual!r}"
        )

    def rich_reason(self) -> str:
        return (
            f"at position [bold]{self.position}[/] doing [bold cyan]{self.stack_name}[/]: "
            f"expected [bold green]{self.expect}[/], actually [bold red]{self.actual}[/]"
        )


class Scanner:
    def __init__(self, stream: str):
        self.stream = stream
        self.cursor = 0

    def is_eof(self) -> bool:
        return self.cursor >= len(self.stream)

    def next(self) -> str:
        to_return = self.peek()
        self.cursor += 1
        return to_return

    def peek(self) -> str:
        if self.is_eof():
            return "\0"
        return self.stream[self.cursor]

    def expect(self, text: str):
        if self.stream[self.cursor :].startswith(text):
            self.cursor += len(text)
        else:
            snippet = self.stream[self.cursor : self.cursor + len(text)]
            if len(text) + self.cursor > len(self.stream):
                snippet += "<EOF>"
            raise ExpectationFailed(text, snippet, self.cursor)

    def match(self, text: str) -> bool:
        if self.stream[self.cursor :].startswith(text):
            self.cursor += len(text)
            return True
        return False

    def read_until(self, terminators: set[str]) -> str:
        start = self.cursor
        while not self.is_eof() and self.peek() not in terminators:
            self.next()
        return self.stream[start : self.cursor]

    def read_while(self, non_terminators: set[str], allow_empty: bool = True) -> str:
        start = self.cursor
        while not self.is_eof() and self.peek() in non_terminators:
            self.next()
        if not allow_empty and start == self.cursor:
            raise ExpectationFailed(
                f"one of {non_terminators}", self.peek(), self.cursor
            )
        return self.stream[start : self.cursor]

    def skip_spaces(self):
        while not self.is_eof() and self.peek().isspace():
            self.next()


def scan_comment(s: Scanner) -> Token:
    mark = s.cursor
    s.expect("#")
    s.match(" ")
    message = s.read_until({"\n"})
    return Token(TokenType.COMMENT, s.stream[mark : s.cursor], message)


def scan_string(s: Scanner, terminator: str) -> Token:
    mark = s.cursor
    s.expect(terminator)
    is_escape = False
    contents = ""
    while not s.is_eof():
        c = s.next()
        if is_escape:
            contents += c
            is_escape = False
        elif c == "\\":
            is_escape = True
        elif c == terminator:
            break
        else:
            contents += c
    return Token(TokenType.STRING_SQ, s.stream[mark : s.cursor], contents)


def scan_id(s: Scanner) -> Token:
    try:
        identifier = s.read_while(
            set(string.ascii_lowercase)
            | set(string.ascii_uppercase)
            | set("0123456789_"),
            False,
        )
    except ExpectationFailed as e:
        raise ExpectationFailed('an identifier (a-zA-Z0-9_)', e.actual, e.position)
    return Token(TokenType.IDENTIFIER, identifier, identifier)


def scan_var_reference(s: Scanner) -> Token:
    mark = s.cursor
    s.expect("$")
    identifier = scan_id(s)
    return Token(TokenType.VAR_REFERENCE, s.stream[mark : s.cursor], identifier)


def scan(input_string: str) -> list[Token]:
    tokens: list[Token] = []
    words = {}
    s = Scanner(input_string)
    while not s.is_eof():
        c = s.peek()
        if c == "#":
            tokens.append(scan_comment(s))
        elif c == "{":
            tokens.append(Token(TokenType.BLOCK_OPEN, s.next()))
        elif c == "}":
            tokens.append(Token(TokenType.BLOCK_CLOSE, s.next()))
        elif c == "'":
            tokens.append(scan_string(s, "'"))
        elif c == '"':
            tokens.append(scan_string(s, '"'))
        elif c == "$":
            tokens.append(scan_var_reference(s))
        else:
            tokens.append(scan_id(s))
        s.skip_spaces()
    return tokens


if __name__ == "__main__":
    rich.print(
        "[red]this script is not meant to be run directly[/red]", file=sys.stderr
    )
    exit(1)
