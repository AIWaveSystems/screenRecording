# Licencia MIT — traducción informativa al español

> **Aviso importante.** Esta traducción se ofrece **solo para facilitar la
> comprensión**. No tiene valor legal. El único texto vinculante es la versión en
> inglés del archivo [`LICENSE`](LICENSE). Ante cualquier discrepancia entre
> ambos textos, prevalece el inglés.

---

Copyright (c) 2026 Ilesandres

Por la presente se concede permiso, libre de cargo, a cualquier persona que
obtenga una copia de este software y de los archivos de documentación asociados
(el "Software"), para utilizar el Software sin restricción, incluyendo sin
limitación los derechos a usar, copiar, modificar, fusionar, publicar,
distribuir, sublicenciar y/o vender copias del Software, y a permitir a las
personas a las que se les proporcione el Software a hacer lo mismo, sujeto a las
siguientes condiciones:

El aviso de copyright anterior y este aviso de permiso deberán incluirse en
todas las copias o partes sustanciales del Software.

EL SOFTWARE SE PROPORCIONA "TAL CUAL", SIN GARANTÍA DE NINGÚN TIPO, EXPRESA O
IMPLÍCITA, INCLUYENDO PERO NO LIMITÁNDOSE A LAS GARANTÍAS DE COMERCIABILIDAD,
IDONEIDAD PARA UN PROPÓSITO PARTICULAR Y NO INFRACCIÓN. EN NINGÚN CASO LOS
AUTORES O TITULARES DEL COPYRIGHT SERÁN RESPONSABLES DE NINGUNA RECLAMACIÓN,
DAÑO U OTRA RESPONSABILIDAD, YA SEA EN UNA ACCIÓN CONTRACTUAL, EXTRACONTRACTUAL
O DE CUALQUIER OTRO TIPO, DERIVADA DE, RELACIONADA CON O EN CONEXIÓN CON EL
SOFTWARE O SU USO U OTRAS OPERACIONES CON EL SOFTWARE.

---

## Qué cubre esta licencia

La licencia MIT ampara **el código fuente de este repositorio**: lo que hay bajo
`src/`, `main.py`, las pruebas y la documentación.

**No ampara el ejecutable distribuido.** El binario de `dist/` incorpora
componentes de terceros con licencias copyleft (PyQt5 y FFmpeg, ambos GPL v3),
así que el programa ya compilado se distribuye bajo GPL v3. Los detalles están
en [`NOTICE`](NOTICE) y conviene leerlos antes de redistribuirlo.

## Qué significa esto en la práctica

| Puedes | Debes | No hay |
| --- | --- | --- |
| Usarlo con **fines comerciales**, sin pagar nada | Conservar el aviso de copyright y esta licencia en las copias o partes sustanciales | Garantía de ningún tipo |
| Modificarlo y adaptarlo a lo que necesites | Respetar además las licencias de terceros listadas en [`NOTICE`](NOTICE) | Responsabilidad del autor por daños |
| Redistribuirlo, con o sin cambios | | Obligación de publicar tus modificaciones del código MIT |
| Sublicenciarlo o venderlo | | Soporte garantizado |
| Usarlo en software cerrado y propietario **si sustituyes los componentes GPL** | | |

### La mención al autor

La licencia MIT **ya exige la atribución**: conservar el aviso de copyright es
una condición obligatoria, no una cortesía. Quien redistribuya este software,
lo use comercialmente o lo integre en un producto cerrado, debe mantener el
aviso `Copyright (c) 2026 Ilesandres` accesible: en un archivo de licencias, en
una pantalla de "Acerca de", en la documentación, o donde corresponda según el
formato del producto.

Si además quieres citarlo, esta forma es suficiente:

```
Construido sobre Screen Recorder
https://github.com/AIWaveSystems/screenRecording
Copyright (c) 2026 Ilesandres — Licencia MIT
```

### Bajo tu propia responsabilidad

Los dos párrafos en mayúsculas son la parte que más importa. El software se
entrega **tal cual**, sin garantías, y el autor **no responde** por ningún daño
derivado de su uso.

> **Especialmente relevante en un grabador de pantalla**
>
> Esta aplicación captura **todo lo que se ve en el monitor elegido**, el audio
> del sistema y el micrófono. Eso incluye, sin distinguirlo, contraseñas
> visibles, mensajes privados, datos de clientes o cualquier información
> sensible que aparezca en pantalla mientras graba.
>
> Grabar a otras personas —reuniones, llamadas, clases— puede requerir su
> consentimiento según la legislación de cada país. Quien use la aplicación es
> responsable de obtenerlo y de custodiar los archivos resultantes.
>
> El proyecto está en fase beta: puede fallar a mitad de una grabación y perder
> material. No lo uses como única fuente para algo que no puedas repetir.

---

## Componentes de terceros

Este proyecto usa bibliotecas y binarios con sus propias licencias, que debes
respetar además de la MIT. Están detallados en [`NOTICE`](NOTICE), incluidos los
que imponen condiciones más estrictas que esta licencia.
