import copy
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


def test_validar_item_no_modifica_el_item_que_recibe():
    un_item = item(talle="m", precio=1)
    copia = copy.deepcopy(un_item)

    validar_item(un_item)

    assert un_item == copia


def test_calcular_total_no_modifica_el_carrito_que_recibe():
    carrito = [item("buzo", "m", 2), item("remera", "xl", 1, color="rojo")]
    copia = copy.deepcopy(carrito)

    calcular_total(carrito, "CABA", None, HOY_VIGENTE)

    assert carrito == copia


@pytest.mark.parametrize("talle", ["XS", "S", "M", "L", "XL", "XXL", "m", "xL", "  M ", "\tXXL\n"])
def test_un_talle_valido_se_acepta_sin_importar_mayusculas_ni_espacios(talle):
    assert resultado_de_validar(item(talle=talle)) == "VALIDO"


@pytest.mark.parametrize("talle", ["XXXL", "XXS", "M L", "MEDIANO", "", "   ", None, 5])
def test_un_talle_que_no_es_de_la_lista_es_invalido(talle):
    assert resultado_de_validar(item(talle=talle)) == "TALLE_INVALIDO"


def test_un_item_sin_talle_es_invalido():
    sin_talle = {"producto": "buzo", "cantidad": 1}

    assert resultado_de_validar(sin_talle) == "TALLE_INVALIDO"
