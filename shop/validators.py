import re
from django.core.exceptions import ValidationError

def normalize_rut(rut):
    return re.sub(r"[\.\-\s]", "", str(rut or "")).upper()

def validate_rut(rut):
    rut = normalize_rut(rut)

    if not re.fullmatch(r"\d{7,8}[0-9K]", rut):
        raise ValidationError("El RUT debe tener el formato válido, por ejemplo 12345678-5.")

    body = rut[:-1]
    verifier = rut[-1]

    total = 0
    multiplier = 2
    for digit in reversed(body):
        total += int(digit) * multiplier
        multiplier += 1
        if multiplier == 8:
            multiplier = 2

    remainder = 11 - (total % 11)
    expected = "0" if remainder == 11 else "K" if remainder == 10 else str(remainder)

    if verifier != expected:
        raise ValidationError("El RUT ingresado no es válido.")

    return rut
