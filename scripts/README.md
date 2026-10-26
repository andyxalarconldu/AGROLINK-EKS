@'
# scripts/ · Scripts de demostración

Dos scripts de PowerShell que se usan en las pruebas del punto 8.

| Script | Para qué |
|---|---|
| `enviar-guias.ps1` | Envía 40 guías seguidas al productor |
| `monitor.ps1` | Llama a `/health` cada 0,5 s y cuenta aciertos y errores |

## Antes de usarlos

Ambos tienen la variable `$URL` con la dirección del LoadBalancer. Es distinta en cada despliegue:
@'
# scripts/ · Scripts de demostración

Dos scripts de PowerShell que se usan en las pruebas del punto 8.

| Script | Para qué |
|---|---|
| `enviar-guias.ps1` | Envía 40 guías seguidas al productor |
| `monitor.ps1` | Llama a `/health` cada 0,5 s y cuenta aciertos y errores |

## Antes de usarlos

Ambos tienen la variable `$URL` con la dirección del LoadBalancer. Es distinta en cada despliegue: