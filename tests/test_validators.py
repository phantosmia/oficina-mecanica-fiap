import pytest

from app.shared.validators import validate_document, validate_plate


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        ("529.982.247-25", "52998224725"),
        ("04.252.011/0001-10", "04252011000110"),
    ],
)
def test_validate_document_accepts_valid_values(document: str, expected: str) -> None:
    assert validate_document(document) == expected


@pytest.mark.parametrize("document", ["111.111.111-11", "12.345.678/0001-00", "123"])
def test_validate_document_rejects_invalid_values(document: str) -> None:
    with pytest.raises(ValueError):
        validate_document(document)


@pytest.mark.parametrize("plate", ["ABC1234", "BRA2E19", "abc1d23"])
def test_validate_plate_accepts_valid_values(plate: str) -> None:
    assert validate_plate(plate)


@pytest.mark.parametrize("plate", ["AB12345", "1234567", "AAAAAAA"])
def test_validate_plate_rejects_invalid_values(plate: str) -> None:
    with pytest.raises(ValueError):
        validate_plate(plate)
