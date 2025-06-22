import pygame
import random
import sys

pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snowy Adventure")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Load assets
bg_image = pygame.image.load("background.png").convert()
player_image = pygame.image.load("player.png").convert_alpha()

# Player properties
player_rect = player_image.get_rect(center=(WIDTH // 2, HEIGHT - 50))
player_speed = 5

# Particle system for snow
class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = random.randint(2, 5)
        self.speed = random.uniform(1, 3)
        self.alpha = 255

    def update(self):
        self.y += self.speed
        self.alpha -= 1
        if self.alpha <= 0:
            self.alpha = 255
            self.y = -self.size
            self.x = random.randint(0, WIDTH)

    def draw(self, surface):
        pygame.draw.circle(surface, WHITE, (self.x, self.y), self.size)

# Create a list of snow particles
snow_particles = [Particle(random.randint(0, WIDTH), random.randint(0, HEIGHT)) for _ in range(200)]

# Main game loop
running = True
while running:
    screen.fill(BLACK)

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Parallax scrolling background
    screen.blit(bg_image, (0, 0))

    # Update and draw snow particles
    for particle in snow_particles:
        particle.update()
        particle.draw(screen)

    # Handle player movement
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] and player_rect.left > 0:
        player_rect.x -= player_speed
    if keys[pygame.K_RIGHT] and player_rect.right < WIDTH:
        player_rect.x += player_speed

    # Draw player
    screen.blit(player_image, player_rect)

    # Update display
    pygame.display.flip()
    pygame.time.Clock().tick(60)

pygame.quit()
sys.exit()
