"""Genera el logo base de Pulse: mancuerna blanca sobre fondo negro
(petición explícita del usuario). Produce un PNG 1024x1024 que luego
`tauri icon` usa como fuente única para generar todo el set de iconos
de plataforma (Windows .ico, macOS .icns, PNGs de distintos tamaños).

Dibujado a mano con PIL (sin dependencias de rasterizado SVG) - formas
simples y deliberadamente geométricas para que escale bien a tamaños
pequeños (16x16 favicon) sin perder legibilidad."""
from __future__ import annotations

from PIL import Image, ImageDraw

SIZE = 1024
BG = (10, 10, 10, 255)  # negro casi puro, coherente con el tema oscuro de la app
FG = (255, 255, 255, 255)  # blanco puro

img = Image.new("RGBA", (SIZE, SIZE), BG)
draw = ImageDraw.Draw(img)

cx, cy = SIZE // 2, SIZE // 2

# Geometría de la mancuerna, todo relativo a SIZE para que sea fácil
# reescalar el lienzo si hiciera falta.
bar_half_len = int(SIZE * 0.22)
bar_thickness = int(SIZE * 0.07)
plate_outer_w = int(SIZE * 0.11)
plate_outer_h = int(SIZE * 0.34)
plate_inner_w = int(SIZE * 0.07)
plate_inner_h = int(SIZE * 0.24)
grip_pad_w = int(SIZE * 0.045)
grip_pad_h = int(SIZE * 0.14)
corner_radius = int(SIZE * 0.03)


def rounded_rect_centered(center_x, half_w, half_h, radius):
    return [center_x - half_w, cy - half_h, center_x + half_w, cy + half_h], radius


# Barra central
draw.rounded_rectangle(
    [cx - bar_half_len, cy - bar_thickness // 2, cx + bar_half_len, cy + bar_thickness // 2],
    radius=bar_thickness // 3,
    fill=FG,
)

for signo in (-1, 1):
    centro_plato = cx + signo * (bar_half_len + plate_outer_w // 2 + int(SIZE * 0.01))

    # Disco exterior (el mas grande)
    box, r = rounded_rect_centered(centro_plato, plate_outer_w // 2, plate_outer_h // 2, corner_radius)
    draw.rounded_rectangle(box, radius=r, fill=FG)

    # Disco interior mas pequeno, mas cerca de la barra - da la
    # silueta clasica de mancuerna de dos discos por lado en vez de
    # un unico bloque.
    centro_disco_interior = cx + signo * (bar_half_len + int(SIZE * 0.02))
    box2, r2 = rounded_rect_centered(
        centro_disco_interior, plate_inner_w // 2, plate_inner_h // 2, corner_radius
    )
    draw.rounded_rectangle(box2, radius=r2, fill=FG)

    # Empunadura moleteada (pequeno tope antes del disco) - detalle
    # que ayuda a leer "mancuerna" y no "pesa/barra generica" incluso
    # a tamanos pequenos.
    centro_grip = cx + signo * (bar_half_len - grip_pad_w // 2 + int(SIZE * 0.01))
    box3, r3 = rounded_rect_centered(centro_grip, grip_pad_w // 2, grip_pad_h // 2, int(SIZE * 0.01))
    draw.rounded_rectangle(box3, radius=r3, fill=FG)

img.save("frontend/src-tauri/icons/pulse-logo-source-1024.png")
print("OK: logo generado en frontend/src-tauri/icons/pulse-logo-source-1024.png")
