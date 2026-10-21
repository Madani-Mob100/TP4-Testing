from datetime import date
from decimal import Decimal

import pytest

import pedidos
from checkout import CheckoutError, calcular_total

HOY_VIGENTE = date(2026, 10, 1)


@pytest.fixture
def ruta(tmp_path):
    return str(tmp_path / "tienda.db")


@pytest.fixture
def con(ruta):
    conexion = pedidos.conectar(ruta)
    pedidos.crear_esquema(conexion)
    yield conexion
    conexion.close()


def item(producto="buzo", talle="M", cantidad=1, **extra):
    return {"producto": producto, "talle": talle, "cantidad": cantidad, **extra}


def contar(ruta, tabla):
    assert tabla in ("pedidos", "items")
    otra = pedidos.conectar(ruta)
    try:
        return otra.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    finally:
        otra.close()


def test_un_id_inexistente_devuelve_none(con):
    assert pedidos.obtener_pedido(con, 999) is None


def leer_desde_otra_conexion(ruta, pedido_id):
    otra = pedidos.conectar(ruta)
    try:
        return pedidos.obtener_pedido(otra, pedido_id)
    finally:
        otra.close()


def test_si_checkout_falla_el_error_se_propaga_y_no_queda_nada_guardado(ruta, con):
    carrito = [item(talle="XXXL")]

    with pytest.raises(CheckoutError) as error:
        pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA")

    assert error.value.code == "TALLE_INVALIDO"
    assert (contar(ruta, "pedidos"), contar(ruta, "items")) == (0, 0)


def test_otra_conexion_ve_el_pedido_completo_con_todos_sus_items(ruta, con):
    carrito = [item("buzo", "M", 1), item("remera", "S", 2)]

    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA")
    pedido = leer_desde_otra_conexion(ruta, pedido_id)

    assert pedido["total"] == Decimal("51498.90")
    assert [(i["producto"], i["cantidad"]) for i in pedido["items"]] == [("buzo", 1), ("remera", 2)]


def test_los_montos_guardados_son_decimal_e_identicos_a_los_de_calcular_total(con):
    carrito = [item("remera", "M", 1)]
    esperado = calcular_total(carrito, "CABA", "EGRESADOS2026", HOY_VIGENTE)

    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA", "EGRESADOS2026", HOY_VIGENTE)
    pedido = pedidos.obtener_pedido(con, pedido_id)

    montos = {clave: pedido[clave] for clave in esperado}
    assert montos == {"subtotal": Decimal("11999.50"), "descuento": Decimal("1799.93"),
                      "envio": Decimal("2500.00"), "total": Decimal("12699.57")}
    assert montos == esperado
    assert all(type(monto) is Decimal for monto in montos.values())


def test_un_email_con_sql_no_altera_la_consulta_de_pedidos_de(con):
    pedidos.guardar_pedido(con, "ana@mail.com", [item()], "CABA")
    pedidos.guardar_pedido(con, "beto@mail.com", [item()], "CABA")

    encontrados = pedidos.pedidos_de(con, "' OR '1'='1")

    assert encontrados == []
