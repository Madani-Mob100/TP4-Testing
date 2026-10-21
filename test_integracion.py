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


# --- Los importes salen de checkout y no se pierde precisión ---------------

def test_el_pedido_guardado_tiene_los_montos_exactos_de_la_especificacion(con):
    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", [item("remera")], "CABA",
                                       "EGRESADOS2026", HOY_VIGENTE)

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido == {
        "id": pedido_id,
        "email": "ana@mail.com",
        "zona": "CABA",
        "cupon": "EGRESADOS2026",
        "subtotal": Decimal("11999.50"),
        "descuento": Decimal("1799.93"),
        "envio": Decimal("2500.00"),
        "total": Decimal("12699.57"),
        "items": [
            {"producto": "remera", "talle": "M", "cantidad": 1, "precio_unitario": Decimal("11999.50")},
        ],
    }


def test_los_montos_guardados_son_decimal_e_identicos_a_los_de_calcular_total(con):
    carrito = [item("buzo", "M", 2), item("campera", "L", 1), item("remera", "S", 2)]
    esperado = calcular_total(carrito, "GBA", "EGRESADOS2026", HOY_VIGENTE)

    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", carrito, "GBA", "EGRESADOS2026", HOY_VIGENTE)
    pedido = pedidos.obtener_pedido(con, pedido_id)

    montos = {clave: pedido[clave] for clave in esperado}
    assert montos == esperado
    assert all(type(monto) is Decimal for monto in montos.values())


def test_el_precio_unitario_es_el_del_catalogo_y_no_el_que_manda_el_cliente(con):
    carrito = [item("buzo", "M", 2, precio=1)]

    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA")
    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido["items"][0]["precio_unitario"] == Decimal("24999.90")
    assert type(pedido["items"][0]["precio_unitario"]) is Decimal
    assert pedido["subtotal"] == Decimal("49999.80")


# --- Si checkout falla no queda nada guardado ------------------------------

def test_si_checkout_falla_el_error_se_propaga(con):
    carrito = [item(talle="XXXL")]

    with pytest.raises(CheckoutError) as error:
        pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA")

    assert error.value.code == "TALLE_INVALIDO"


@pytest.mark.parametrize("carrito, zona, cupon", [
    ([item(talle="XXXL")], "CABA", None),
    ([item("remera")], "CABA", "PROMO10"),
    ([item("remera")], "MARTE", None),
    ([item("buzo"), item("zapatilla")], "CABA", None),
], ids=["talle", "cupon", "zona", "segundo_item"])
def test_si_checkout_falla_no_queda_ni_el_pedido_ni_sus_items(ruta, con, carrito, zona, cupon):
    with pytest.raises(CheckoutError):
        pedidos.guardar_pedido(con, "ana@mail.com", carrito, zona, cupon, HOY_VIGENTE)

    assert (contar(ruta, "pedidos"), contar(ruta, "items")) == (0, 0)


def test_un_cupon_vencido_no_deja_ningun_pedido_guardado(ruta, con):
    with pytest.raises(CheckoutError):
        pedidos.guardar_pedido(con, "ana@mail.com", [item("remera")], "CABA",
                               "EGRESADOS2026", date(2026, 12, 1))

    assert contar(ruta, "pedidos") == 0


# --- El pedido es definitivo ----------------------------------------------

def test_otra_conexion_ve_el_pedido_completo_con_todos_sus_items(ruta, con):
    carrito = [item("buzo", "M", 1), item("remera", "S", 2)]

    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA")
    pedido = leer_desde_otra_conexion(ruta, pedido_id)

    assert pedido["total"] == Decimal("51498.90")
    assert [(i["producto"], i["cantidad"]) for i in pedido["items"]] == [("buzo", 1), ("remera", 2)]


def test_el_pedido_sigue_completo_despues_de_cerrar_la_conexion_que_lo_guardo(ruta):
    conexion = pedidos.conectar(ruta)
    pedidos.crear_esquema(conexion)
    pedido_id = pedidos.guardar_pedido(conexion, "ana@mail.com", [item("campera", "L", 1)], "INTERIOR")
    conexion.close()

    pedido = leer_desde_otra_conexion(ruta, pedido_id)

    assert pedido["total"] == Decimal("54499.99")
    assert contar(ruta, "items") == 1


# --- Datos normalizados -----------------------------------------------------

def test_los_datos_se_guardan_normalizados(con):
    carrito = [item("remera", " m ", 1)]

    pedido_id = pedidos.guardar_pedido(con, "  Ana@Mail.COM ", carrito, " caba ",
                                       " egresados2026 ", HOY_VIGENTE)
    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert (pedido["email"], pedido["zona"], pedido["cupon"], pedido["items"][0]["talle"]) == (
        "ana@mail.com", "CABA", "EGRESADOS2026", "M")


@pytest.mark.parametrize("cupon", [None, "", "   "], ids=["none", "vacio", "espacios"])
def test_un_cupon_vacio_se_guarda_como_none(con, cupon):
    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", [item()], "CABA", cupon)

    assert pedidos.obtener_pedido(con, pedido_id)["cupon"] is None


# --- Consultas ---------------------------------------------------------------

def test_pedidos_de_devuelve_del_mas_reciente_al_mas_antiguo_sin_importar_mayusculas(con):
    primero = pedidos.guardar_pedido(con, "ana@mail.com", [item("buzo")], "CABA")
    pedidos.guardar_pedido(con, "beto@mail.com", [item("remera")], "CABA")
    segundo = pedidos.guardar_pedido(con, "ANA@mail.com", [item("campera")], "GBA")

    encontrados = pedidos.pedidos_de(con, "  Ana@MAIL.com ")

    assert [p["id"] for p in encontrados] == [segundo, primero]


def test_pedidos_de_un_email_sin_pedidos_es_una_lista_vacia(con):
    pedidos.guardar_pedido(con, "ana@mail.com", [item()], "CABA")

    assert pedidos.pedidos_de(con, "nadie@mail.com") == []


@pytest.mark.parametrize("email", ["' OR '1'='1", "x' OR 1=1 --", "%"])
def test_un_email_con_sql_no_altera_la_consulta(con, email):
    pedidos.guardar_pedido(con, "ana@mail.com", [item()], "CABA")
    pedidos.guardar_pedido(con, "beto@mail.com", [item()], "CABA")

    assert pedidos.pedidos_de(con, email) == []


def test_un_email_con_apostrofe_se_busca_como_cualquier_otro(con):
    pedido_id = pedidos.guardar_pedido(con, "o'brien@mail.com", [item()], "CABA")

    encontrados = pedidos.pedidos_de(con, "O'Brien@mail.com")

    assert [p["id"] for p in encontrados] == [pedido_id]
