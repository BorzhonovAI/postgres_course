"""Unit tests for the command registration system (commands module).

Covers @command decorator, Command dataclass, registry, role filtering,
completer dict, find_command, and get_args.
"""

from unittest.mock import MagicMock

import pytest
from prompt_toolkit.completion import NestedCompleter

import commands
from auth import ALL_ROLES, ROLE_CATALOG_MANAGER, ROLE_SALES_MANAGER
from commands import (
    Command,
    _COMMANDS_REGISTRY,
    _build_completer_dict,
    command,
    find_command,
    get_args,
    get_commands,
    get_completer,
)


class TestCommandDataclass:
    """Command is a frozen dataclass with the expected fields."""

    def test_fields(self):
        cmd = Command(
            text="hello",
            handler=lambda: None,
            description="greeting",
            category="TEST",
            allowed_roles=["catalog_manager"],
            args=("name",),
        )
        assert cmd.text == "hello"
        assert cmd.description == "greeting"
        assert cmd.category == "TEST"
        assert cmd.allowed_roles == ["catalog_manager"]
        assert cmd.args == ("name",)

    def test_frozen(self):
        import dataclasses

        cmd = Command(
            text="x",
            handler=lambda: None,
            description="x",
            category="X",
            allowed_roles=[],
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            cmd.text = "mutated"

    def test_default_args_is_empty_tuple(self):
        cmd = Command(
            text="no_args",
            handler=lambda: None,
            description="none",
            category="C",
            allowed_roles=[],
        )
        assert cmd.args == ()


class TestCommandDecorator:
    """The @command decorator registers handlers and extracts signature args."""

    def test_registers_command(self):
        @command("greet", "приветствие", "ПРОЧЕЕ", ALL_ROLES)
        def greet_handler():
            pass

        assert any(c.text == "greet" for c in _COMMANDS_REGISTRY)

    def test_extracts_args_from_signature(self):
        @command("ship order", "отправить заказ", "ЗАКАЗЫ", ALL_ROLES)
        def ship_order_handler(order_id: str, tracking: str):
            pass

        cmd = next(c for c in _COMMANDS_REGISTRY if c.text == "ship order")
        assert cmd.args == ("order_id", "tracking")

    def test_stores_metadata(self):
        @command("test cmd", "тестовое описание", "ПРОЧЕЕ", [ROLE_SALES_MANAGER])
        def test_fn():
            pass

        cmd = next(c for c in _COMMANDS_REGISTRY if c.text == "test cmd")
        assert cmd.description == "тестовое описание"
        assert cmd.category == "ПРОЧЕЕ"
        assert cmd.allowed_roles == [ROLE_SALES_MANAGER]

    def test_returns_original_function(self):

        def my_func(a: int):
            return a + 1

        decorated = command("f", "f", "C", ALL_ROLES)(my_func)
        assert decorated is my_func


class TestGetCommands:
    """get_commands() filters by the authenticated user's role."""

    def test_filters_by_role(self, mock_user):
        # mock_user has role catalog_manager — only catalog_manager commands visible
        @command("cat_only", "для каталога", "ПРОЧЕЕ", [ROLE_CATALOG_MANAGER])
        def cat_fn():
            pass

        @command("sales_only", "для продаж", "ПРОЧЕЕ", [ROLE_SALES_MANAGER])
        def sales_fn():
            pass

        visible = get_commands()
        texts = [c.text for c in visible]
        assert "cat_only" in texts
        assert "sales_only" not in texts

    def test_all_roles_command_visible(self, mock_user):
        @command("everyone", "для всех", "ПРОЧЕЕ", ALL_ROLES)
        def everyone_fn():
            pass

        visible = get_commands()
        assert any(c.text == "everyone" for c in visible)

    def test_raises_when_not_authenticated(self):
        # auth._USER is None after autouse reset
        with pytest.raises(RuntimeError, match="Not authenticated"):
            get_commands()


class TestBuildCompleterDict:
    """_build_completer_dict builds a nested dict from command texts."""

    def test_single_word_command(self, mock_user):
        @command("ping", "проверка", "ПРОЧЕЕ", ALL_ROLES)
        def ping_fn():
            pass

        d = _build_completer_dict()
        assert "ping" in d
        assert d["ping"] is None

    def test_multi_word_command(self, mock_user):
        @command("add warehouse", "добавить склад", "СКЛАДЫ", ALL_ROLES)
        def add_wh_fn():
            pass

        d = _build_completer_dict()
        assert "add" in d
        assert isinstance(d["add"], dict)
        assert "warehouse" in d["add"]

    def test_empty_text_skipped(self, mock_user):
        @command("", "пустая", "ПРОЧЕЕ", ALL_ROLES)
        def empty_fn():
            pass

        d = _build_completer_dict()
        # Empty text stripped -> skipped, should not appear as key ""
        assert "" not in d

    def test_whitespace_text_skipped(self, mock_user):
        @command("   ", "пробелы", "ПРОЧЕЕ", ALL_ROLES)
        def ws_fn():
            pass

        d = _build_completer_dict()
        assert "   " not in d

    def test_returns_nested_completer_via_get_completer(self, mock_user):
        @command("hello", "привет", "ПРОЧЕЕ", ALL_ROLES)
        def hello_fn():
            pass

        completer = get_completer()
        assert isinstance(completer, NestedCompleter)


class TestFindCommand:
    """find_command matches user input against registered command texts."""

    def test_exact_match(self, mock_user):
        @command("status", "статус", "ПРОЧЕЕ", ALL_ROLES)
        def status_fn():
            pass

        cmd = find_command("status")
        assert cmd is not None
        assert cmd.text == "status"

    def test_prefix_match_with_space(self, mock_user):
        @command("show order", "показать заказ", "ЗАКАЗЫ", ALL_ROLES)
        def show_order_fn():
            pass

        cmd = find_command("show order 42")
        assert cmd is not None
        assert cmd.text == "show order"

    def test_no_match_returns_none(self, mock_user):
        @command("alpha", "альфа", "ПРОЧЕЕ", ALL_ROLES)
        def alpha_fn():
            pass

        assert find_command("beta") is None

    def test_prefix_without_space_no_match(self, mock_user):
        @command("show", "показать", "ПРОЧЕЕ", ALL_ROLES)
        def show_fn():
            pass

        # "showme" starts with "show" but not "show " — should NOT match
        assert find_command("showme") is None

    def test_empty_input_returns_none(self, mock_user):
        assert find_command("") is None


class TestGetArgs:
    """get_args extracts positional arguments from user input."""

    def test_no_args(self):
        @command("go", "поехали", "C", ALL_ROLES)
        def go_fn():
            pass

        cmd = next(c for c in _COMMANDS_REGISTRY if c.text == "go")
        args = get_args("go", cmd)
        assert args == {}

    def test_one_arg(self):
        @command("get", "получить", "C", ALL_ROLES)
        def get_fn(item_id: str):
            pass

        cmd = next(c for c in _COMMANDS_REGISTRY if c.text == "get")
        args = get_args("get 42", cmd)
        assert args == {"item_id": "42"}

    def test_two_args(self):
        @command("transfer", "переместить", "C", ALL_ROLES)
        def transfer_fn(from_wh: str, to_wh: str):
            pass

        cmd = next(c for c in _COMMANDS_REGISTRY if c.text == "transfer")
        args = get_args("transfer 1 2", cmd)
        assert args == {"from_wh": "1", "to_wh": "2"}

    def test_multi_word_command_with_args(self):
        @command("update product", "обновить товар", "C", ALL_ROLES)
        def update_fn(_id: str, name: str):
            pass

        cmd = next(c for c in _COMMANDS_REGISTRY if c.text == "update product")
        args = get_args("update product 5 Hammer", cmd)
        assert args == {"_id": "5", "name": "Hammer"}

    def test_wrong_number_of_args_raises(self):
        @command("set price", "установить цену", "C", ALL_ROLES)
        def set_price_fn(_id: str, price: str):
            pass

        cmd = next(c for c in _COMMANDS_REGISTRY if c.text == "set price")
        with pytest.raises(ValueError, match="expects 2"):
            get_args("set price 10", cmd)

    def test_misaligned_input_raises(self):
        @command("ok", "окей", "C", ALL_ROLES)
        def ok_fn():
            pass

        cmd = next(c for c in _COMMANDS_REGISTRY if c.text == "ok")
        with pytest.raises(ValueError, match="not aligned"):
            get_args("no 1 2", cmd)

    def test_extra_whitespace_is_stripped(self):
        @command("do", "сделать", "C", ALL_ROLES)
        def do_fn(task: str):
            pass

        cmd = next(c for c in _COMMANDS_REGISTRY if c.text == "do")
        args = get_args("  do cleanup  ", cmd)
        assert args == {"task": "cleanup"}
