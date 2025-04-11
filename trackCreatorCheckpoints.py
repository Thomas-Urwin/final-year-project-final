# Coded on the 13/02/2025, updated to a two checkpoint system


import pygame
import sys
import json
import os

# Initialize Pygame
pygame.init()

# Window Configuration
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
game_window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Racetrack Circuit Creator")

# Grid Settings
GRID_CELL_SIZE = 20
GRID_COLUMNS = WINDOW_WIDTH // GRID_CELL_SIZE
GRID_ROWS = WINDOW_HEIGHT // GRID_CELL_SIZE

# Color Definitions
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (160, 160, 160)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 200, 0)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)  
LIGHT_GRAY = (220, 220, 220)
DARK_GRAY = (50, 50, 50)

# Track Tile Types
TRACK_TILE_TYPES = {
    'out_of_bounds': 0,
    'road': 1,
    'start_finish_line': 2,
    'checkpoint1': 3,
    'checkpoint2': 4  
}

TILE_COLOR_MAPPING = {
    0: BLACK,
    1: WHITE,
    2: GREEN,
    3: BLUE,
    4: PURPLE  
}

# Editor State
track_layout = [[TRACK_TILE_TYPES['road'] for column in range(GRID_COLUMNS)] for row in range(GRID_ROWS)]
selected_tile_type = TRACK_TILE_TYPES['road']
is_editing_mode = True
brush_size = 1
is_drawing_active = False

# UI State
is_save_dialog_active = False
is_load_dialog_active = False
input_text = ""
save_overwrite_confirm = False
status_message = ""
status_message_duration = 0
should_show_instructions = True

def get_available_tracks():
    tracks = []
    for file in os.listdir():
        if file.endswith('.json'):
            tracks.append(file)
    return tracks

def save_racetrack():
    global is_save_dialog_active, input_text
    if validate_track_layout():
        is_save_dialog_active = True
        input_text = ""
    else:
        global status_message, status_message_duration
        status_message = "Invalid track: Need 4+ connected start/finish tiles and both checkpoint types (4+ tiles each)"
        status_message_duration = 180
        print(status_message)

def load_racetrack():
    global is_load_dialog_active
    is_load_dialog_active = True

def handle_save_confirmation():
    global track_layout, status_message, status_message_duration, is_save_dialog_active, save_overwrite_confirm

    filename = input_text.strip()
    if not filename:
        return
    
    if not filename.endswith('.json'):
        filename += '.json'
    
    if os.path.exists(filename) and not save_overwrite_confirm:
        save_overwrite_confirm = True
        return
    
    with open(filename, 'w') as file:
        json.dump(track_layout, file)
    
    status_message = f"Track saved to {filename}"
    status_message_duration = 180
    print(status_message)
    
    is_save_dialog_active = False
    save_overwrite_confirm = False

def handle_track_selection(track_name):
    global track_layout, status_message, status_message_duration, is_load_dialog_active
    
    try:
        with open(track_name, 'r') as file:
            track_layout = json.load(file)
        status_message = f"Track loaded from {track_name}"
        status_message_duration = 180
        print(status_message)
    except FileNotFoundError:
        status_message = f"File {track_name} not found."
        status_message_duration = 180
        print(status_message)
    
    is_load_dialog_active = False

def draw_track_grid():
    for row in range(GRID_ROWS):
        for column in range(GRID_COLUMNS):
            tile_value = track_layout[row][column]
            tile_color = TILE_COLOR_MAPPING.get(tile_value, WHITE)
            tile_rect = pygame.Rect(column * GRID_CELL_SIZE, row * GRID_CELL_SIZE, GRID_CELL_SIZE, GRID_CELL_SIZE)
            pygame.draw.rect(game_window, tile_color, tile_rect)
            pygame.draw.rect(game_window, BLACK, tile_rect, 1)

