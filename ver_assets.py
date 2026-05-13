import pygame
import sys
from pathlib import Path

pygame.init()

ASSET_DIR = Path(__file__).parent / "assets"
FILES = [
    "player.png",
    "enemy.png",
    "wall.png",
    "block.png",
    "bomb.png",
    "power_bomb.png",
    "power_range.png",
    "power_speed.png",
]

WIDTH, HEIGHT = 1100, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Visor de Assets")

font = pygame.font.SysFont("arial", 22, bold=True)
clock = pygame.time.Clock()

images = []
for name in FILES:
    path = ASSET_DIR / name
    if path.exists():
        img = pygame.image.load(str(path)).convert_alpha()
        preview = pygame.transform.smoothscale(img, (180, 180))
        images.append((name, preview))
    else:
        images.append((name, None))

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    screen.fill((30, 30, 30))

    for i, (name, img) in enumerate(images):
        x = 30 + (i % 4) * 260
        y = 40 + (i // 4) * 300

        pygame.draw.rect(screen, (60, 60, 60), (x - 10, y - 10, 220, 240))

        text = font.render(name, True, (255, 255, 255))
        screen.blit(text, (x, y - 35))

        if img:
            screen.blit(img, (x, y))
        else:
            missing = font.render("No encontrado", True, (255, 80, 80))
            screen.blit(missing, (x, y + 70))

    pygame.display.flip()
    clock.tick(60)