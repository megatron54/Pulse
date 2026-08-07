# Investigación: migrar Pulse a app nativa de escritorio (Épica K)

> Investigación real (no implementación) pedida explícitamente por el usuario
> tras sentir que arrancar Pulse hoy (scripts + Docker + backend + frontend +
> HTML) no da el UX que quiere para un "producto de verdad". Mismo criterio
> que el resto de decisiones de arquitectura de este proyecto: comparar
> candidatos reales con evidencia, no elegir a ciegas.

## Resumen ejecutivo

**Recomendación preliminar: Tauri v2, con el backend FastAPI empaquetado como
"sidecar" (binario compilado con PyInstaller) y SQLite en vez de Postgres.**
El frontend Next.js actual está en una forma sorprendentemente favorable para
esto (ver hallazgo 3) - la migración es más barata de lo que parecía a priori.
No se recomienda Electron ni Capacitor para este caso. Esto NO es una
decisión final - es la recomendación mejor fundamentada con la evidencia
reunida hasta ahora; queda pendiente una prueba de concepto real antes de
comprometerse (ver "Siguientes pasos").

## 1. Tauri vs. Electron vs. Capacitor — comparación real

| | Tauri v2 | Electron | Capacitor |
|---|---|---|---|
| Motor de render | WebView nativo del SO (WebView2 en Windows, WebKit en macOS, WebKitGTK en Linux) | Chromium empaquetado completo | Pensado para móvil; su soporte de escritorio existe pero es secundario/menos maduro |
| Tamaño típico | Un dígito de MB (sin contar el sidecar de Python) | 100MB+ (incluye Chromium completo) | Variable, no es su caso de uso principal |
| Uso de memoria | Bajo (no hay una instancia de Chromium por app) | Alto (cada app corre su propio Chromium) | N/A para escritorio |
| Lenguaje del núcleo nativo | Rust | Node.js/JavaScript | JavaScript (wrapper nativo por plataforma) |
| Track record en producción | Creciente pero más joven | Muy maduro (VS Code, Slack) | Sólido en móvil, débil en escritorio |
| Soporte de "sidecar" (proceso hijo, ej. backend Python) | Sí, de primera clase (`externalBin` en `tauri.conf.json`), con ejemplos reales funcionando | Sí, vía `child_process` de Node, patrón también común | No es su modelo de uso típico |

**Descartado: Capacitor para escritorio.** Es la elección correcta para la futura app Android (Épica 14, ya en el roadmap), pero su soporte de escritorio es secundario y no tiene el mismo ecosistema de "sidecar" ni la ventaja de tamaño que sí tiene Tauri. Reutilizar Capacitor "porque ya se mencionó para Android" sería forzar una herramienta a un caso de uso para el que no está pensada.

**Descartado: Electron**, salvo que la inconsistencia de renderizado entre plataformas de Tauri (WebView nativo distinto por SO) se demuestre un problema real durante la prueba de concepto. Dado que Pulse hoy solo se usa en Windows (confirmado en esta sesión: el usuario no necesita acceso móvil/remoto todavía), el argumento de "renderizado 100% idéntico en todo SO" de Electron pesa menos que su coste de tamaño/memoria.

## 2. Qué pasa con el backend (FastAPI + Capa 1 en Python) — la decisión más importante

**Confirmado con evidencia real, no solo teoría**: el patrón "Tauri + Next.js + FastAPI como sidecar" ya existe y funciona en producción de terceros:
- `dieharders/example-tauri-v2-python-server-sidecar` (122 estrellas, Tauri v2, activamente mantenido): Next.js como frontend, FastAPI compilado con **PyInstaller** a un único ejecutable, registrado como `externalBin` en `tauri.conf.json`. Tauri arranca/para el proceso hijo, y el frontend le habla por HTTP normal (`localhost:PUERTO`).
- Relato real de migración (`dev.to/kination`, enero 2026): migró de Electron a Tauri v2 exactamente por el mismo motivo (peso de Chromium), manteniendo FastAPI + PyInstaller como sidecar, y un motor de IA local (Ollama) como segundo sidecar. Confirma retos reales a anticipar: las políticas de seguridad del WebView bloquean `fetch` normal a `localhost` por defecto (solución: plugin oficial `@tauri-apps/plugin-http`), hace falta un "health check polling" mientras el sidecar arranca (para no mostrar la UI antes de que el backend esté listo - patrón ya conocido en este proyecto, ver `docker-compose.yml`/healthchecks), y en macOS los binarios descargados quedan en cuarentena por Gatekeeper (a resolver si algún día se soporta macOS).

