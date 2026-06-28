"""Unit tests for prompt_toolkit validators (non-DB validators).

ProductCategoryValidator is tested in integration tests — its validate()
method lazily imports handler modules that require the handlers directory
on sys.path and a live database connection.
"""

from prompt_toolkit.validation import ValidationError
from pytest import raises

from validators import (
    ChoiceValidator,
    NonEmptyValidator,
    PriceValidator,
    QuantityValidator,
    YesNoValidator,
)


class TestNonEmptyValidator:
    """NonEmptyValidator accepts any non-empty string."""

    def test_accepts_text(self, document):
        validator = NonEmptyValidator()
        # No exception means success
        validator.validate(document("hello"))

    def test_accepts_single_space_stripped_to_empty_no(self, document):
        validator = NonEmptyValidator()
        with raises(ValidationError):
            validator.validate(document("   "))

    def test_rejects_empty(self, document):
        validator = NonEmptyValidator()
        with raises(ValidationError) as exc:
            validator.validate(document(""))
        assert "не может быть пустым" in exc.value.message

    def test_custom_message(self, document):
        validator = NonEmptyValidator(message="Введите имя")
        with raises(ValidationError) as exc:
            validator.validate(document(""))
        assert exc.value.message == "Введите имя"


class TestYesNoValidator:
    """YesNoValidator accepts y/yes/д/да and n/no/н/нет (case-insensitive)."""

    def test_accepts_y(self, document):
        v = YesNoValidator()
        v.validate(document("y"))

    def test_accepts_yes(self, document):
        v = YesNoValidator()
        v.validate(document("YES"))

    def test_accepts_д(self, document):
        v = YesNoValidator()
        v.validate(document("да"))

    def test_accepts_n(self, document):
        v = YesNoValidator()
        v.validate(document("n"))

    def test_accepts_no(self, document):
        v = YesNoValidator()
        v.validate(document("NO"))

    def test_accepts_н(self, document):
        v = YesNoValidator()
        v.validate(document("нет"))

    def test_rejects_invalid(self, document):
        v = YesNoValidator()
        with raises(ValidationError):
            v.validate(document("maybe"))

    def test_rejects_empty(self, document):
        v = YesNoValidator()
        with raises(ValidationError):
            v.validate(document(""))

    def test_is_yes_classmethod(self):
        assert YesNoValidator.is_yes("y") is True
        assert YesNoValidator.is_yes("Y") is True
        assert YesNoValidator.is_yes("да") is True
        assert YesNoValidator.is_yes("n") is False

    def test_is_no_classmethod(self):
        assert YesNoValidator.is_no("n") is True
        assert YesNoValidator.is_no("нет") is True
        assert YesNoValidator.is_no("y") is False


class TestChoiceValidator:
    """ChoiceValidator accepts values from a given list."""

    def test_accepts_valid_choice(self, document):
        v = ChoiceValidator(choices=["a", "b", "c"])
        v.validate(document("b"))

    def test_rejects_invalid_choice(self, document):
        v = ChoiceValidator(choices=["a", "b"])
        with raises(ValidationError) as exc:
            v.validate(document("z"))
        assert "из списка" in exc.value.message

    def test_rejects_empty(self, document):
        v = ChoiceValidator(choices=["a"])
        with raises(ValidationError):
            v.validate(document(""))

    def test_custom_message(self, document):
        v = ChoiceValidator(choices=["x"], message="Выбери x!")
        with raises(ValidationError) as exc:
            v.validate(document("y"))
        assert exc.value.message == "Выбери x!"

    def test_strips_whitespace(self, document):
        v = ChoiceValidator(choices=["ok"])
        # Leading/trailing whitespace is stripped before check
        v.validate(document("  ok  "))


class TestPriceValidator:
    """PriceValidator accepts positive floats."""

    def test_accepts_integer_price(self, document):
        v = PriceValidator()
        v.validate(document("10"))

    def test_accepts_float_price(self, document):
        v = PriceValidator()
        v.validate(document("3.14"))

    def test_rejects_zero(self, document):
        v = PriceValidator()
        with raises(ValidationError) as exc:
            v.validate(document("0"))
        assert "больше 0" in exc.value.message

    def test_rejects_negative(self, document):
        v = PriceValidator()
        with raises(ValidationError) as exc:
            v.validate(document("-5"))
        assert "больше 0" in exc.value.message

    def test_rejects_non_numeric(self, document):
        v = PriceValidator()
        with raises(ValidationError) as exc:
            v.validate(document("abc"))
        assert "число" in exc.value.message

    def test_rejects_empty(self, document):
        v = PriceValidator()
        with raises(ValidationError):
            v.validate(document(""))

    def test_accepts_whitespace_padded(self, document):
        v = PriceValidator()
        v.validate(document("  42.5  "))


class TestQuantityValidator:
    """QuantityValidator accepts positive integers."""

    def test_accepts_positive_int(self, document):
        v = QuantityValidator()
        v.validate(document("1"))

    def test_rejects_zero(self, document):
        v = QuantityValidator()
        with raises(ValidationError) as exc:
            v.validate(document("0"))
        assert "больше 0" in exc.value.message

    def test_rejects_negative(self, document):
        v = QuantityValidator()
        with raises(ValidationError) as exc:
            v.validate(document("-3"))
        assert "больше 0" in exc.value.message

    def test_rejects_float(self, document):
        v = QuantityValidator()
        # float string -> int() raises ValueError -> ValidationError
        with raises(ValidationError) as exc:
            v.validate(document("2.5"))
        assert "число" in exc.value.message

    def test_rejects_non_numeric(self, document):
        v = QuantityValidator()
        with raises(ValidationError) as exc:
            v.validate(document("xyz"))
        assert "число" in exc.value.message

    def test_rejects_empty(self, document):
        v = QuantityValidator()
        with raises(ValidationError):
            v.validate(document(""))

    def test_accepts_whitespace_padded(self, document):
        v = QuantityValidator()
        v.validate(document("  99  "))
