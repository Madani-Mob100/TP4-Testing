from datetime import date
from decimal import Decimal

import pytest

from checkout import (
    CheckoutError,
    calcular_descuento,
    calcular_envio,
    calcular_subtotal,
    calcular_total,
    validar_item,
)

HOY_VIGENTE = date(2026, 10, 1)


def item(producto="buzo", talle="M", cantidad=1, **extra):
    return {"producto": producto, "talle": talle, "cantidad": cantidad, **extra}


def codigo_de_error(funcion, *args):
    with pytest.raises(CheckoutError) as error:
        funcion(*args)
    return error.value.code


def resultado_de_validar(un_item):
    try:
        validar_item(un_item)
    except CheckoutError as error:
        return error.code
    return "VALIDO"


def test_cantidad_cero_es_invalida():
    assert codigo_de_error(validar_item, item(cantidad=0)) == "CANTIDAD_INVALIDA"


def test_cantidad_diez_es_valida_porque_el_limite_es_inclusive():
    assert resultado_de_validar(item(cantidad=10)) == "VALIDO"


@pytest.mark.parametrize("cantidad", [2.5, 2.0, "3", True, None], ids=["decimal", "float_entero", "texto", "bool", "none"])
def test_una_cantidad_que_no_es_entera_es_invalida(cantidad):
    assert resultado_de_validar(item(cantidad=cantidad)) == "CANTIDAD_INVALIDA"