**Conclusión: NO hace falta reescribir la Capa 1 (motor de reglas Python, ~100% cobertura de tests) a otro lenguaje.** Esta era la preocupación de mayor coste identificada antes de investigar, y la evidencia real descarta que sea necesario - el patrón sidecar preserva el backend Python tal cual, solo cambia cómo se empaqueta y arranca.

## 3. Qué pasa con el frontend Next.js — hallazgo favorable confirmado contra el código real

Tauri exige explícitamente **exportación estática** de Next.js (`output: 'export'` en `next.config`) - "Tauri doesn't support server-based solutions" (documentación oficial de Tauri v2, `v2.tauri.app/start/frontend/nextjs`). Esto normalmente es una restricción real y dolorosa para apps Next.js que usan Route Handlers (`app/api/`), Server Actions (`"use server"`), middleware, o rutas dinámicas con datos en build time.

**Se verificó contra el código real de Pulse en esta sesión** (no asumido):
- `grep` de `src/app/api` → **no existe ningún Route Handler**.
- `grep` de `"use server"` → **cero coincidencias**, no hay Server Actions.
- `src/middleware.ts` → **no existe**.
- Ninguna carpeta de ruta con `[parametro]` → **no hay rutas dinámicas**.

Es decir: **Pulse ya es, de facto, una SPA cliente pura** - todas las páginas son `"use client"` que llaman directamente a la API de FastAPI vía `lib/api.ts`, exactamente el patrón que Tauri necesita sin cambios estructurales. Los únicos ajustes esperables (no verificados exhaustivamente en esta pasada, a confirmar en la prueba de concepto): `images: { unoptimized: true }` si se usa `next/image` en algún punto, y el `assetPrefix` condicional que documenta la guía oficial de Tauri.

**Esto reduce el riesgo de la migración de frontend de "alto, requiere reescritura" a "bajo, principalmente configuración".**

## 4. Qué pasa con Postgres — SQLite es la opción pragmática, embeber Postgres no lo es

Consenso claro en la comunidad de Tauri (hilo oficial `tauri-apps/discussions#5418`, 2022-2025, respuesta aceptada): **embeber Postgres de verdad dentro de un instalador de escritorio de un solo binario no es viable en la práctica** - las alternativas mencionadas (`pg-embed`, `embedded-postgres`, `postgresql-embedded`) son proyectos de nicho, pensados sobre todo para tests de integración Node/Rust, no para distribuir a usuarios finales no técnicos. La recomendación repetida de la propia comunidad es: **usar SQLite** para este caso de uso (offline, mono-usuario, sin servidor de BD que administrar).

**Para Pulse esto es más barato de lo habitual**: el backend ya usa SQLAlchemy como capa de abstracción, y **la suite de tests YA corre contra SQLite en memoria** (`sqlite:///:memory:`, visto en prácticamente todos los archivos de test de este proyecto) - es decir, la compatibilidad de los modelos con SQLite ya está probada indirectamente en cientos de tests, aunque quedan por confirmar detalles reales de producción (tipos de columna específicos de Postgres si los hubiera, migraciones con Alembic si se usan, comportamiento de columnas JSON). Migrar el `DATABASE_URL` de producción de Postgres a un archivo SQLite local (en el directorio de datos del usuario, ej. `%APPDATA%\Pulse\pulse.db` en Windows) es la ruta de menor fricción, no una reescritura de modelo de datos.

