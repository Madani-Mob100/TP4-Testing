# Parte 2 — Auditoría

Salvo que se diga otra cosa, los números de línea son los del código **tal
como lo entregó la IA** (commit `Estado inicial`).

---

## Sección 1 — Los tests de la IA (`test_checkout_ia.py`)

### 1.1 Evaluación de cada test

| # | Test | Veredicto | Por qué |
|---|---|---|---|
| 1 | `test_subtotal` | **Tautológico** | El valor esperado sale de `CATALOGO["buzo"] * 2`, es decir, del mismo código que se prueba: si el precio del catálogo estuviera mal, el test también estaría mal. |
| 2 | `test_total_funciona` | **Inútil** | `assert resultado is not None` pasa con cualquier dict, incluso con importes absurdos; nunca puede fallar si la función devuelve algo. |
| 3 | `test_total_positivo` | **Débil** | `total > 0` acepta cualquier número positivo: no detecta un envío mal cobrado, un `float` en vez de `Decimal` ni un descuento mal calculado. |
| 4 | `test_cupon_egresados` | **Tautológico** | Calcula el esperado con la misma fórmula del código (`100000 * 0.15`, en `float`): repite la implementación en vez de usar un valor del negocio, elige un subtotal que no ejercita el redondeo y no prueba la fecha de vencimiento. |
| 5 | `test_envio_caba` | **Útil** | Compara contra un valor concreto de la tabla de R8 (`2500`). Es el único test cuyo oráculo es la especificación. Su límite: no prueba el umbral de envío gratis ni el tipo `Decimal`. |
| 6 | `test_descuento_por_cantidad` | **Débil** | Usa 6 prendas, justo un valor por encima del límite: el bug `> 5` (que excluye 5 prendas) pasa sin ser detectado. Es el ejemplo de "el valor límite que ni el código ni el test contemplaron". |
| 7 | `test_talle_valido` | **Débil** | No tiene `assert`: solo comprueba que un talle ya en mayúscula no explote. Camino feliz puro; no prueba minúsculas, espacios ni talles inválidos, y tampoco detecta que la función modifica el ítem. |
| 8 | `test_no_explota_con_varios_productos` | **Inútil** | El `try/except Exception: pass` traga cualquier error: el test es imposible de hacer fallar. No verifica ni siquiera que la función termine bien. |

Resumen: 1 útil, 3 débiles, 2 tautológicos y 2 inútiles.

### 1.2 Puntaje de mutación

```
$ python mutar.py --tests test_checkout_ia.py
Mutando checkout.py contra test_checkout_ia.py  (motor: pytest)

Mutantes generados : 29
Muertos            : 17
Sobrevivientes     : 12
Puntaje de mutación: 58.6%
```

El puntaje corresponde al `checkout.py` original, que es el que auditó esta
sección. Contra mi `checkout.py` corregido, la misma suite da 61,1 %.

Sobrevivientes: línea 40 (`<`→`<=` y `10`→`11`), 60 (`>`→`>=`), 72 (`<`→`<=`),
76 (`==`→`!=`), 77 (`<`→`<=`), 82 (`+`→`-`), 96 (`>=`→`>` y
`60000`→`60001`), 107 (`+`→`-`) y 111 (`+`→`-` y `-`→`+`).

Dato revelador: tres de los mutantes que sobreviven (`< 10` → `<= 10`,
`> 5` → `>= 5` y `fecha < vence` → `fecha <= vence`) **son exactamente la
corrección del bug**. La suite no distingue el código roto del código
correcto. Por la misma razón, los ocho tests de la IA **siguen pasando contra
mi `checkout.py` corregido**: no detectan ni la falla ni el arreglo.

### 1.3 ¿Por qué cubre casi el 80 % y no detecta ninguna falla?

```
Name          Stmts   Miss  Cover   Missing          (cobertura de líneas)
checkout.py      62     14    77%   7-9, 38, 41, 50-51, 67, 73, 76-82, 91
checkout.py      62     14     26      6    73%      (cobertura de ramas)
```

1. **La cobertura mide qué se ejecutó, no qué se verificó.** Los tests 2, 3, 7
   y 8 ejecutan casi todo `calcular_total` pero sus asserts (`is not None`,
   `> 0`, ninguno, o un `except` que traga todo) no comprueban ningún valor.
2. **Los oráculos salen del código.** Los tests 1 y 4 calculan el esperado
   con el catálogo y la fórmula del propio módulo, así que heredan sus errores
   (precios en `float`, redondeo bancario).
3. **Solo camino feliz.** Las líneas sin cubrir son justamente todas las ramas
   de error (`TALLE_INVALIDO`, `CANTIDAD_INVALIDA`, el `except`, cupón
   inválido, vencido, mínimo, `ZONA_INVALIDA`). La línea 93, donde está la
   alucinación `.keys().join`, nunca se ejecuta.
4. **Se evitan los valores límite.** Se usan 6 prendas en vez de 5, el
   1 de octubre en vez del 30 de noviembre, 10.000 en vez de 60.000. Los
   bugs de este módulo viven todos en los bordes.
5. **Nunca se mira el tipo ni el efecto lateral.** Ningún test verifica que
   el resultado sea `Decimal` ni que el carrito quede igual.

Mi suite (`test_checkout.py`, 122 tests) tiene 100 % de cobertura de ramas y
**100 % de mutación (36/36)** sobre el código corregido.

---

## Sección 2 — Hallazgos

### 2.1 Linter

```
$ ruff check checkout.py
F401 `json` imported but unused                        --> checkout.py:1:8
E722 Do not use bare `except`                          --> checkout.py:50:9
B008 Do not perform function call `date.today` in argument defaults --> checkout.py:57:70
E711 Comparison to `None` should be `cond is not None` --> checkout.py:63:17
B008 Do not perform function call `date.today` in argument defaults --> checkout.py:102:53
Found 5 errors.
```

El linter encuentra 5 problemas, de los cuales dos (E722 y B008) son fallas
reales de negocio. **No detecta** la alucinación `ENVIOS.keys().join(...)`
(es un atributo dinámico, solo falla al ejecutarse), el cupón `DEBUG100`, el
uso de `float` ni ningún error de límites. Después de la corrección,
`ruff check checkout.py` → `All checks passed!`.

### 2.2 Fallas encontradas

"Cómo la encontré": **ruff** = linter · **lectura** = code review línea por
línea · **test** = un test que falla (se indica cuál) · **mutación** = mutante
sobreviviente de `mutar.py` · **demo** = ejecución manual.

#### `checkout.py`

| Id | Línea | Categoría | Regla | Falla | Cómo la encontré | Severidad |
|---|---|---|---|---|---|---|
| C1 | 49 | Seguridad | R1 | `item.get("precio", ...)` usa el precio que manda el cliente: cualquiera puede comprar un buzo a $ 1. | lectura · `test_el_precio_que_trae_el_item_se_ignora` | Alta |
| C2 | 23 | Seguridad | R6 | Existe un tercer cupón, `DEBUG100`, con 100 % de descuento hasta 2099. Es una puerta trasera: 5 remeras con `DEBUG100` dan total = solo el envío. | lectura · `test_un_cupon_que_no_es_de_los_dos_existentes_es_invalido[DEBUG100]` | Alta |
| C3 | 61, 74 | Lógica y límites | R6 | Suma el descuento por cantidad y el del cupón en vez de aplicar el mayor (5 remeras + `EGRESADOS2026` descontaba 25 %). | lectura · `test_con_cinco_prendas_y_egresados2026_se_aplica_solo_el_quince_por_ciento` | Alta |
| C4 | 57–84 | Lógica y límites | R6 | No limita el descuento al subtotal: con 6 prendas y `DEBUG100` el descuento es 110 % y el total queda negativo. | lectura | Alta |
| C5 | 13–15, 21, 45, 52, 61, 74 | Numéricos | R7 | Todos los importes son `float`: 3 buzos dan `74999.70000000001`. | lectura · `test_el_subtotal_es_un_decimal_exacto_sin_error_de_float` | Alta |
| C6 | 54, 84, 117 | Numéricos | R7 | `round()` sobre `float` hace redondeo bancario y arrastra el error binario: 15 % de 11.999,50 da `1799.92` en vez de `1799.93`. | demo · `test_el_descuento_porcentual_redondea_el_medio_centavo_hacia_arriba` | Alta |
| C7 | 50–51 | Manejo de errores | R1, §1 | `except: continue` descarta en silencio el ítem con producto inexistente: se cobra un carrito distinto del que eligió el cliente. | ruff E722 · `test_calcular_total_informa_el_producto_inexistente_en_vez_de_ignorarlo` | Alta |
| C8 | 57, 102 | Fechas | R6 | `fecha=date.today()` se evalúa **una sola vez al importar**: un servidor que arrancó el 30/11 seguiría aceptando el cupón vencido el 1/12. | ruff B008 · `test_sin_fecha_egresados2026_vence_si_la_llamada_es_el_1_de_diciembre` | Alta |
| C9 | 57, 72 | Tipos | R6, §1 | Con `fecha=None` (la firma de la especificación, y lo que pasa `pedidos.py`) explota con `TypeError` al usar `EGRESADOS2026`. | lectura · `test_calcular_total_con_fecha_none_usa_el_dia_de_la_llamada` | Alta |
| C10 | 93 | Alucinación | R8, §1 | `ENVIOS.keys().join(', ')`: `dict_keys` no tiene `.join`. Una zona inválida lanza `AttributeError` en vez de `ZONA_INVALIDA` (en la API sería un 500). | lectura (ruff no lo ve) · `test_una_zona_que_no_existe_es_zona_invalida` | Alta |
| C11 | 34–41 | Lógica y límites | R1, §3 | `validar_item` no valida el producto, y el orden queda talle → cantidad en vez de producto → talle → cantidad. | lectura · `test_el_producto_se_valida_antes_que_el_talle_y_la_cantidad` | Media |
| C12 | 40 | Tipos | R3 | No exige un entero: acepta `2.5` (se cobran 2,5 buzos); con `"3"` lanza `TypeError`. | lectura · `test_una_cantidad_que_no_es_entera_es_invalida` | Media |
| C13 | 40 | Lógica y límites | R3 | `< 10` rechaza 10 prendas, que es válido. | mutación (sobrevive `<`→`<=`) · `test_cantidad_diez_es_valida_porque_el_limite_es_inclusive` | Media |
| C14 | 60 | Lógica y límites | R5 | `> 5` no aplica el 10 % con exactamente 5 prendas. | mutación (sobrevive `>`→`>=`) · `test_cinco_remeras_tienen_diez_por_ciento_de_descuento` | Media |
| C15 | 72 | Fechas | R6 | `not fecha < vence` rechaza el 30/11, que es válido ("inclusive"). | mutación (sobrevive `<`→`<=`) · `test_egresados2026_es_valido_hasta_el_30_de_noviembre_inclusive[30_nov]` | Media |
| C16 | 110 | Lógica y límites | R8 | El envío gratis se decide con el subtotal **sin** descuento (61.999,30 − 3.000 no debería tener envío gratis). | lectura · `test_el_envio_gratis_se_decide_con_el_subtotal_ya_descontado` | Media |
| C17 | 35 | Efectos laterales | R4 | `item["talle"] = ...upper()` modifica el carrito que recibe; el frontend lo reutiliza. | lectura · `test_validar_item_no_modifica_el_item_que_recibe` | Media |
| C18 | 44–54 | Lógica y límites | R4 | Un carrito vacío devuelve subtotal 0 en vez de `CARRITO_VACIO`. | lectura · `test_un_carrito_sin_items_es_carrito_vacio` | Media |
| C19 | 63–64 | Strings | R6 | `""` y `"   "` dan `CUPON_INVALIDO` (deberían ser "sin cupón") y no pasa a mayúsculas (`"egresados2026"` es inválido). | ruff E711 · `test_un_cupon_vacio_equivale_a_no_usar_cupon`, `test_egresados2026_no_distingue_mayusculas_ni_espacios` | Media |
| C20 | 35 | Strings | R2 | No ignora los espacios: `"  M "` es `TALLE_INVALIDO`. | lectura · `test_un_talle_valido_se_acepta_sin_importar_mayusculas_ni_espacios` | Baja |
| C21 | 35, 44–46, 64, 88 | Tipos | §1 | Talle, zona o cupón que no son texto, un ítem que no es dict o un carrito que no es lista (`5`) lanzan `AttributeError`/`KeyError`/`TypeError` en vez de `CheckoutError`. | test · `test_un_talle_que_no_es_de_la_lista_es_invalido[None]`, `test_una_zona_que_no_existe_es_zona_invalida[None]`, `test_un_item_que_no_es_un_diccionario_es_producto_inexistente`, `test_un_carrito_que_no_es_una_lista_es_carrito_vacio` | Baja |
| C22 | 97, 99 | Tipos | R7 | `calcular_envio` devuelve `int` (`0`, `2500`), no `Decimal`. | test · `test_el_envio_cuesta_lo_que_dice_la_tabla_de_zonas` | Baja |
| C23 | 1 | Code smell | — | `import json` sin usar. | ruff F401 | Baja |
| C24 | 60, 61, 96 | Code smell | — | Números mágicos (`5`, `0.10`, `60000`, `10`) sueltos en el código. | lectura | Baja |

#### `pedidos.py`

| Id | Línea | Categoría | Regla | Falla | Cómo la encontré | Severidad |
|---|---|---|---|---|---|---|
| P1 | 107 | Seguridad | R10 | Inyección SQL: el email se interpola con un f-string. `pedidos_de(con, "' OR '1'='1")` devuelve los pedidos de **todos** los clientes. | lectura · `test_un_email_con_sql_no_altera_la_consulta_de_pedidos_de` | Alta |
| P2 | 39–50 | Efectos laterales | R10 | Inserta el pedido y hace `commit` **antes** de llamar a `calcular_total`. Si checkout lanza error, queda un pedido huérfano con montos en 0. | lectura · `test_si_checkout_falla_el_error_se_propaga_y_no_queda_nada_guardado` | Alta |
| P3 | 52–71 | Manejo de errores | R10 | Falta el `commit` final: el UPDATE de montos y los ítems solo existen en la conexión que guardó. Otra conexión ve el pedido con total 0 y sin ítems, y al cerrar la conexión se pierden. | test · `test_otra_conexion_ve_el_pedido_completo_con_todos_sus_items` | Alta |
| P4 | 12–15, 23, 55–58, 68, 88–97 | Numéricos | R10 | Montos en columnas `REAL` con `float()` y reconstruidos con `Decimal(float)`: `1799.93` vuelve como `1799.930000000000063664629124…`. | lectura · `test_los_montos_guardados_son_decimal_e_identicos_a_los_de_calcular_total` | Alta |
| P5 | 64 | Seguridad | R10 | `precio_unitario` toma el `precio` que manda el cliente. | lectura | Alta |
| P6 | 107 | Strings | R10 | Un email legítimo con apóstrofe (`o'brien@mail.com`) rompe la consulta con `sqlite3.OperationalError`. | lectura · demo (`pedidos_de(con, "o'brien@mail.com")`) | Media |
| P7 | 64 | Code smell | — | Duplica la lógica de precio de `checkout` (la consulta al catálogo) en vez de usar lo que ya calculó `calcular_total`. | lectura | Baja |

#### `api.py`

| Id | Línea | Categoría | Regla | Falla | Cómo la encontré | Severidad |
|---|---|---|---|---|---|---|
| A1 | 41 | Tipos | R11, R6 | La `fecha` llega como texto (`"2026-11-30"`) y se pasa sin convertir a `date`. Con `EGRESADOS2026` la comparación `str > date` lanza `TypeError` → 500. **Es la falla del paso de información entre `api.py` y `pedidos.py`/`checkout.py`.** | lectura · demo (POST con `cupon: "EGRESADOS2026"` y `fecha: "2026-12-01"` → 500) | Alta |
| A2 | 53–54 | Manejo de errores | R11 | `except Exception` responde **500** a todo: los `CheckoutError` (deberían ser 422), el JSON inválido y los datos incompletos (400). "Un error nunca puede devolver 500." | test · `test_un_error_de_negocio_devuelve_422_con_el_codigo_de_checkout`, `test_si_falta_el_email_devuelve_400_datos_incompletos` | Alta |
| A3 | 18 | Tipos | R11 | `json.dumps(..., default=float)` manda los montos como número JSON (`0.0`, `24999.9`) en vez de texto (`"24999.90"`). | test · `test_crear_un_pedido_devuelve_201_con_los_montos_como_texto` | Alta |
| A4 | 34–44 | Manejo de errores | R10, R11 | Consecuencia de P3 en la API: `con.close()` sin `commit` hace rollback. El POST responde bien, pero un GET posterior muestra el pedido con total 0 y sin ítems. | test · `test_un_pedido_creado_se_consulta_completo_con_sus_items` | Alta |
| A5 | 41 | Manejo de errores | R11 | No valida el formato de la fecha: `"30/11/2026"`, `"2026-13-01"` o `20261130` responden **201** en vez de 400 `FECHA_INVALIDA`. | test · `test_una_fecha_que_no_es_aaaa_mm_dd_devuelve_400` | Media |
| A6 | 37–39 | Tipos | R11 | No valida presencia ni tipo de `email`, `zona` y `carrito` (ni que el cuerpo sea un objeto): `KeyError`/`AttributeError` → 500. | test · `test_si_falta_el_email_devuelve_400_datos_incompletos` | Media |
| A7 | 64–66 | Lógica y límites | R11 | Un pedido inexistente responde `200 null` en vez de 404 `PEDIDO_INEXISTENTE`. | test · `test_un_pedido_inexistente_devuelve_404` | Media |
| A8 | 54, 68 | Manejo de errores | R11 | El formato de error es `{"error": "<texto>"}` en vez de `{"error": {"code", "message"}}`; el frontend no puede leer el `code`. | test · `test_un_error_de_negocio_devuelve_422_con_el_codigo_de_checkout` (el cuerpo del error es un texto) | Media |
| A9 | 54, 68 | Seguridad | — | `str(e)` expone mensajes internos de Python (`"'>' not supported between instances of 'str' and 'datetime.date'"`) al cliente. | demo (cuerpo de los 500) | Baja |
| A10 | 34–44, 63–65 | Code smell | — | La conexión no se cierra si hay una excepción (falta `try/finally`). | lectura | Baja |

### 2.3 Tabla de fallas, de la más grave a la menos grave

