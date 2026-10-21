import json
import threading
import urllib.error
import urllib.request

import pytest

import api

RUTA = "/api/v1/pedidos"


@pytest.fixture
def url(tmp_path):
    servidor = api.crear_servidor(str(tmp_path / "tienda.db"), 0)
    threading.Thread(target=servidor.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_address[1]}"
    servidor.shutdown()
    servidor.server_close()


def pedir(url, metodo, ruta, cuerpo=None, crudo=None):
    datos = crudo if crudo is not None else (json.dumps(cuerpo).encode() if cuerpo is not None else None)
    req = urllib.request.Request(url + ruta, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def compra(**cambios):
    cuerpo = {"email": "ana@mail.com", "zona": "CABA",
              "carrito": [{"producto": "buzo", "talle": "M", "cantidad": 1}]}
    cuerpo.update(cambios)
    return cuerpo


def test_una_ruta_inexistente_devuelve_404(url):
    status, cuerpo = pedir(url, "GET", "/api/v1/otra")
    assert status == 404
    assert cuerpo["error"]["code"] == "RUTA_INEXISTENTE"


def codigo_de_error(cuerpo):
    error = cuerpo.get("error") if isinstance(cuerpo, dict) else None
    return error.get("code") if isinstance(error, dict) else error


# --- POST /api/v1/pedidos ---------------------------------------------------

def test_crear_un_pedido_devuelve_201_con_los_montos_como_texto(url):
    cuerpo_compra = compra(carrito=[{"producto": "remera", "talle": "M", "cantidad": 1}],
                           cupon="EGRESADOS2026", fecha="2026-11-30")

    status, cuerpo = pedir(url, "POST", RUTA, cuerpo_compra)

    assert status == 201
    assert type(cuerpo["id"]) is int
    assert cuerpo == {"id": cuerpo["id"], "subtotal": "11999.50", "descuento": "1799.93",
                      "envio": "2500.00", "total": "12699.57"}


def test_crear_un_pedido_sin_cupon_ni_fecha_devuelve_el_ejemplo_de_la_especificacion(url):
    cuerpo_compra = compra(carrito=[{"producto": "buzo", "talle": "M", "cantidad": 2}])

    status, cuerpo = pedir(url, "POST", RUTA, cuerpo_compra)

    assert (status, cuerpo["subtotal"], cuerpo["descuento"], cuerpo["envio"], cuerpo["total"]) == (
        201, "49999.80", "0.00", "2500.00", "52499.80")


# --- GET /api/v1/pedidos/{id} -----------------------------------------------

def test_un_pedido_creado_se_puede_consultar_completo_con_montos_como_texto(url):
    cuerpo_compra = compra(email="  Ana@Mail.com ", zona=" caba ",
                           carrito=[{"producto": "remera", "talle": "m", "cantidad": 1, "precio": 1}],
                           cupon="egresados2026", fecha="2026-11-30")
    _, creado = pedir(url, "POST", RUTA, cuerpo_compra)

    status, pedido = pedir(url, "GET", f"{RUTA}/{creado['id']}")

    assert status == 200
    assert pedido == {
        "id": creado["id"],
        "email": "ana@mail.com",
        "zona": "CABA",
        "cupon": "EGRESADOS2026",
        "subtotal": "11999.50",
        "descuento": "1799.93",
        "envio": "2500.00",
        "total": "12699.57",
        "items": [{"producto": "remera", "talle": "M", "cantidad": 1, "precio_unitario": "11999.50"}],
    }


def test_un_pedido_sin_cupon_queda_guardado_y_se_consulta_con_sus_items(url):
    _, creado = pedir(url, "POST", RUTA, compra())

    status, pedido = pedir(url, "GET", f"{RUTA}/{creado['id']}")

    assert status == 200
    assert (pedido["subtotal"], pedido["envio"], pedido["total"]) == ("24999.90", "2500.00", "27499.90")
    assert pedido["items"] == [{"producto": "buzo", "talle": "M", "cantidad": 1, "precio_unitario": "24999.90"}]


def test_un_pedido_inexistente_devuelve_404(url):
    status, cuerpo = pedir(url, "GET", f"{RUTA}/999")

    assert (status, codigo_de_error(cuerpo)) == (404, "PEDIDO_INEXISTENTE")


def test_una_compra_rechazada_no_deja_un_pedido_consultable(url):
    pedir(url, "POST", RUTA, compra(zona="MARTE"))

    status, cuerpo = pedir(url, "GET", f"{RUTA}/1")

    assert (status, codigo_de_error(cuerpo)) == (404, "PEDIDO_INEXISTENTE")


# --- Errores de negocio: 422 ------------------------------------------------

@pytest.mark.parametrize("cambios, codigo", [
    ({"carrito": [{"producto": "zapatilla", "talle": "M", "cantidad": 1}]}, "PRODUCTO_INEXISTENTE"),
    ({"carrito": [{"producto": "buzo", "talle": "XXXL", "cantidad": 1}]}, "TALLE_INVALIDO"),
    ({"carrito": [{"producto": "buzo", "talle": "M", "cantidad": 11}]}, "CANTIDAD_INVALIDA"),
    ({"carrito": []}, "CARRITO_VACIO"),
    ({"cupon": "PROMO10"}, "CUPON_INVALIDO"),
    ({"cupon": "EGRESADOS2026", "fecha": "2026-12-01"}, "CUPON_VENCIDO"),
    ({"carrito": [{"producto": "remera", "talle": "M", "cantidad": 1}], "cupon": "BIENVENIDA"},
     "CUPON_MINIMO_NO_ALCANZADO"),
    ({"zona": "MARTE"}, "ZONA_INVALIDA"),
], ids=["producto", "talle", "cantidad", "carrito_vacio", "cupon_invalido", "cupon_vencido",
        "cupon_minimo", "zona"])
def test_un_error_de_negocio_devuelve_422_con_el_codigo_de_checkout(url, cambios, codigo):
    status, cuerpo = pedir(url, "POST", RUTA, compra(**cambios))

    assert (status, codigo_de_error(cuerpo)) == (422, codigo)


def test_un_error_tiene_el_formato_de_la_especificacion(url):
    _, cuerpo = pedir(url, "POST", RUTA, compra(zona="MARTE"))

    assert list(cuerpo) == ["error"]
    assert sorted(cuerpo["error"]) == ["code", "message"]
    assert type(cuerpo["error"]["message"]) is str
    assert cuerpo["error"]["message"] != ""


# --- Errores de la request: 400 ---------------------------------------------

@pytest.mark.parametrize("crudo", [b"{no es json", b"", "{\"email\": \"ana\"".encode()], ids=["roto", "vacio", "incompleto"])
def test_un_cuerpo_que_no_es_json_devuelve_400(url, crudo):
    status, cuerpo = pedir(url, "POST", RUTA, crudo=crudo)

    assert (status, codigo_de_error(cuerpo)) == (400, "JSON_INVALIDO")


@pytest.mark.parametrize("campo", ["email", "zona", "carrito"])
def test_si_falta_un_dato_obligatorio_devuelve_400(url, campo):
    cuerpo_compra = compra()
    del cuerpo_compra[campo]

    status, cuerpo = pedir(url, "POST", RUTA, cuerpo_compra)

    assert (status, codigo_de_error(cuerpo)) == (400, "DATOS_INCOMPLETOS")


@pytest.mark.parametrize("cambios", [
    {"email": 123},
    {"zona": ["CABA"]},
    {"carrito": "buzo"},
    {"carrito": None},
], ids=["email_numero", "zona_lista", "carrito_texto", "carrito_null"])
def test_si_un_dato_obligatorio_tiene_otro_tipo_devuelve_400(url, cambios):
    status, cuerpo = pedir(url, "POST", RUTA, compra(**cambios))

    assert (status, codigo_de_error(cuerpo)) == (400, "DATOS_INCOMPLETOS")


def test_un_json_que_no_es_un_objeto_devuelve_400(url):
    status, cuerpo = pedir(url, "POST", RUTA, [compra()])

    assert (status, codigo_de_error(cuerpo)) == (400, "DATOS_INCOMPLETOS")


@pytest.mark.parametrize("fecha", ["30/11/2026", "2026-13-01", "2026-02-29", "20261130", "2026-1-5", "", 20261130])
def test_una_fecha_que_no_es_aaaa_mm_dd_devuelve_400(url, fecha):
    status, cuerpo = pedir(url, "POST", RUTA, compra(fecha=fecha))

    assert (status, codigo_de_error(cuerpo)) == (400, "FECHA_INVALIDA")


# --- Rutas inexistentes: 404 -------------------------------------------------

@pytest.mark.parametrize("metodo, ruta", [
    ("POST", "/api/v1/otra"),
    ("POST", "/api/v1/pedidos/1"),
    ("GET", "/api/v1/pedidos/abc"),
    ("GET", "/api/v1/pedidos"),
])
def test_otras_rutas_inexistentes_devuelven_404(url, metodo, ruta):
    status, cuerpo = pedir(url, metodo, ruta)

    assert (status, codigo_de_error(cuerpo)) == (404, "RUTA_INEXISTENTE")
