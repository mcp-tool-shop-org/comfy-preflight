<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.md">English</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/comfy-preflight/readme.png" alt="comfy-preflight" width="600">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/comfy-preflight/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/comfy-preflight/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/comfy-preflight/"><img src="https://img.shields.io/pypi/v/comfy-preflight?color=3775a9&label=pypi" alt="PyPI"></a>
  <a href="https://www.npmjs.com/package/@mcptoolshop/comfy-preflight"><img src="https://img.shields.io/npm/v/@mcptoolshop/comfy-preflight?color=cb3837&label=npm" alt="npm"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/comfy-preflight/"><img src="https://img.shields.io/badge/landing%20page-live-2ea043" alt="Landing page"></a>
</p>

<p align="center">
  <strong>A gate that runs on a ComfyUI workflow graph in the seconds before it is submitted,</strong><br>
  and halts a submission that would spend credits producing a known-wrong result.<br>
  It does not submit. It does not fix your graph.
</p>

---

## El espacio en el que se encuentra

> **Un PASS de `dry_run` de Comfy Cloud NO prueba la integridad del enlace.**
> Una carga útil reescrita manualmente con un enlace de nodo autorreferencial — `VAEDecode.samples = ["14", 0]`,
> el nodo apuntando a sí mismo — devolvió `status: validated`.

La respuesta del validador del proveedor es: *¿este gráfico está lo suficientemente bien formado para ejecutarse?* No responde a la pregunta de si
*¿este es el gráfico que pretendías?* Cada comprobación aquí se realiza en ese espacio, y cada una fue pagada por
una ejecución que superó `dry_run`.

**El envío es el acto irreversible sin una verdadera opción de deshacerlo, y un precontrol es un mecanismo compensatorio que se ejecuta
ANTES en lugar de después.** Se factura un trabajo en la nube completado; el único mecanismo compensatorio posterior es
*cancelarlo si aún está en cola, de lo contrario ninguno.* Ese es todo el argumento para este paquete.

## Instalar

```bash
npx @mcptoolshop/comfy-preflight check graph.json   # no Python needed
pip install comfy-preflight                          # for the in-process gate
pip install "comfy-preflight[mcp]"                   # + the MCP stdio server
```

El lanzador npx descarga un archivo binario del repositorio GitHub Release y **verifica su SHA256**
en comparación con las sumas de comprobación en ese mismo lanzamiento antes de ejecutarlo. Python ≥ 3.11; archivos binarios para
linux-x64 y win-x64 (la instalación de macOS se realiza a través de `pip`).

## Úsalo

**La puerta de producción: en proceso, en la ruta de envío:**

```python
from comfy_preflight import preflight

# Inside the function that submits. Not in a shell step before it.
preflight(graph, register, input_dims=(width, height))   # raises PreflightHalt
submit(graph)                                            # only reached if nothing raised
```

**La puerta de desarrollo:**

```bash
comfy-preflight check graph.json \
  --input-dims 1072x1024 --register subject.json --saved sidecar.json --json
```

| salir | significado |
|---|---|
| `0` | nada se detuvo — PASS, ADVISORY o NOT_APPLICABLE, **cada uno con un nombre en la salida** |
| `1` | DETENER |
| `2` | **no se examinó nada:** argumentos incorrectos, archivo ilegible o un error interno |

Las salidas ADVISORY `0` a propósito: un estado distinto de cero detiene una cadena `&&`, lo que convertiría una advertencia
en una parada en cada shell que la ejecute.

## Lo que comprueba

| # | comprobar | se detiene al encontrar |
|---|---|---|
| 1 | **Link topology** | una entrada de nodo que lee su propio nodo; un enlace a un ID de nodo que no está en el gráfico |
| 2 | **El escaneo invertido del registro** | un registro declarado que no coincide con la construcción del gráfico — **en ambas direcciones** |
| 4 | **Saved-is-submitted** | el archivo adjunto guardado y la carga útil enviada difieren **como gráficos analizados** |
| 5 | **Generator-legal frame** | una dimensión que el VAE del marco efectivo no puede decodificar |
| 8 | **Declared envelope** | **nada: nunca se detiene.** Fuera de banda es una ADVERTENCIA |

Tres comprobaciones del diseño original **no están implementadas**, y tienen un nombre en lugar de simplemente faltar: acuerdo entre receta y perfil (no existe ninguna configuración de sujeto-perfil), estimación antes del envío
(lado del transporte: no hay operando estructural del gráfico) y reproducción del ancla (necesita el
*constructor*; el corpus contiene salidas, no los scripts que las crearon).

### Comprobación 2: la que nombra el método

Cuando el registro de un sujeto declara **que no tiene adaptador de estilo**, la afirmación que se está haciendo NO es "el
peso es 0.0". Es que **no existe ningún nodo cargador ni ninguna referencia a una tarjeta adaptadora en ningún lugar del
gráfico**.