def draw_save_dialog():
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.fill(BLACK)
    overlay.set_alpha(180)
    game_window.blit(overlay, (0, 0))
    
    dialog_width, dialog_height = 500, 200
    dialog_rect = pygame.Rect(WINDOW_WIDTH//2 - dialog_width//2, WINDOW_HEIGHT//2 - dialog_height//2, 
                            dialog_width, dialog_height)
    pygame.draw.rect(game_window, DARK_GRAY, dialog_rect)
    pygame.draw.rect(game_window, WHITE, dialog_rect, 2)
    
    title_font = pygame.font.SysFont(None, 36)
    title_text = title_font.render("Save Track", True, WHITE)
    game_window.blit(title_text, (dialog_rect.centerx - title_text.get_width()//2, dialog_rect.y + 20))
    
    input_font = pygame.font.SysFont(None, 32)
    input_rect = pygame.Rect(dialog_rect.x + 50, dialog_rect.y + 70, dialog_width - 100, 40)
    pygame.draw.rect(game_window, WHITE, input_rect)
    pygame.draw.rect(game_window, BLACK, input_rect, 2)
    
    input_surface = input_font.render(input_text, True, BLACK)
    game_window.blit(input_surface, (input_rect.x + 10, input_rect.y + 10))
    
    if pygame.time.get_ticks() % 1000 < 500:
        cursor_x = input_rect.x + 10 + input_surface.get_width()
        pygame.draw.line(game_window, BLACK, (cursor_x, input_rect.y + 10), 
                       (cursor_x, input_rect.y + 30), 2)
    
    instruction_font = pygame.font.SysFont(None, 24)
    instruction_text = instruction_font.render("Enter filename (without extension)", True, WHITE)
    game_window.blit(instruction_text, (dialog_rect.centerx - instruction_text.get_width()//2, 
                                      dialog_rect.y + 50))
    
    button_font = pygame.font.SysFont(None, 28)
    button_width, button_height = 100, 30
    
    save_button_rect = pygame.Rect(dialog_rect.centerx - button_width - 10, 
                                 dialog_rect.y + dialog_height - 50, 
                                 button_width, button_height)
    pygame.draw.rect(game_window, GREEN, save_button_rect)
    pygame.draw.rect(game_window, BLACK, save_button_rect, 2)
    save_text = button_font.render("Save", True, BLACK)
    game_window.blit(save_text, (save_button_rect.centerx - save_text.get_width()//2, 
                               save_button_rect.centery - save_text.get_height()//2))
    
    cancel_button_rect = pygame.Rect(dialog_rect.centerx + 10, 
                                   dialog_rect.y + dialog_height - 50, 
                                   button_width, button_height)
    pygame.draw.rect(game_window, RED, cancel_button_rect)
    pygame.draw.rect(game_window, BLACK, cancel_button_rect, 2)
    cancel_text = button_font.render("Cancel", True, BLACK)
    game_window.blit(cancel_text, (cancel_button_rect.centerx - cancel_text.get_width()//2, 
                                 cancel_button_rect.centery - cancel_text.get_height()//2))
    
    if save_overwrite_confirm:
        warning_rect = pygame.Rect(dialog_rect.x + 20, dialog_rect.y + dialog_height - 80, 
                                 dialog_width - 40, 25)
        warning_text = instruction_font.render(f"File '{input_text}.json' already exists. Click Save again to overwrite.", 
                                             True, YELLOW)
        game_window.blit(warning_text, (warning_rect.centerx - warning_text.get_width()//2, 
                                      warning_rect.centery - warning_text.get_height()//2))
    
    return save_button_rect, cancel_button_rect

def draw_load_dialog():
    tracks = get_available_tracks()
    
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.fill(BLACK)
    overlay.set_alpha(180)
    game_window.blit(overlay, (0, 0))
    
    button_height = 30
    track_spacing = 40
    header_height = 60
    footer_height = 70  
    
    content_height = len(tracks) * track_spacing
    
    dialog_height = min(500, header_height + content_height + footer_height)
    dialog_width = 500
    
    max_visible_tracks = (dialog_height - header_height - footer_height) // track_spacing
    visible_tracks = tracks[:max_visible_tracks]
    
    dialog_rect = pygame.Rect(WINDOW_WIDTH//2 - dialog_width//2, WINDOW_HEIGHT//2 - dialog_height//2, 
                            dialog_width, dialog_height)
    pygame.draw.rect(game_window, DARK_GRAY, dialog_rect)
    pygame.draw.rect(game_window, WHITE, dialog_rect, 2)
    
    title_font = pygame.font.SysFont(None, 36)
    title_text = title_font.render("Load Track", True, WHITE)
    game_window.blit(title_text, (dialog_rect.centerx - title_text.get_width()//2, dialog_rect.y + 20))
    
    button_font = pygame.font.SysFont(None, 28)
    button_width = dialog_width - 100
    button_rects = []
    
    if not tracks:
        no_tracks_text = button_font.render("No track files found", True, WHITE)
        game_window.blit(no_tracks_text, (dialog_rect.centerx - no_tracks_text.get_width()//2, 
                                        dialog_rect.y + 70))
    else:
        for i, track in enumerate(visible_tracks):
            button_rect = pygame.Rect(dialog_rect.centerx - button_width//2, 
                                    dialog_rect.y + header_height + i * track_spacing, 
                                    button_width, button_height)
            
            mouse_pos = pygame.mouse.get_pos()
            if button_rect.collidepoint(mouse_pos):
                pygame.draw.rect(game_window, WHITE, button_rect)
                text_color = BLACK
            else:
                pygame.draw.rect(game_window, LIGHT_GRAY, button_rect)
                text_color = BLACK
            
            pygame.draw.rect(game_window, BLACK, button_rect, 2)
            track_text = button_font.render(track, True, text_color)
            game_window.blit(track_text, (button_rect.centerx - track_text.get_width()//2, 
                                        button_rect.centery - track_text.get_height()//2))
            button_rects.append((button_rect, track))
    
    cancel_button_rect = pygame.Rect(dialog_rect.centerx - 50, 
                                   dialog_rect.y + dialog_height - 40, 
                                   100, 30)
    pygame.draw.rect(game_window, RED, cancel_button_rect)
    pygame.draw.rect(game_window, BLACK, cancel_button_rect, 2)
    cancel_text = button_font.render("Cancel", True, BLACK)
    game_window.blit(cancel_text, (cancel_button_rect.centerx - cancel_text.get_width()//2, 
                                 cancel_button_rect.centery - cancel_text.get_height()//2))
    
    return button_rects, cancel_button_rect

def validate_track_layout():
    start_finish_groups = find_all_connected_groups(TRACK_TILE_TYPES['start_finish_line'])
    if not any(len(group) >= 4 for group in start_finish_groups):
        return False
    
    checkpoint1_groups = find_all_connected_groups(TRACK_TILE_TYPES['checkpoint1'])
    checkpoint2_groups = find_all_connected_groups(TRACK_TILE_TYPES['checkpoint2'])
    
    valid_checkpoint1_groups = [group for group in checkpoint1_groups if len(group) >= 4]
    valid_checkpoint2_groups = [group for group in checkpoint2_groups if len(group) >= 4]
    
    if not valid_checkpoint1_groups or not valid_checkpoint2_groups:
        return False
    
    for checkpoint1_group in valid_checkpoint1_groups:
        for checkpoint2_group in valid_checkpoint2_groups:
            if are_groups_adjacent(checkpoint1_group, checkpoint2_group):
                return False
    
    return True

def find_all_connected_groups(target_tile_type):
    visited_tiles = [[False for column in range(GRID_COLUMNS)] for row in range(GRID_ROWS)]
    connected_groups = []
    for row in range(GRID_ROWS):
        for column in range(GRID_COLUMNS):
            if track_layout[row][column] == target_tile_type and not visited_tiles[row][column]:
                group = find_connected_tiles((column, row), target_tile_type, visited_tiles)
                connected_groups.append(group)
    return connected_groups

def find_connected_tiles(start_position, target_tile_type, visited_flags):
    search_queue = [start_position]
    connected_tiles = []
    while search_queue:
        current_column, current_row = search_queue.pop(0)
        if visited_flags[current_row][current_column]:
            continue
        visited_flags[current_row][current_column] = True
        if track_layout[current_row][current_column] == target_tile_type:
            connected_tiles.append((current_column, current_row))
            for column_offset, row_offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor_column = current_column + column_offset
                neighbor_row = current_row + row_offset
                if 0 <= neighbor_column < GRID_COLUMNS and 0 <= neighbor_row < GRID_ROWS:
                    if not visited_flags[neighbor_row][neighbor_column] and track_layout[neighbor_row][neighbor_column] == target_tile_type:
                        search_queue.append((neighbor_column, neighbor_row))
    return connected_tiles

def are_groups_adjacent(first_group, second_group):
    for (column, row) in first_group:
        for column_offset, row_offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            adjacent_column = column + column_offset
            adjacent_row = row + row_offset
            if (adjacent_column, adjacent_row) in second_group:
                return True
    return False

game_clock = pygame.time.Clock()

info_font = pygame.font.SysFont(None, 24)
header_font = pygame.font.SysFont(None, 36)

instruction_lines = [
    "Instructions:",
    "",
    "Toggle Edit Mode: Press 'E'",
    "Save Track: Press 'S'",
    "Load Track: Press 'L'",
    "Increase Brush Size: Press '+'",
    "Decrease Brush Size: Press '-'",
    "Select Tile Type:",
    "  1: Out of Bounds",
    "  2: Road",
    "  3: Start/Finish Line",
    "  4: Checkpoint 1",
    "  5: Checkpoint 2",
    "Show/Hide Instructions: Press 'H'",
    "",
    "Requirements to Save:",
    "- 4+ connected Start/Finish tiles",
    "- One group of Checkpoint 1 (4+ tiles)",
    "- One group of Checkpoint 2 (4+ tiles)",
    "- Checkpoints must not be connected",
    "",
    "Current Settings:",
    f"- Editing Mode: {'On' if is_editing_mode else 'Off'}",
    f"- Selected Tile: {selected_tile_type}",
    f"- Brush Size: {brush_size}",
]

def draw_instruction_panel():
    instruction_panel = pygame.Surface((WINDOW_WIDTH - 100, WINDOW_HEIGHT - 100))
    instruction_panel.fill((50, 50, 50))
    instruction_panel.set_alpha(220)

    # Update dynamic settings in instructions
    instruction_lines[-3] = f"- Editing Mode: {'On' if is_editing_mode else 'Off'}"
    instruction_lines[-2] = f"- Selected Tile: {selected_tile_type}"
    instruction_lines[-1] = f"- Brush Size: {brush_size}"

    vertical_offset = 20
    for line in instruction_lines:
        text_color = YELLOW if line.startswith("Instructions") else WHITE
        text_surface = header_font.render(line, True, text_color) if line.startswith("Instructions") else info_font.render(line, True, WHITE)
        instruction_panel.blit(text_surface, (20, vertical_offset))
        vertical_offset += 30 if line.startswith("Instructions") else 25

    game_window.blit(instruction_panel, (50, 50))

def draw_help_hint():
    hint_panel_x = WINDOW_WIDTH - 280
    hint_panel_y = 15
    hint_panel_width = 270
    hint_panel_height = 30

    current_mouse_x, current_mouse_y = pygame.mouse.get_pos()
    if not (hint_panel_x <= current_mouse_x <= hint_panel_x + hint_panel_width and hint_panel_y <= current_mouse_y <= hint_panel_y + hint_panel_height):
        hint_background = pygame.Surface((hint_panel_width, hint_panel_height))
        hint_background.fill((50, 50, 50))
        hint_background.set_alpha(220)
        hint_text = info_font.render("Press 'H' for help, 'ESC' for menu", True, WHITE)
        hint_background.blit(hint_text, (10, 10))
        game_window.blit(hint_background, (hint_panel_x, hint_panel_y))

def draw_status_message():
    if status_message and not should_show_instructions:
        message_surface = info_font.render(status_message, True, YELLOW)
        # Create background rectangle with padding
        padding = 10
        bg_rect = pygame.Rect(0, WINDOW_HEIGHT - 40 - padding, 
                            message_surface.get_width() + padding * 2, 
                            message_surface.get_height() + padding * 2)
        # Create semi-transparent background
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 180))  # Black with 180 alpha (70% opacity)
        game_window.blit(bg_surface, bg_rect)
        # Draw the message on top
        game_window.blit(message_surface, (padding, WINDOW_HEIGHT - 35 - padding))

def main():
    global editor_running, is_save_dialog_active, save_overwrite_confirm, is_load_dialog_active, status_message
    global status_message_duration, should_show_instructions, is_editing_mode, is_drawing_active
    global brush_size, selected_tile_type, input_text, track_layout

    editor_running = True
    is_save_dialog_active = False
    is_load_dialog_active = False
    input_text = ""
    save_overwrite_confirm = False
    status_message = ""
    status_message_duration = 0
    should_show_instructions = True
    is_editing_mode = True
    brush_size = 1
    is_drawing_active = False
    selected_tile_type = TRACK_TILE_TYPES['road']
    track_layout = [[TRACK_TILE_TYPES['road'] for column in range(GRID_COLUMNS)] for row in range(GRID_ROWS)]

    while editor_running:
        game_clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                editor_running = False
                break
            elif event.type == pygame.KEYDOWN:
                if is_save_dialog_active:
                    if event.key == pygame.K_RETURN:
                        handle_save_confirmation()
                    elif event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        is_save_dialog_active = False
                        save_overwrite_confirm = False
                    else:
                        if event.unicode.isalnum() or event.unicode in '-_':
                            input_text += event.unicode
                elif is_load_dialog_active:
                    if event.key == pygame.K_ESCAPE:
                        is_load_dialog_active = False
                elif event.key == pygame.K_h:
                    should_show_instructions = not should_show_instructions
                elif event.key == pygame.K_ESCAPE:
                    editor_running = False
                elif not should_show_instructions:
                    if event.key == pygame.K_e:
                        is_editing_mode = not is_editing_mode
                    elif event.key == pygame.K_s:
                        save_racetrack()
                    elif event.key == pygame.K_l:
                        load_racetrack()
                    elif event.key == pygame.K_1:
                        selected_tile_type = TRACK_TILE_TYPES['out_of_bounds']
                    elif event.key == pygame.K_2:
                        selected_tile_type = TRACK_TILE_TYPES['road']
                    elif event.key == pygame.K_3:
                        selected_tile_type = TRACK_TILE_TYPES['start_finish_line']
                    elif event.key == pygame.K_4:
                        selected_tile_type = TRACK_TILE_TYPES['checkpoint1']
                    elif event.key == pygame.K_5:
                        selected_tile_type = TRACK_TILE_TYPES['checkpoint2']
                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                        brush_size = min(10, brush_size + 1)
                    elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE):
                        brush_size = max(1, brush_size - 1)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  
                if is_save_dialog_active:
                    save_button, cancel_button = draw_save_dialog()
                    if save_button.collidepoint(event.pos):
                        handle_save_confirmation()
                    elif cancel_button.collidepoint(event.pos):
                        is_save_dialog_active = False
                        save_overwrite_confirm = False
                elif is_load_dialog_active:
                    track_buttons, cancel_button = draw_load_dialog()
                    if cancel_button.collidepoint(event.pos):
                        is_load_dialog_active = False
                    else:
                        for button, track in track_buttons:
                            if button.collidepoint(event.pos):
                                handle_track_selection(track)
                                break
                elif is_editing_mode and not should_show_instructions:
                    is_drawing_active = True
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    grid_column = mouse_x // GRID_CELL_SIZE
                    grid_row = mouse_y // GRID_CELL_SIZE
                    brush_radius = brush_size // 2
                    for row_offset in range(-brush_radius, brush_radius + 1):
                        for column_offset in range(-brush_radius, brush_radius + 1):
                            modified_column = grid_column + column_offset
                            modified_row = grid_row + row_offset
                            if 0 <= modified_column < GRID_COLUMNS and 0 <= modified_row < GRID_ROWS:
                                track_layout[modified_row][modified_column] = selected_tile_type
            elif event.type == pygame.MOUSEBUTTONUP and is_editing_mode:
                is_drawing_active = False
            elif event.type == pygame.MOUSEMOTION and is_editing_mode and is_drawing_active and not should_show_instructions:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                grid_column = mouse_x // GRID_CELL_SIZE
                grid_row = mouse_y // GRID_CELL_SIZE
                brush_radius = brush_size // 2
                for row_offset in range(-brush_radius, brush_radius + 1):
                    for column_offset in range(-brush_radius, brush_radius + 1):
                        modified_column = grid_column + column_offset
                        modified_row = grid_row + row_offset
                        if 0 <= modified_column < GRID_COLUMNS and 0 <= modified_row < GRID_ROWS:
                            track_layout[modified_row][modified_column] = selected_tile_type

        if status_message_duration > 0:
            status_message_duration -= 1
        else:
            status_message = ""

        game_window.fill(WHITE)
        draw_track_grid()

        if should_show_instructions:
            draw_instruction_panel()
        else:
            draw_help_hint()

        if is_save_dialog_active:
            draw_save_dialog()
        elif is_load_dialog_active:
            draw_load_dialog()

        draw_status_message()

        pygame.display.update()
    
    return True  

if __name__ == "__main__":
    main()
    pygame.quit()
    sys.exit()