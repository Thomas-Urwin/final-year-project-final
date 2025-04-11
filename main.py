import pygame
import sys
import importlib
import os
import time  
from RaceAgainstAIv2 import select_track, Game  
import trackCreatorCheckpoints  
import heuristicTesting
import dataStructureTesting
import glob  

# Initialize Pygame
pygame.init()

# Game Window Settings
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
game_window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Racetrack Game Menu")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 200, 0)
YELLOW = (255, 255, 0)
PURPLE = (160, 32, 240)

show_warning = False

class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, text_color, requires_tracks=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.is_hovered = False
        self.requires_tracks = requires_tracks
        
    def draw(self, surface):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, BLACK, self.rect, 2)  
        
        font = pygame.font.Font(None, 36)
        text_surface = font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)
        
    def update(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        
    def is_clicked(self, mouse_pos, mouse_clicked):
        return self.rect.collidepoint(mouse_pos) and mouse_clicked

def check_for_tracks():
    track_files = glob.glob("*.json") 
    return len(track_files) > 0

def draw_warning(surface):
    if show_warning:
        warning_font = pygame.font.Font(None, 36)
        warning = warning_font.render("No tracks found! Please create some in Track Creator first", True, RED)
        warning_rect = warning.get_rect(center=(WINDOW_WIDTH//2, 220))
        surface.blit(warning, warning_rect)

def draw_title(surface):
    font = pygame.font.Font(None, 74)
    title = font.render("Racetrack Game Menu", True, BLACK)
    title_rect = title.get_rect(center=(WINDOW_WIDTH//2, 120))
    surface.blit(title, title_rect)
    
    font = pygame.font.Font(None, 32)
    subtitle = font.render("Select a game mode to play", True, GRAY)
    subtitle_rect = subtitle.get_rect(center=(WINDOW_WIDTH//2, 180))
    surface.blit(subtitle, subtitle_rect)
    
    draw_warning(surface)

def run_ai_race():
    result = select_track()
    if not result:
        return True  
    
    track_filename, laps, show_ai_path = result
    
    game = Game()
    game.required_laps = laps
    game.show_ai_path = show_ai_path
    game.load_track(track_filename)
    game.game_start_time = time.time()
    
    clock = pygame.time.Clock()
    window_open = True
    
    while window_open:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                window_open = False
            elif event.type == pygame.MOUSEBUTTONDOWN and game.is_player_turn and game.game_running:
                game.handle_player_move(pygame.mouse.get_pos())
            elif event.type == pygame.KEYDOWN and not game.game_running:
                window_open = False
        
        if game.game_running:
            game.update()
        game.draw()
        clock.tick(60)
    
    return True

def run_heuristic_test():
    original_render_results = heuristicTesting.render_results
    
    def patched_render_results(screen, all_results):
        result = original_render_results(screen, all_results)
        return result if result is False else True
    
    heuristicTesting.render_results = patched_render_results
    
    heuristicTesting.test_heuristics()
    
    return True

def run_data_structure_test():    
    original_render_results = dataStructureTesting.render_results
    
    def patched_render_results(screen, all_results):
        result = original_render_results(screen, all_results)
        return result if result is False else True
    

    dataStructureTesting.render_results = patched_render_results
    
    dataStructureTesting.test_data_structures()
    
    return True

def run_track_creator():
    return trackCreatorCheckpoints.main()

def main_menu():
    global show_warning
    clock = pygame.time.Clock()
    
    button_width = 300  
    button_height = 80
    button_spacing = 40 
    
    grid_start_y = 240
    left_column_x = WINDOW_WIDTH // 2 - button_width - button_spacing // 2
    right_column_x = WINDOW_WIDTH // 2 + button_spacing // 2
    
    buttons = [
        Button(left_column_x, grid_start_y, button_width, button_height, "Race Against AI", LIGHT_GRAY, WHITE, BLACK, True),
        Button(right_column_x, grid_start_y, button_width, button_height, "Track Creator", LIGHT_GRAY, WHITE, BLACK, False),
        Button(left_column_x, grid_start_y + button_height + button_spacing, button_width, button_height, "Heuristic Testing", LIGHT_GRAY, WHITE, BLACK, True),
        Button(right_column_x, grid_start_y + button_height + button_spacing, button_width, button_height, "Data Structure Testing", LIGHT_GRAY, WHITE, BLACK, True),
        Button(WINDOW_WIDTH // 2 - button_width // 2, grid_start_y + 2 * (button_height + button_spacing) + 40, button_width, button_height, "Exit", LIGHT_GRAY, WHITE, BLACK, False)
    ]
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: 
                    mouse_clicked = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        for button in buttons:
            button.update(mouse_pos)
        
        if mouse_clicked:
            for button in buttons:
                if button.is_clicked(mouse_pos, mouse_clicked):
                    if button.requires_tracks and not check_for_tracks():
                        show_warning = True
                        continue
                    
                    if button.text == "Race Against AI":
                        if not run_ai_race():
                            running = False
                    elif button.text == "Track Creator":
                        if not run_track_creator():
                            running = False
                    elif button.text == "Heuristic Testing":
                        if not run_heuristic_test():
                            running = False
                    elif button.text == "Data Structure Testing":
                        if not run_data_structure_test():
                            running = False
                    elif button.text == "Exit":
                        running = False
                    show_warning = False 
        
        game_window.fill(WHITE)
        
        draw_title(game_window)
        
        for button in buttons:
            button.draw(game_window)
        
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main_menu()
    pygame.quit()
    sys.exit() 