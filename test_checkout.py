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


@pytest.mark.parametrize("producto", ["zapatilla", "Buzo", " buzo", "buzos", "", None, ["buzo"]])
def test_un_producto_fuera_del_catalogo_es_inexistente(producto):
    assert resultado_de_validar(item(producto=producto)) == "PRODUCTO_INEXISTENTE"


def test_un_item_sin_producto_es_inexistente():
    sin_producto = {"talle": "M", "cantidad": 1}

    assert resultado_de_validar(sin_producto) == "PRODUCTO_INEXISTENTE"


def test_el_producto_se_valida_antes_que_el_talle_y_la_cantidad():
    assert resultado_de_validar(item("zapatilla", "XXXL", 0)) == "PRODUCTO_INEXISTENTE"


def test_el_talle_se_valida_antes_que_la_cantidad():
    assert resultado_de_validar(item("buzo", "XXXL", 0)) == "TALLE_INVALIDO"


def test_calcular_total_informa_el_producto_inexistente_en_vez_de_ignorarlo():
    carrito = [item("buzo"), item("zapatilla")]

    assert codigo_de_error(calcular_total, carrito, "CABA") == "PRODUCTO_INEXISTENTE"


def test_el_subtotal_es_un_decimal_exacto_sin_error_de_float():
    carrito = [item("buzo", "M", 3)]

    subtotal = calcular_subtotal(carrito)

    assert isinstance(subtotal, Decimal)
    assert subtotal == Decimal("74999.70")


def test_el_descuento_porcentual_redondea_el_medio_centavo_hacia_arriba():
    descuento = calcular_descuento(Decimal("11999.50"), 1, "EGRESADOS2026", HOY_VIGENTE)

    assert isinstance(descuento, Decimal)
    assert descuento == Decimal("1799.93")


def test_el_descuento_porcentual_redondea_hacia_abajo_por_debajo_del_medio_centavo():
    descuento = calcular_descuento(Decimal("100.03"), 1, "EGRESADOS2026", HOY_VIGENTE)

    assert descuento == Decimal("15.00")


def test_calcular_total_devuelve_el_ejemplo_de_la_especificacion_en_decimal():
    carrito = [item("buzo", "M", 2)]

    resultado = calcular_total(carrito, "CABA", None, HOY_VIGENTE)

    assert resultado == {
        "subtotal": Decimal("49999.80"),
        "descuento": Decimal("0.00"),
        "envio": Decimal("2500.00"),
        "total": Decimal("52499.80"),
    }
    assert all(isinstance(importe, Decimal) for importe in resultado.values())


@pytest.mark.parametrize("producto, precio", [
    ("buzo", Decimal("24999.90")),
    ("remera", Decimal("11999.50")),
    ("campera", Decimal("47999.99")),
])
def test_el_subtotal_usa_el_precio_del_catalogo(producto, precio):
    assert calcular_subtotal([item(producto)]) == precio


def test_el_precio_que_trae_el_item_se_ignora():
    carrito = [item("buzo", "M", 2, precio=1)]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == Decimal("49999.80")


def test_las_claves_extra_del_item_se_ignoran():
    carrito = [item("remera", "S", 2, color="rojo", nota="regalo")]

    assert calcular_subtotal(carrito) == Decimal("23999.00")


def test_el_subtotal_suma_todos_los_items():
    carrito = [item("buzo", "M", 1), item("remera", "S", 2), item("campera", "XL", 1)]

    assert calcular_subtotal(carrito) == Decimal("96998.89")
