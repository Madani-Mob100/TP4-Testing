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


@pytest.mark.parametrize("carrito", [[], None], ids=["lista_vacia", "none"])
def test_un_carrito_sin_items_es_carrito_vacio(carrito):
    assert codigo_de_error(calcular_total, carrito, "CABA") == "CARRITO_VACIO"


def test_calcular_subtotal_de_un_carrito_vacio_es_carrito_vacio():
    assert codigo_de_error(calcular_subtotal, []) == "CARRITO_VACIO"


def test_el_carrito_vacio_se_informa_antes_que_el_cupon_y_la_zona():
    assert codigo_de_error(calcular_total, [], "MARTE", "PROMO") == "CARRITO_VACIO"


@pytest.mark.parametrize("prendas, descuento_esperado", [
    (4, Decimal("0.00")),
    (5, Decimal("100.00")),
    (6, Decimal("100.00")),
])
def test_el_descuento_por_cantidad_es_del_diez_por_ciento_desde_cinco_prendas(prendas, descuento_esperado):
    assert calcular_descuento(Decimal("1000.00"), prendas, None, HOY_VIGENTE) == descuento_esperado


def test_cinco_remeras_tienen_diez_por_ciento_de_descuento():
    carrito = [item("remera", "M", 5)]

    resultado = calcular_total(carrito, "CABA", None, HOY_VIGENTE)

    assert resultado["descuento"] == Decimal("5999.75")


def test_las_prendas_se_suman_entre_todos_los_items_del_carrito():
    carrito = [item("buzo", "M", 2), item("remera", "S", 3)]

    resultado = calcular_total(carrito, "CABA", None, HOY_VIGENTE)

    assert resultado["descuento"] == Decimal("8599.83")


@pytest.mark.parametrize("fecha", [date(2026, 11, 29), date(2026, 11, 30)], ids=["29_nov", "30_nov"])
def test_egresados2026_es_valido_hasta_el_30_de_noviembre_inclusive(fecha):
    descuento = calcular_descuento(Decimal("11999.50"), 1, "EGRESADOS2026", fecha)

    assert descuento == Decimal("1799.93")


def test_egresados2026_despues_del_30_de_noviembre_esta_vencido():
    error = codigo_de_error(calcular_descuento, Decimal("11999.50"), 1, "EGRESADOS2026", date(2026, 12, 1))

    assert error == "CUPON_VENCIDO"


@pytest.mark.parametrize("cupon", ["DEBUG100", "PROMO10", "EGRESADOS2025", 123])
def test_un_cupon_que_no_es_de_los_dos_existentes_es_invalido(cupon):
    error = codigo_de_error(calcular_descuento, Decimal("50000.00"), 1, cupon, HOY_VIGENTE)

    assert error == "CUPON_INVALIDO"


def test_con_cinco_prendas_y_egresados2026_se_aplica_solo_el_quince_por_ciento():
    carrito = [item("remera", "M", 5)]

    resultado = calcular_total(carrito, "CABA", "EGRESADOS2026", HOY_VIGENTE)

    assert resultado["descuento"] == Decimal("8999.63")


def test_con_cinco_prendas_y_bienvenida_se_aplica_solo_el_diez_por_ciento():
    carrito = [item("remera", "M", 5)]

    resultado = calcular_total(carrito, "CABA", "BIENVENIDA", HOY_VIGENTE)

    assert resultado["descuento"] == Decimal("5999.75")


def test_bienvenida_mayor_que_el_descuento_por_cantidad_se_aplica_solo():
    descuento = calcular_descuento(Decimal("25000.00"), 5, "BIENVENIDA", HOY_VIGENTE)

    assert descuento == Decimal("3000.00")


@pytest.mark.parametrize("cupon", [None, "", "   "], ids=["none", "vacio", "espacios"])
def test_un_cupon_vacio_equivale_a_no_usar_cupon(cupon):
    carrito = [item("remera", "M", 1)]

    resultado = calcular_total(carrito, "CABA", cupon, HOY_VIGENTE)

    assert resultado["descuento"] == Decimal("0.00")


@pytest.mark.parametrize("cupon", ["egresados2026", " EGRESADOS2026 ", "Egresados2026"])
def test_egresados2026_no_distingue_mayusculas_ni_espacios(cupon):
    assert calcular_descuento(Decimal("11999.50"), 1, cupon, HOY_VIGENTE) == Decimal("1799.93")


@pytest.mark.parametrize("cupon", ["bienvenida", "  BIENVENIDA  "])
def test_bienvenida_no_distingue_mayusculas_ni_espacios(cupon):
    assert calcular_descuento(Decimal("24999.90"), 1, cupon, HOY_VIGENTE) == Decimal("3000.00")