## 5. Diagnóstico de lentitud actual — separar percepción de causa real (ya confirmado en esta sesión, no repetir la investigación)

Ya se confirmó en una sesión anterior de este mismo proyecto: la lentitud de `next dev` en Windows es por el fallback a bindings WASM de Next.js/SWC (bindings nativos rotos en este entorno Windows concreto) - **no** es un problema del proyecto Pulse en sí. El build de producción vía Docker (Linux, SWC nativo) ya es rápido, verificado repetidamente con Playwright en esta sesión.

Esto es importante para no resolver el problema equivocado: si la frustración fuera *solo* velocidad de desarrollo, ya hay una vía barata (no usar `next dev` en Windows, o corregir los bindings nativos). La razón real para una app nativa, según lo que expresó el usuario, es más amplia: **UX de "aplicación de verdad"** (icono, doble clic, sensación nativa, sin depender de abrir Docker/backend/frontend por separado ni de una pestaña de navegador) - un objetivo legítimo que una app Tauri sí resuelve directamente, independientemente de la causa de la lentitud de desarrollo.

## 6. Riesgos y preguntas abiertas (sin resolver todavía, requieren prueba de concepto)

- **No se ha probado nada de esto contra el código real de Pulse todavía** - todo lo anterior es evidencia de patrones ya probados por terceros con un stack equivalente (Next.js + FastAPI), no una prueba de concepto propia. El siguiente paso real sería un spike pequeño y acotado (ej. una sola página de Pulse sirviéndose dentro de un shell de Tauri mínimo con el backend como sidecar) antes de comprometerse a la migración completa.
- **PyInstaller y las dependencias pesadas del backend** (SQLAlchemy, FastAPI, `python-garminconnect`, `google-generativeai`) - no se ha verificado el tamaño/tiempo de arranque resultante del binario compilado, ni si alguna dependencia tiene problemas conocidos de compatibilidad con PyInstaller (algunas librerías con extensiones C o carga dinámica de plugins a veces requieren configuración extra de `--hidden-import`/`--collect-all`).
- **Migración de datos reales**: el usuario ya tiene datos reales en Postgres (perfil, historial de Garmin, hábitos). Migrar a SQLite requiere un script de migración de datos real (no solo de esquema), a diseñar con el mismo cuidado que la migración de volumen Docker ya hecha en esta sesión (Épica 15/scheduler).
- **El scheduler nocturno** (`scheduler/app.py`, hoy un contenedor Docker separado) necesitaría repensarse en el modelo de app nativa: ¿un segundo sidecar? ¿un timer del propio sistema operativo (Task Scheduler de Windows)? Esto también queda pendiente de decidir en la prueba de concepto.
- **Plataformas soportadas**: dado que hoy Pulse es de un solo usuario en Windows, la prueba de concepto puede acotarse a Windows únicamente en una primera fase, sin gastar esfuerzo en macOS/Linux hasta que haga falta.

## 7. Siguientes pasos recomendados (NO ejecutar sin decisión explícita del usuario)

1. Prueba de concepto acotada: un `tauri.conf.json` mínimo sirviendo la exportación estática ya existente de Next.js (`next build` con `output: 'export'`), sin backend todavía - confirmar que la UI carga y navega dentro del WebView de Windows.
2. Compilar el backend actual con PyInstaller como un ejecutable standalone, ejecutarlo manualmente (fuera de Tauri) y confirmar que responde a `/health` igual que hoy en Docker.
3. Conectar ambas piezas: registrar el ejecutable como `externalBin`, arrancar/parar desde Tauri, verificar comunicación HTTP real desde el frontend empaquetado.
4. Solo si los 3 pasos anteriores funcionan, evaluar la migración de Postgres a SQLite y el plan de migración de los datos reales ya existentes.
5. Documentar aquí mismo los resultados reales de la prueba de concepto (tamaños de binario, tiempos de arranque, problemas encontrados) antes de decidir si se convierte en la vía de producción.