> *Un peso de 0.0 no es un peso cero en una tarjeta cargada; es que no hay ninguna tarjeta.*

**Y afirma la imagen especular.** Un peso positivo decidido con **ningún nodo cargador** es
*silenciosamente inerte*: la ejecución se completa, cuesta dinero y produce una salida del modelo base mientras que cada línea de registro indica que se solicitó el adaptador. Esa dirección no produce ninguna señal que un humano pueda notar, lo cual es exactamente por lo que una puerta justifica su lugar frente a una persona que lo revisa.

### Comprobación 5: el marco efectivo, no el declarado

`1066 / 8 = 133.25` se codifica en 133 columnas latentes y se decodifica en **1064**, desplazando cada salida
2 píxeles de su imagen de control y rompiendo cada emparejamiento posterior.

**El defecto ocurrió aguas arriba del gráfico.** El valor de 1066 se derivó correctamente de una malla, la
imagen se renderizó a ese ancho y se cargó, y el gráfico nunca lo declaró, por lo que una comprobación que leyera los literales del gráfico no podría haber detectado el incidente que la motiva. El operando es el
marco que realmente producirá la ejecución, que en un gráfico img2img es las dimensiones de la imagen de entrada.

÷8 se detiene. ÷16 advierte. Un límite y una preferencia, no dos límites.

### Comprobación 8: advertencia y honesta sobre lo que no puede decir

Para cada punto de control que carga el gráfico, se comparan los parámetros con una tabla de **envolventes citadas**.
Cada entrada lleva su banda, la URL de origen, la fecha de recuperación y una cita de las propias palabras de la tarjeta, y el constructor se niega a construir una entrada que no lo haga.

La entrada del primer día es `Qwen-Image-InstantX-ControlNet-Union`. Contiene la
banda `controlnet_conditioning_scale` que documenta su tarjeta, y una **ausencia declarada** para la eliminación de ruido,
porque esa tarjeta no publica ningún rango de eliminación de ruido: se verifica con la tarjeta activa en lugar de recuperarla. Por lo tanto, una ejecución en un gráfico en `denoise=0.92` informa el valor de 0.92, nombra el parámetro y dice
claramente que no puede juzgarlo y por qué.

Informar del valor que no puede juzgar es la mitad honesta del hallazgo. Inventar una banda para juzgarlo sería la mitad deshonesta.

## El contrato de adopción

**Llamémoslo en proceso en la ruta de envío. No hay ninguna opción de omisión.**

*La comprobación se realiza dentro de la herramienta que realiza el paso irreversible.* Un precontrol en una cadena de shell antes del envío es un **transporte, no una protección**: en el incidente que produjo esta regla, se confirmaron 47.020 texeles después de que ya se hubiera activado una puerta, porque una cadena de PowerShell pasó
por un código de salida fallido. Nadie decidió continuar; la construcción era incapaz de detenerse.

**La CLI y el servidor MCP son ambos transportes, no puertas.** Leer una DETENCIÓN de cualquiera de ellos y luego enviar desde otro lugar es la misma cadena con una interfaz más agradable.

Ninguna función aquí toma un parámetro `skip`, `force`, `warn_only` o `enabled`, y las pruebas leen cada
firma en lugar de confiar en la documentación. **Cada puerta `raise`; ninguna es una simple `assert`** —
`python -O` elimina `assert` silenciosamente, y CI ejecuta toda la suite bajo `-O` y
`PYTHONOPTIMIZE=1` para demostrar que las puertas sobreviven a ello.

## A través de MCP

```bash
python -m comfy_preflight.mcp_server     # stdio
npx @mcptoolshop/comfy-preflight mcp     # same server, no Python required
```

Una herramienta, `preflight`, devuelve el mismo resultado estructurado que devuelve la biblioteca; una prueba confirma la identidad de los bytes. Una instrucción HALT es una llamada *exitosa* que devuelve `{"verdict": "halt", ...}`, porque informar de ella como un error de protocolo implicaría descartar la estructura que necesita el llamador.

## Seguridad

No se realizan llamadas a la red, no se utilizan credenciales, no se recopilan datos de telemetría y no se escribe nada en ninguna parte. Lee un grafo y un perfil, y devuelve un resultado. Modelo completo de amenazas: datos accedidos, datos *no* accedidos y los permisos necesarios; todo esto se encuentra en [SECURITY.md](SECURITY.md).

## Documentación

📖 **[El manual](https://mcp-tool-shop-org.github.io/comfy-preflight/handbook/)** — cómo empezar, descripción detallada de cada comprobación, el contrato de adopción y la tabla de parámetros.

## Licencia

MIT; consulte [LICENSE](LICENSE).

<p align="center">
  Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
</p>
