# Infraestructura — Fase 0

## wger (backend base) — ✅ CORRIENDO

Repo oficial clonado en `wger-docker/` (https://github.com/wger-project/docker).

**Entorno usado: compose de producción (raíz de `wger-docker/`)**, no
`dev-postgres` — ese entorno requiere compilar desde el código fuente de
wger (`WGER_CODEPATH`), pensado para contribuir al proyecto wger en sí,
no para usarlo como backend ya construido. En su lugar se usa la imagen
oficial `docker.io/wger/server:latest`.

### Cómo se levantó

```powershell
cd infra\wger-docker
docker compose up -d
```

Primer arranque: descarga de imágenes (wger/server, postgres:15-alpine,
nginx, redis, powersync), migraciones de base de datos, carga de fixtures
(incluye la BD de ejercicios oficial: 2429 registros), collectstatic
(11310 archivos), generación de usuario admin. Tarda varios minutos la
primera vez; arranques posteriores son mucho más rápidos.

### Acceso

- **URL:** http://localhost
- **Usuario admin:** `admin`
- **Contraseña:** `adminadmin` (⚠️ cambiar en cuanto se use en serio —
  ver nota de seguridad más abajo)

### Verificación
```powershell
docker compose -p wger-docker ps        # todos "healthy"
docker compose -p wger-docker logs web  # sin errores
```

### ⚠️ Notas de seguridad pendientes antes de uso real (no bloqueantes para desarrollo local)

El `config/prod.env` de `wger-docker/` trae valores de ejemplo que
**deben cambiarse** antes de exponer esto fuera de `localhost`:
- `SECRET_KEY`: usa un valor de ejemplo público del repo.
- `JWT_PUBLIC_KEY`/`JWT_PRIVATE_KEY`: son las claves de ejemplo del
  propio repo de wger — regenerar con
  `docker compose exec web ./manage.py generate-jwt-keys`.
- Contraseña del admin (`adminadmin`): cambiarla desde el panel de administración.

Para desarrollo 100% local (solo accesible desde `localhost`) esto no es
un problema urgente, pero queda anotado para antes de cualquier
despliegue con acceso remoto.

### Notas generales
- Este entorno persiste datos en volúmenes Docker (`postgres-data`,
  `media`, `static`, `redis-data`) — sobreviven a `docker compose down`
  (sin `-v`).
- No modificar el contenido de `wger-docker/` directamente (es un repo de
  terceros clonado) — la configuración propia va en los `.env`/overrides.
- Recordatorio del roadmap: "regularly pull the latest version" — de vez
  en cuando hacer `git pull` dentro de `wger-docker/` para traer
  actualizaciones del compose oficial.

## Siguiente pieza (independiente de Docker): sync de Garmin

El módulo `backend/garmin_sync/` no depende de Docker/wger — corre en un
venv Python normal y escribe a la base de datos. Ver `backend/README.md`.
Ya implementado y testeado sin red real (PR #8); pendiente de probar
end-to-end contra una cuenta Garmin real.