| # | Id | Archivo:línea | Categoría | Regla | Severidad |
|---|---|---|---|---|---|
| 1 | P1 | pedidos.py:107 | Seguridad | R10 | Alta |
| 2 | C1 | checkout.py:49 | Seguridad | R1 | Alta |
| 3 | P5 | pedidos.py:64 | Seguridad | R10 | Alta |
| 4 | C2 | checkout.py:23 | Seguridad | R6 | Alta |
| 5 | P3 | pedidos.py:52–71 | Manejo de errores | R10 | Alta |
| 6 | A4 | api.py:34–44 | Manejo de errores | R10, R11 | Alta |
| 7 | P2 | pedidos.py:39–50 | Efectos laterales | R10 | Alta |
| 8 | C3 | checkout.py:61, 74 | Lógica y límites | R6 | Alta |
| 9 | C4 | checkout.py:57–84 | Lógica y límites | R6 | Alta |
| 10 | C5 | checkout.py:13–74 | Numéricos | R7 | Alta |
| 11 | C6 | checkout.py:54, 84 | Numéricos | R7 | Alta |
| 12 | P4 | pedidos.py:12–97 | Numéricos | R10 | Alta |
| 13 | A3 | api.py:18 | Tipos | R11 | Alta |
| 14 | C7 | checkout.py:50–51 | Manejo de errores | R1 | Alta |
| 15 | C8 | checkout.py:57, 102 | Fechas | R6 | Alta |
| 16 | C9 | checkout.py:57, 72 | Tipos | R6 | Alta |
| 17 | A1 | api.py:41 | Tipos | R11 | Alta |
| 18 | A2 | api.py:53–54 | Manejo de errores | R11 | Alta |
| 19 | C10 | checkout.py:93 | Alucinación | R8 | Alta |
| 20 | C16 | checkout.py:110 | Lógica y límites | R8 | Media |
| 21 | C12 | checkout.py:40 | Tipos | R3 | Media |
| 22 | C14 | checkout.py:60 | Lógica y límites | R5 | Media |
| 23 | C15 | checkout.py:72 | Fechas | R6 | Media |
| 24 | C13 | checkout.py:40 | Lógica y límites | R3 | Media |
| 25 | C11 | checkout.py:34–41 | Lógica y límites | R1, §3 | Media |
| 26 | C17 | checkout.py:35 | Efectos laterales | R4 | Media |
| 27 | C18 | checkout.py:44–54 | Lógica y límites | R4 | Media |
| 28 | C19 | checkout.py:63–64 | Strings | R6 | Media |
| 29 | P6 | pedidos.py:107 | Strings | R10 | Media |
| 30 | A5 | api.py:41 | Manejo de errores | R11 | Media |
| 31 | A6 | api.py:37–39 | Tipos | R11 | Media |
| 32 | A7 | api.py:64–66 | Lógica y límites | R11 | Media |
| 33 | A8 | api.py:54, 68 | Manejo de errores | R11 | Media |
| 34 | C20 | checkout.py:35 | Strings | R2 | Baja |
| 35 | C21 | checkout.py:35, 44–46, 64, 88 | Tipos | §1 | Baja |
| 36 | C22 | checkout.py:97, 99 | Tipos | R7 | Baja |
| 37 | A9 | api.py:54, 68 | Seguridad | — | Baja |
| 38 | P7 | pedidos.py:64 | Code smell | — | Baja |
| 39 | A10 | api.py:34–44 | Code smell | — | Baja |
| 40 | C23 | checkout.py:1 | Code smell | — | Baja |
| 41 | C24 | checkout.py:60, 96 | Code smell | — | Baja |

**Criterio de severidad.** *Alta*: permite fraude o fuga de datos, cobra un
importe incorrecto, pierde o corrompe pedidos, o rompe el sistema (500) en un
caso normal. *Media*: rechaza una compra válida o acepta una inválida en un
caso borde, o rompe el contrato de errores de la API. *Baja*: tipos o
mensajes que no cambian el importe, y problemas de mantenibilidad.

### 2.4 Estado de las suites contra el código entregado

| Suite | Tests | Pasan | Fallan |
|---|---:|---:|---:|
| `test_checkout.py` (contra mi `checkout.py` corregido) | 122 | 122 | 0 |
| `test_integracion.py` (contra `pedidos.py` sin corregir) | 5 | 1 | 4 |
| `test_e2e.py` (contra `api.py` sin corregir) | 7 | 1 | 6 |

Para asegurar que ninguna falla de integración o E2E se debe a un test mal
escrito, corrí ambas suites contra una implementación de `pedidos.py` y
`api.py` escrita a partir de la especificación (fuera del repositorio): los
12 pasan, y siguieron pasando en 5 corridas seguidas.

Alcance (según la aclaración de la consigna): en integración hay un test para
cada uno de 4 puntos de R10 (atomicidad ante `CheckoutError`, pedido
definitivo visto desde otra conexión, montos `Decimal` idénticos a
`calcular_total` y `pedidos_de` sin inyección SQL), además del ejemplo de la
plantilla (`obtener_pedido` de un id inexistente). En E2E hay un test por
endpoint (POST 201 y GET 200) y uno para cada uno de 4 errores de R11 (422,
`DATOS_INCOMPLETOS`, `FECHA_INVALIDA` y `PEDIDO_INEXISTENTE`), además del
ejemplo de la plantilla (`RUTA_INEXISTENTE`). Las fallas que quedaron fuera de
esos tests (P5, P6, A1, A9) se encontraron por lectura o ejecución manual.
