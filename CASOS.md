# Parte 1 — Casos de caja negra

Todos los casos salen **solo de `ESPECIFICACION.md`**. Los importes esperados
se calcularon a mano con los precios del catálogo y redondeo comercial
(medio centavo hacia arriba).

Notación: `item(p, t, c)` = `{"producto": p, "talle": t, "cantidad": c}`.
Salvo que se indique otra cosa, la zona es `"CABA"` y la fecha es
`2026-10-01` (cupón vigente).

## Decisiones ante ambigüedades de la especificación

La especificación no cubre explícitamente estos puntos. Se resuelven así, y
los tests siguen estas decisiones:

| # | Situación | Decisión | Justificación |
|---|---|---|---|
| D1 | `cantidad = 2.0` (float con valor entero) | `CANTIDAD_INVALIDA` | R3: "número entero"; un `float` no es un entero. |
| D2 | `cantidad = True` | `CANTIDAD_INVALIDA` | Un booleano no es una cantidad, aunque Python lo trate como `int`. |
| D3 | `cantidad = "3"` (texto) | `CANTIDAD_INVALIDA` | "Cualquier otro valor" → error de negocio, nunca `TypeError`. |
| D4 | Falta una clave del ítem (`producto`, `talle` o `cantidad`) | El error del campo que falta | §1: "Ante cualquier dato inválido … `CheckoutError`. Nunca otro tipo de excepción." |
| D5 | Producto, talle, zona o cupón que no son texto (`None`, `5`, `[]`) | El código de error del campo | Ídem D4. |
| D6 | Carrito `None` o que no es una lista (`5`, `3.5`) | `CARRITO_VACIO` | No tiene ítems. |
| D7 | Importes | Siempre `Decimal` con dos decimales (`Decimal("2500.00")`, `Decimal("0.00")`) | §6 y §7 muestran `"2500.00"` y `Decimal("2500.00")`. |
| D8 | Cupón inválido aunque el descuento por cantidad sea mayor | Igual se informa el error del cupón | R6 define el error sin excepciones; §3 valida el cupón antes de la zona. |
| D9 | Mínimo de `BIENVENIDA` | Se compara contra el subtotal **sin** descuento | R6: "Subtotal de $ 20.000 o más". |

---

## R1 — Catálogo y precios

**Particiones**

| Id | Partición | Tipo |
|---|---|---|
| P1.1 | Producto del catálogo (`buzo`, `remera`, `campera`) | Válida |
| P1.2 | Producto del catálogo con un `precio` propio en el ítem | Válida (se ignora el precio) |
| P1.3 | Ítem con claves extra (`color`, `nota`) | Válida (se ignoran) |
| P1.4 | Nombre que no está en el catálogo | Inválida |
| P1.5 | Nombre del catálogo con otra capitalización o con espacios | Inválida (se escribe "exactamente así") |
| P1.6 | Producto vacío, ausente o que no es texto | Inválida |

**Valores límite:** no hay rango numérico. Los bordes son de escritura:
`"buzo"` frente a `"Buzo"`, `" buzo"`, `"buzos"` y `""`.

**Casos**

| Caso | Entrada | Resultado esperado |
|---|---|---|
| C1.1 | `[item("buzo","M",1)]` → `calcular_subtotal` | `Decimal("24999.90")` |
| C1.2 | `[item("remera","M",1)]` | `Decimal("11999.50")` |
| C1.3 | `[item("campera","M",1)]` | `Decimal("47999.99")` |
| C1.4 | `[item("buzo","M",1, precio=1)]` | `Decimal("24999.90")` (precio ignorado) |
| C1.5 | `[item("buzo","M",1, color="rojo")]` | `Decimal("24999.90")` |
| C1.6 | `item("zapatilla","M",1)` | `PRODUCTO_INEXISTENTE` |
| C1.7 | `item("Buzo","M",1)` | `PRODUCTO_INEXISTENTE` |
| C1.8 | `item(" buzo","M",1)` | `PRODUCTO_INEXISTENTE` |
| C1.9 | `item("","M",1)` | `PRODUCTO_INEXISTENTE` |
| C1.10 | `{"talle":"M","cantidad":1}` (sin producto) | `PRODUCTO_INEXISTENTE` |
| C1.11 | `item(None,"M",1)` / `item(["buzo"],"M",1)` | `PRODUCTO_INEXISTENTE` (nunca `TypeError`) |

## R2 — Talles

**Particiones**

| Id | Partición | Tipo |
|---|---|---|
| P2.1 | Talle válido en mayúscula (`XS`, `S`, `M`, `L`, `XL`, `XXL`) | Válida |
| P2.2 | Talle válido en minúscula o mixto (`m`, `xL`) | Válida |
| P2.3 | Talle válido con espacios alrededor (`"  M "`) | Válida |
| P2.4 | Texto que no es un talle (`XXXL`, `XXS`, `"M L"`, `"MEDIANO"`) | Inválida |
| P2.5 | Vacío o solo espacios (`""`, `"   "`) | Inválida |
| P2.6 | Ausente o que no es texto (`None`, `5`) | Inválida |

**Valores límite:** los extremos de la lista (`XS` y `XXL`) y justo afuera
(`XXS` y `XXXL`). Espacios: uno, varios, al principio, al final y en el medio.

**Casos**

| Caso | Entrada (`validar_item`) | Resultado esperado |
|---|---|---|
| C2.1 | `item("buzo", t, 1)` para cada `t` de `XS…XXL` | Sin error |
| C2.2 | `item("buzo","m",1)` | Sin error |
| C2.3 | `item("buzo","xxl",1)` | Sin error |
| C2.4 | `item("buzo","  M ",1)` | Sin error |
| C2.5 | `item("buzo","XXXL",1)` | `TALLE_INVALIDO` |
| C2.6 | `item("buzo","XXS",1)` | `TALLE_INVALIDO` |
| C2.7 | `item("buzo","M L",1)` | `TALLE_INVALIDO` (espacio en el medio) |
| C2.8 | `item("buzo","",1)` / `item("buzo","   ",1)` | `TALLE_INVALIDO` |
| C2.9 | `item("buzo",None,1)` / `item("buzo",5,1)` / sin clave `talle` | `TALLE_INVALIDO` |

## R3 — Cantidad

**Particiones**

| Id | Partición | Tipo |
|---|---|---|
| P3.1 | Entero entre 1 y 10 | Válida |
| P3.2 | Entero menor a 1 (0 o negativo) | Inválida |
| P3.3 | Entero mayor a 10 | Inválida |
| P3.4 | No entero: `float` (`2.5`, `2.0`), texto (`"3"`), `bool`, `None`, ausente | Inválida |

**Valores límite:** 0 / **1** / 2 y 9 / **10** / 11.

**Casos**

| Caso | Entrada (`validar_item`) | Resultado esperado |
|---|---|---|
| C3.1 | `cantidad = 1` | Sin error (límite inferior) |
| C3.2 | `cantidad = 5` | Sin error |
| C3.3 | `cantidad = 10` | Sin error (límite superior, inclusive) |
| C3.4 | `cantidad = 0` | `CANTIDAD_INVALIDA` |
| C3.5 | `cantidad = -1` | `CANTIDAD_INVALIDA` |
| C3.6 | `cantidad = 11` | `CANTIDAD_INVALIDA` |
| C3.7 | `cantidad = 2.5` | `CANTIDAD_INVALIDA` |
| C3.8 | `cantidad = 2.0` | `CANTIDAD_INVALIDA` (D1) |
| C3.9 | `cantidad = "3"` | `CANTIDAD_INVALIDA` (D3) |
| C3.10 | `cantidad = True` | `CANTIDAD_INVALIDA` (D2) |
| C3.11 | `cantidad = None` / sin clave | `CANTIDAD_INVALIDA` |

## R4 — Carrito

**Particiones**

| Id | Partición | Tipo |
|---|---|---|
| P4.1 | Carrito con 1 ítem | Válida |
| P4.2 | Carrito con varios ítems | Válida |
| P4.3 | Carrito vacío (`[]`), `None` o que no es una lista | Inválida |
| P4.4 | Cualquier llamada (válida o con error) | El carrito recibido queda idéntico |

**Valores límite:** 0 y 1 ítems.

**Casos**

| Caso | Entrada | Resultado esperado |
|---|---|---|
| C4.1 | `calcular_total([], "CABA")` | `CARRITO_VACIO` |
| C4.2 | `calcular_subtotal([])` | `CARRITO_VACIO` |
| C4.3 | `calcular_total(None, "CABA")` / `calcular_total(5, "CABA")` | `CARRITO_VACIO` (D6) |
| C4.4 | `[item("buzo","M",1)]` | Subtotal `24999.90` |
| C4.5 | `[item("buzo","M",1), item("remera","S",2)]` | Subtotal `48998.90` |
| C4.6 | `carrito = [item("buzo"," m ",2, precio=1)]`; se copia con `deepcopy`; se llama a `calcular_total` | `carrito == copia` (no cambió ni el talle ni el precio) |
| C4.7 | Lo mismo con `validar_item(item)` | El dict queda igual |
| C4.8 | Carrito con un ítem inválido; `calcular_total` lanza error | El carrito queda igual |

## R5 — Descuento por cantidad

**Particiones**

| Id | Partición | Tipo |
|---|---|---|
| P5.1 | Total de prendas < 5 | Sin descuento |
| P5.2 | Total de prendas ≥ 5 en un solo ítem | 10 % |
| P5.3 | Total de prendas ≥ 5 sumando varios ítems | 10 % |

**Valores límite:** 4 / **5** / 6 prendas.

**Casos** (sin cupón)

| Caso | Entrada | Resultado esperado |
|---|---|---|
| C5.1 | 4 remeras (subtotal `47998.00`) | Descuento `0.00` |
| C5.2 | 5 remeras (subtotal `59997.50`) | Descuento `5999.75` |
| C5.3 | 6 remeras (subtotal `71997.00`) | Descuento `7199.70` |
| C5.4 | 2 buzos + 3 remeras (subtotal `85998.30`) | Descuento `8599.83` (suma de cantidades = 5) |
| C5.5 | `calcular_descuento(Decimal("1000.00"), 4)` | `Decimal("0.00")` |
| C5.6 | `calcular_descuento(Decimal("1000.00"), 5)` | `Decimal("100.00")` |

## R6 — Cupones

**Particiones**

| Id | Partición | Tipo |
|---|---|---|
| P6.1 | Sin cupón: `None`, `""`, solo espacios | Válida (sin descuento por cupón) |
| P6.2 | `EGRESADOS2026` con fecha ≤ 30/11/2026 | Válida (15 %) |
| P6.3 | `EGRESADOS2026` con fecha > 30/11/2026 | Inválida → `CUPON_VENCIDO` |
| P6.4 | `BIENVENIDA` con subtotal ≥ 20.000 | Válida ($ 3.000) |
| P6.5 | `BIENVENIDA` con subtotal < 20.000 | Inválida → `CUPON_MINIMO_NO_ALCANZADO` |
| P6.6 | Cupón válido con otra capitalización o con espacios | Válida |
| P6.7 | Código inexistente (incluidos códigos "de prueba" como `DEBUG100`) | Inválida → `CUPON_INVALIDO` |
| P6.8 | Cupón y R5 aplicables a la vez | Se aplica el mayor, no la suma |
| P6.9 | Fecha omitida | Se usa la fecha del día de la llamada |

**Valores límite**
- Fecha: 29/11/2026, **30/11/2026** (vigente) y 01/12/2026 (vencido).
- Mínimo: subtotal 19.999,99 / **20.000,00** / 20.000,01.
- Descuento ≤ subtotal: con los cupones reales nunca se alcanza (15 % < 100 %
  y $ 3.000 < $ 20.000 de mínimo). Se verifica que el descuento resultante sea
  siempre menor o igual al subtotal.

**Casos**

| Caso | Entrada | Resultado esperado |
|---|---|---|
| C6.1 | 1 remera, `cupon=None` | Descuento `0.00` |
| C6.2 | 1 remera, `cupon=""` | Descuento `0.00` (no es error) |
| C6.3 | 1 remera, `cupon="   "` | Descuento `0.00` (no es error) |
| C6.4 | 1 remera, `EGRESADOS2026`, fecha 2026-10-01 | Descuento `1799.93` |
| C6.5 | 1 remera, `EGRESADOS2026`, fecha **2026-11-30** | Descuento `1799.93` (último día, inclusive) |
| C6.6 | 1 remera, `EGRESADOS2026`, fecha 2026-12-01 | `CUPON_VENCIDO` |
| C6.7 | 1 remera, `" egresados2026 "` | Descuento `1799.93` |
| C6.8 | 1 buzo (24.999,90), `BIENVENIDA` | Descuento `3000.00` |
| C6.9 | 1 remera (11.999,50), `BIENVENIDA` | `CUPON_MINIMO_NO_ALCANZADO` |
| C6.10 | `calcular_descuento(Decimal("20000.00"), 1, "BIENVENIDA")` | `Decimal("3000.00")` (límite) |
| C6.11 | `calcular_descuento(Decimal("19999.99"), 1, "BIENVENIDA")` | `CUPON_MINIMO_NO_ALCANZADO` |
| C6.12 | `"bienvenida"` con 1 buzo | Descuento `3000.00` |
| C6.13 | `"PROMO10"` | `CUPON_INVALIDO` |
| C6.14 | `"DEBUG100"` | `CUPON_INVALIDO` (solo existen dos cupones) |
| C6.15 | 5 remeras (59.997,50) + `EGRESADOS2026` | Descuento `8999.63` (15 % > 10 %; no `14999.38`) |
| C6.16 | 5 remeras + `BIENVENIDA` | Descuento `5999.75` (10 % > $ 3.000; no `8999.75`) |
| C6.17 | 5 remeras + `"PROMO10"` | `CUPON_INVALIDO` (D8) |
| C6.18 | `EGRESADOS2026` sin `fecha`, con el día de la llamada fijado en 2026-11-30 | Descuento aplicado |
| C6.19 | `EGRESADOS2026` sin `fecha`, con el día de la llamada fijado en 2026-12-01 | `CUPON_VENCIDO` |
| C6.20 | `cupon=123` (no es texto) | `CUPON_INVALIDO` |

## R7 — Dinero y redondeo

**Particiones**

| Id | Partición | Tipo |
|---|---|---|
| P7.1 | Porcentaje con resultado exacto al centavo | Sin redondeo |
| P7.2 | Porcentaje con medio centavo exacto (…,xx5) | Redondea hacia arriba |
| P7.3 | Porcentaje con fracción menor a medio centavo | Redondea hacia abajo |
| P7.4 | Tipo de todos los importes devueltos | Siempre `Decimal` |

**Valores límite:** fracción `…,xx4` / **`…,xx5`** / `…,xx6`.

**Casos**

| Caso | Entrada | Resultado esperado |
|---|---|---|
| C7.1 | 15 % de `11999.50` (= 1.799,925) | `Decimal("1799.93")`, no `1799.92` |
| C7.2 | 15 % de `59997.50` (= 8.999,625) | `Decimal("8999.63")` |
| C7.3 | 10 % de `85998.30` (= 8.599,83) | `Decimal("8599.83")` |
| C7.4 | `calcular_descuento(Decimal("100.03"), 1, "EGRESADOS2026", 2026-10-01)` (= 15,0045) | `Decimal("15.00")` |
| C7.5 | `calcular_total` de cualquier compra | Las cuatro claves son instancia de `Decimal` |
| C7.6 | `calcular_envio(...)` | Devuelve `Decimal`, también cuando es `0` |
| C7.7 | `calcular_subtotal` de 3 buzos | `Decimal("74999.70")` exacto (en `float` daría `74999.70000000001`) |

## R8 — Envío

**Particiones**

| Id | Partición | Tipo |
|---|---|---|
| P8.1 | Zona válida (`CABA`, `GBA`, `INTERIOR`, `RETIRO`), subtotal con descuento < 60.000 | Costo de la tabla |
| P8.2 | Zona válida con otra capitalización o con espacios | Válida |
| P8.3 | Subtotal con descuento ≥ 60.000 | Envío gratis |
| P8.4 | Subtotal **sin** descuento ≥ 60.000, pero **con** descuento < 60.000 | Se cobra el envío |
| P8.5 | Zona inexistente, vacía o que no es texto | Inválida → `ZONA_INVALIDA` |

**Valores límite:** 59.999,99 / **60.000,00** / 60.000,01.

**Casos**

| Caso | Entrada | Resultado esperado |
|---|---|---|
| C8.1 | `calcular_envio(Decimal("10000.00"), "CABA")` | `Decimal("2500.00")` |
| C8.2 | … `"GBA"` | `Decimal("4000.00")` |
| C8.3 | … `"INTERIOR"` | `Decimal("6500.00")` |
| C8.4 | … `"RETIRO"` | `Decimal("0.00")` |
| C8.5 | … `"  caba "` | `Decimal("2500.00")` |
| C8.6 | `calcular_envio(Decimal("59999.99"), "CABA")` | `Decimal("2500.00")` |
| C8.7 | `calcular_envio(Decimal("60000.00"), "CABA")` | `Decimal("0.00")` (límite) |
| C8.8 | `calcular_envio(Decimal("60000.01"), "INTERIOR")` | `Decimal("0.00")` |
| C8.9 | 2 buzos + 1 remera (61.999,30) + `BIENVENIDA` → 58.999,30, CABA | Envío `2500.00` |
| C8.10 | 3 buzos (74.999,70), sin cupón, CABA | Envío `0.00` |
| C8.11 | zona `"Córdoba"`, `""`, `None` | `ZONA_INVALIDA` (nunca otra excepción) |

## R9 — Total

**Particiones**

| Id | Partición | Tipo |
|---|---|---|
| P9.1 | Sin descuento y con costo de envío | Válida: total = subtotal + envío |
| P9.2 | Con descuento y con costo de envío | Válida: total = subtotal − descuento + envío |
| P9.3 | Sin descuento y con envío gratis por monto | Válida: total = subtotal |
| P9.4 | Con descuento y con envío gratis por monto | Válida: total = subtotal − descuento |
| P9.5 | Envío $ 0 por la zona (`RETIRO`) | Válida: total = subtotal − descuento |
| P9.6 | Compra con cualquier dato inválido | Inválida: no hay total, se lanza el `CheckoutError` de R1 a R8 |

**Valores límite:** descuento `0.00` frente a descuento mayor a cero; envío
justo en el umbral (subtotal con descuento 59.999,99 paga envío y 60.000,00
no), donde el total salta el costo del envío.

| Caso | Entrada | Resultado esperado |
|---|---|---|
| C9.1 | 2 buzos M, CABA, sin cupón (ejemplo de la §5) | `{"subtotal": 49999.80, "descuento": 0.00, "envio": 2500.00, "total": 52499.80}` |
| C9.2 | 1 remera M, CABA, `EGRESADOS2026`, 2026-10-01 (ejemplo de la §6) | `{11999.50, 1799.93, 2500.00, 12699.57}` |
| C9.3 | 2 buzos + 1 remera, CABA, `BIENVENIDA` | `{61999.30, 3000.00, 2500.00, 61499.30}` |
| C9.4 | 3 buzos, CABA | `{74999.70, 0.00, 0.00, 74999.70}` |
| C9.5 | 5 remeras, `EGRESADOS2026`, CABA | `{59997.50, 8999.63, 2500.00, 53497.87}` |
| C9.6 | 3 buzos, `EGRESADOS2026`, CABA | `{74999.70, 11249.96, 0.00, 63749.74}` (P9.4) |
| C9.7 | 1 buzo, RETIRO, sin cupón | `{24999.90, 0.00, 0.00, 24999.90}` (P9.5) |
| C9.8 | 1 buzo, zona `"MARTE"` | `ZONA_INVALIDA`, sin total (P9.6) |

## Orden de validación (§3)

| Caso | Entrada | Resultado esperado |
|---|---|---|
| C§3.1 | `calcular_total([], "MARTE", "PROMO")` | `CARRITO_VACIO` |
| C§3.2 | `item("zapatilla","XXXL",0)` | `PRODUCTO_INEXISTENTE` (producto antes que talle) |
| C§3.3 | `item("buzo","XXXL",0)` | `TALLE_INVALIDO` (talle antes que cantidad) |
| C§3.4 | `[item("buzo","XXXL",1), item("zapatilla","M",1)]` | `TALLE_INVALIDO` (primer ítem primero) |
| C§3.5 | Ítem con cantidad 0 + cupón `"PROMO"` | `CANTIDAD_INVALIDA` |
| C§3.6 | Carrito válido + cupón `"PROMO"` + zona `"MARTE"` | `CUPON_INVALIDO` |
| C§3.7 | Carrito válido + sin cupón + zona `"MARTE"` | `ZONA_INVALIDA` |

---

## R10 — Persistencia (`pedidos.py`)

**Particiones**

| Id | Partición | Tipo |
|---|---|---|
| P10.1 | Compra válida | Se guarda el pedido con sus ítems |
| P10.2 | Compra con `CheckoutError` | Se propaga el error; no queda nada guardado |
| P10.3 | Lectura desde otra conexión | Ve el pedido completo |
| P10.4 | Ítem con `precio` del cliente | Se guarda el precio del catálogo |
| P10.5 | Datos con mayúsculas o espacios | Se guardan normalizados |
| P10.6 | Cupón vacío o solo espacios | Se guarda `None` |
| P10.7 | Id existente / inexistente | Pedido / `None` |
| P10.8 | Email con distinta capitalización o espacios en `pedidos_de` | Mismos pedidos |
| P10.9 | Email con caracteres SQL (`'`, `--`, `OR`) | Se trata como texto literal |

**Valores límite:** cero, uno y varios pedidos por email; id 0, último id e
id siguiente al último; cupón `""` frente a `"   "`.

**Casos**

| Caso | Entrada | Resultado esperado |
|---|---|---|
| C10.1 | `guardar_pedido(con, "ana@mail.com", [item("remera","M",1)], "CABA", "EGRESADOS2026", 2026-10-01)` y luego `obtener_pedido` | Montos `Decimal("11999.50")`, `Decimal("1799.93")`, `Decimal("2500.00")`, `Decimal("12699.57")`; iguales a `calcular_total` |
| C10.2 | `guardar_pedido` con talle `XXXL` | Lanza `CheckoutError` `TALLE_INVALIDO`; 0 filas en `pedidos` y 0 en `items`, vistas desde otra conexión |
| C10.3 | `guardar_pedido` con cupón vencido | Lanza `CUPON_VENCIDO`; 0 pedidos |
| C10.4 | Guardar y leer desde **otra** conexión | Mismo pedido, con todos sus ítems y montos |
| C10.5 | Guardar y cerrar la conexión sin nada más; abrir otra | El pedido sigue completo |
| C10.6 | `item("buzo","M",1, precio=1)` | `precio_unitario == Decimal("24999.90")` y subtotal `24999.90` |
| C10.7 | Email `"  Ana@Mail.COM "`, zona `" caba "`, talle `" m "`, cupón `" egresados2026 "` | `"ana@mail.com"`, `"CABA"`, `"M"`, `"EGRESADOS2026"` |
| C10.8 | `cupon=""` / `cupon="   "` | `cupon is None` |
| C10.9 | `obtener_pedido(con, 999)` | `None` |
| C10.10 | Dos pedidos de `ana@mail.com`; `pedidos_de(con, " ANA@mail.com ")` | Los dos, el más reciente primero |
| C10.11 | `pedidos_de(con, "' OR '1'='1")` con pedidos de otros | `[]` |
| C10.12 | Pedido de `o'brien@mail.com`; `pedidos_de(con, "o'brien@mail.com")` | Ese pedido, sin excepción |
| C10.13 | `pedidos_de` de un email sin pedidos | `[]` |

## R11 — API HTTP (`api.py`)

**Particiones**

| Id | Partición | Tipo |
|---|---|---|
| P11.1 | POST válido | 201 con id y montos como texto |
| P11.2 | GET de un id existente | 200 con el pedido completo y montos como texto |
| P11.3 | Error de negocio (`CheckoutError`) | 422 con el `code` |
| P11.4 | Cuerpo que no es JSON | 400 `JSON_INVALIDO` |
| P11.5 | Falta email, zona o carrito, o tienen otro tipo | 400 `DATOS_INCOMPLETOS` |
| P11.6 | Fecha con otro formato o imposible | 400 `FECHA_INVALIDA` |
| P11.7 | GET de un id inexistente | 404 `PEDIDO_INEXISTENTE` |
| P11.8 | Ruta inexistente | 404 `RUTA_INEXISTENTE` |
| P11.9 | Cualquier entrada | Nunca 500; siempre `{"error": {"code", "message"}}` |

**Valores límite:** fecha `2026-11-30` frente a `2026-12-01`; `2026-02-29`
(no existe); `2026-13-01`; `20261130` (sin guiones); cuerpo vacío.

**Casos**

| Caso | Entrada | Resultado esperado |
|---|---|---|
| C11.1 | POST con 1 remera, `EGRESADOS2026`, `fecha "2026-11-30"` | 201 `{"id": 1, "subtotal": "11999.50", "descuento": "1799.93", "envio": "2500.00", "total": "12699.57"}` |
| C11.2 | POST y luego GET `/api/v1/pedidos/{id}` | 200, pedido con el formato de la §6; montos y `precio_unitario` como texto |
| C11.3 | POST con talle `XXXL` | 422 `TALLE_INVALIDO` |
| C11.4 | POST con cada código de `CheckoutError` (producto, talle, cantidad, carrito vacío, cupón inválido, vencido, mínimo, zona) | 422 con ese código |
| C11.5 | POST con `EGRESADOS2026` y `fecha "2026-12-01"` | 422 `CUPON_VENCIDO` |
| C11.6 | POST con cuerpo `{no es json` | 400 `JSON_INVALIDO` |
| C11.7 | POST sin `email` / sin `zona` / sin `carrito` | 400 `DATOS_INCOMPLETOS` |
| C11.8 | POST con `email: 123` / `carrito: "buzo"` / `zona: ["CABA"]` | 400 `DATOS_INCOMPLETOS` |
| C11.9 | POST con un JSON que no es objeto (`[1, 2]`) | 400 `DATOS_INCOMPLETOS` |
| C11.10 | POST con `fecha "30/11/2026"` / `"2026-13-01"` / `"20261130"` / `"2026-02-29"` | 400 `FECHA_INVALIDA` |
| C11.11 | GET `/api/v1/pedidos/999` | 404 `PEDIDO_INEXISTENTE` |
| C11.12 | GET `/api/v1/otra` / POST `/api/v1/otra` | 404 `RUTA_INEXISTENTE` |
| C11.13 | POST sin `cupon` ni `fecha` | 201 |
