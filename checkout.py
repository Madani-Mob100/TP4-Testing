import json
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


class CheckoutError(Exception):
    def __init__(self, code, mensaje):
        super().__init__(mensaje)
        self.code = code
        self.mensaje = mensaje


CATALOGO = {
    "buzo": Decimal("24999.90"),
    "remera": Decimal("11999.50"),
    "campera": Decimal("47999.99"),
}

TALLES = ["XS", "S", "M", "L", "XL", "XXL"]

CUPONES = {
    "EGRESADOS2026": {"tipo": "porcentaje", "valor": Decimal("0.15"), "vence": date(2026, 11, 30)},
    "BIENVENIDA": {"tipo": "fijo", "valor": Decimal("3000.00"), "minimo": Decimal("20000.00")},
}

ENVIOS = {
    "CABA": Decimal("2500.00"),
    "GBA": Decimal("4000.00"),
    "INTERIOR": Decimal("6500.00"),
    "RETIRO": Decimal("0.00"),
}

CERO = Decimal("0.00")
CENTAVO = Decimal("0.01")


def _redondear(importe):
    return importe.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _normalizar(texto):
    if not isinstance(texto, str):
        return None
    return texto.strip().upper()


def validar_item(item):
    if not isinstance(item, dict):
        raise CheckoutError("PRODUCTO_INEXISTENTE", f"Ítem inválido: {item!r}")

    producto = item.get("producto")
    if not isinstance(producto, str) or producto not in CATALOGO:
        raise CheckoutError("PRODUCTO_INEXISTENTE", f"Producto inexistente: {producto!r}")

    talle = _normalizar(item.get("talle"))

    if talle not in TALLES:
        raise CheckoutError("TALLE_INVALIDO", f"Talle inválido: {item.get('talle')!r}")

    cantidad = item.get("cantidad")
    if type(cantidad) is not int or not 1 <= cantidad <= 10:
        raise CheckoutError("CANTIDAD_INVALIDA", "La cantidad debe estar entre 1 y 10")


def calcular_subtotal(carrito):
    if not carrito:
        raise CheckoutError("CARRITO_VACIO", "El carrito está vacío")

    subtotal = CERO
    for item in carrito:
        validar_item(item)
        subtotal += CATALOGO[item["producto"]] * item["cantidad"]

    return subtotal


def _descuento_por_cupon(subtotal, cupon, fecha):
    codigo = "" if cupon is None else _normalizar(cupon)
    if codigo == "":
        return CERO

    if codigo not in CUPONES:
        raise CheckoutError("CUPON_INVALIDO", "El cupón no existe")

    datos = CUPONES[codigo]
    if datos["tipo"] == "porcentaje":
        if fecha > datos["vence"]:
            raise CheckoutError("CUPON_VENCIDO", "El cupón está vencido")
        return _redondear(subtotal * datos["valor"])

    if subtotal < datos["minimo"]:
        raise CheckoutError(
            "CUPON_MINIMO_NO_ALCANZADO",
            f"El cupón requiere una compra mínima de ${datos['minimo']}",
        )
    return datos["valor"]


def calcular_descuento(subtotal, cantidad_prendas, cupon=None, fecha=None):
    if fecha is None:
        fecha = date.today()

    por_cantidad = CERO
    if cantidad_prendas >= 5:
        por_cantidad = _redondear(subtotal * Decimal("0.10"))

    por_cupon = _descuento_por_cupon(subtotal, cupon, fecha)
    return min(max(por_cantidad, por_cupon), subtotal)


def calcular_envio(subtotal, zona):
    zona_normalizada = _normalizar(zona)

    if zona_normalizada not in ENVIOS:
        raise CheckoutError(
            "ZONA_INVALIDA",
            f"Zona inválida: {zona!r}. Opciones: {', '.join(ENVIOS)}",
        )

    if subtotal >= 60000:
        return CERO

    return ENVIOS[zona_normalizada]


def calcular_total(carrito, zona, cupon=None, fecha=None):
    subtotal = calcular_subtotal(carrito)

    prendas = 0
    for item in carrito:
        prendas = prendas + item["cantidad"]

    descuento = calcular_descuento(subtotal, prendas, cupon, fecha)
    envio = calcular_envio(subtotal - descuento, zona)
    total = subtotal - descuento + envio

    resultado = {
        "subtotal": subtotal,
        "descuento": descuento,
        "envio": envio,
        "total": total,
    }
    return resultado
