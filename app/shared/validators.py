import re


CPF_LENGTH = 11
CNPJ_LENGTH = 14
PLATE_PATTERN = re.compile(r"^(?:[A-Z]{3}\d{4}|[A-Z]{3}\d[A-Z0-9]\d{2})$")


def only_digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def detect_document_type(value: str) -> str:
    digits = only_digits(value)
    if len(digits) == CPF_LENGTH:
        return "CPF"
    if len(digits) == CNPJ_LENGTH:
        return "CNPJ"
    raise ValueError("CPF/CNPJ inválido.")


def validate_document(value: str) -> str:
    digits = only_digits(value)
    document_type = detect_document_type(value)

    if document_type == "CPF" and not _is_valid_cpf(digits):
        raise ValueError("CPF inválido.")
    if document_type == "CNPJ" and not _is_valid_cnpj(digits):
        raise ValueError("CNPJ inválido.")

    return digits


def validate_plate(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]", "", value).upper()
    if not PLATE_PATTERN.match(normalized):
        raise ValueError("Placa de veículo inválida.")
    return normalized


def _is_valid_cpf(value: str) -> bool:
    if len(value) != CPF_LENGTH or value == value[0] * CPF_LENGTH:
        return False

    first_digit = _cpf_digit(value[:9])
    second_digit = _cpf_digit(value[:9] + str(first_digit))
    return value.endswith(f"{first_digit}{second_digit}")


def _cpf_digit(value: str) -> int:
    factor = len(value) + 1
    total = sum(int(number) * weight for number, weight in zip(value, range(factor, 1, -1), strict=True))
    remainder = 11 - (total % 11)
    return 0 if remainder >= 10 else remainder


def _is_valid_cnpj(value: str) -> bool:
    if len(value) != CNPJ_LENGTH or value == value[0] * CNPJ_LENGTH:
        return False

    first_digit = _cnpj_digit(value[:12])
    second_digit = _cnpj_digit(value[:12] + str(first_digit))
    return value.endswith(f"{first_digit}{second_digit}")


def _cnpj_digit(value: str) -> int:
    if len(value) == 12:
        weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    else:
        weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    total = sum(int(number) * weight for number, weight in zip(value, weights, strict=True))
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder
