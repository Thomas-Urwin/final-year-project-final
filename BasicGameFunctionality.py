# Coded on the 13/02/2025, updated code to work with 
# the new 2 checkpoint sytem. 


import pygame
import sys
import json
import random

# Initialize Pygame
pygame.init()

# Game Window Settings
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
game_window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Racetrack Circuit Game")

# Grid Configuration
GRID_CELL_SIZE = 20
GRID_COLUMNS = WINDOW_WIDTH // GRID_CELL_SIZE
GRID_ROWS = WINDOW_HEIGHT // GRID_CELL_SIZE

# Color Definitions
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 200, 0)
YELLOW = (255, 255, 0)
PURPLE = (160, 32, 240)
LIGHT_GRAY = (220, 220, 220)

# Track Tile Types
TRACK_TILE_TYPES = {
    'out_of_bounds': 0,
    'wall': 1,
    'road': 2,
    'start_finish_line': 3,
    'checkpoint1': 4,
    'checkpoint2': 5
}

TILE_COLOR_MAPPING = {
    0: BLACK,
    1: GRAY,
    2: WHITE,
    3: GREEN,
    4: BLUE,
    5: PURPLE
}

# Game State Variables
track_layout = []
car_grid_x = 0
car_grid_y = 0
car_velocity_x = 0
car_velocity_y = 0
game_running = True
is_animating = False
animation_total_steps = 10
current_animation_step = 0
car_path_history = []
position_markers = []
possible_next_positions = []
total_moves_made = 0
number_of_laps = 1
current_lap_number = 1
checkpoint1_passed = False
checkpoint2_passed = False
checkpoint1_group = []
checkpoint2_group = []
tiles_crossed_during_move = []

def load_racetrack():
    global track_layout, checkpoint1_group, checkpoint2_group
    input_filename = input("Enter track filename to load (without extension): ")
    if not input_filename.endswith('.json'):
        input_filename += '.json'
    try:
        with open(input_filename, 'r') as file:
            track_layout = json.load(file)
        print(f"Track loaded from {input_filename}")
        
        # Find checkpoint groups using BFS
        visited_tiles = [[False for column in range(GRID_COLUMNS)] for row in range(GRID_ROWS)]
        
        # Find Checkpoint 1 group
        for row in range(GRID_ROWS):
            for column in range(GRID_COLUMNS):
                if track_layout[row][column] == TRACK_TILE_TYPES['checkpoint1'] and not visited_tiles[row][column]:
                    checkpoint1_group = find_connected_checkpoints((column, row), TRACK_TILE_TYPES['checkpoint1'], visited_tiles)
                    break
                    
        # Find Checkpoint 2 group
        for row in range(GRID_ROWS):
            for column in range(GRID_COLUMNS):
                if track_layout[row][column] == TRACK_TILE_TYPES['checkpoint2'] and not visited_tiles[row][column]:
                    checkpoint2_group = find_connected_checkpoints((column, row), TRACK_TILE_TYPES['checkpoint2'], visited_tiles)
                    break
                    
        print(f"Found checkpoint1 group with {len(checkpoint1_group)} tiles")
        print(f"Found checkpoint2 group with {len(checkpoint2_group)} tiles")
        
    except FileNotFoundError:
        print(f"File {input_filename} not found.")
        sys.exit()

def find_connected_checkpoints(start_position, target_tile_type, visited_flags):
    search_queue = [start_position]
    connected_tiles = []
    while search_queue:
        current_x, current_y = search_queue.pop(0)
        if visited_flags[current_y][current_x]:
            continue
        visited_flags[current_y][current_x] = True
        if track_layout[current_y][current_x] == target_tile_type:
            connected_tiles.append((current_x, current_y))
            # Check all four directions
            for x_offset, y_offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor_x = current_x + x_offset
                neighbor_y = current_y + y_offset
                if 0 <= neighbor_x < GRID_COLUMNS and 0 <= neighbor_y < GRID_ROWS:
                    if not visited_flags[neighbor_y][neighbor_x] and track_layout[neighbor_y][neighbor_x] == target_tile_type:
                        search_queue.append((neighbor_x, neighbor_y))
    return connected_tiles

def find_start_positions():
    start_positions_list = []
    for row in range(GRID_ROWS):
        for column in range(GRID_COLUMNS):
            if track_layout[row][column] == TRACK_TILE_TYPES['start_finish_line']:
                start_positions_list.append((column, row))
    return start_positions_list

def calculate_bresenham_line(start_x, start_y, end_x, end_y):
    line_points = []
    delta_x = abs(end_x - start_x)
    delta_y = abs(end_y - start_y)
    current_x, current_y = start_x, start_y
    x_step = 1 if end_x > start_x else -1
    y_step = 1 if end_y > start_y else -1
    
    if delta_x > delta_y:
        error = delta_x // 2
        while current_x != end_x:
            line_points.append((current_x, current_y))
            error -= delta_y
            if error < 0:
                current_y += y_step
                error += delta_x
            current_x += x_step
    else:
        error = delta_y // 2
        while current_y != end_y:
            line_points.append((current_x, current_y))
            error -= delta_x
            if error < 0:
                current_x += x_step
                error += delta_y
            current_y += y_step
    line_points.append((end_x, end_y))
    return line_points

def validate_move(start_x, start_y, end_x, end_y):
    trajectory_points = calculate_bresenham_line(start_x, start_y, end_x, end_y)
    is_valid_move = True
    crossed_tiles = []
    
    for point_x, point_y in trajectory_points:
        # Check if point is within grid bounds
        if not (0 <= point_x < GRID_COLUMNS and 0 <= point_y < GRID_ROWS):
            is_valid_move = False
            break
        
        tile_type = track_layout[point_y][point_x]
        if tile_type == TRACK_TILE_TYPES['wall'] or tile_type == TRACK_TILE_TYPES['out_of_bounds']:
            is_valid_move = False
            break
            
        if tile_type in [TRACK_TILE_TYPES['checkpoint1'], TRACK_TILE_TYPES['checkpoint2'], TRACK_TILE_TYPES['start_finish_line']]:
            crossed_tiles.append((point_x, point_y, tile_type))
    
    return is_valid_move, crossed_tiles

def calculate_possible_moves():
    possible_moves = []
    for x_velocity_change in [-1, 0, 1]:
        for y_velocity_change in [-1, 0, 1]:
            new_velocity_x = car_velocity_x + x_velocity_change
            new_velocity_y = car_velocity_y + y_velocity_change
            new_position_x = car_grid_x + new_velocity_x
            new_position_y = car_grid_y + new_velocity_y
            if 0 <= new_position_x < GRID_COLUMNS and 0 <= new_position_y < GRID_ROWS:
                move_valid, _ = validate_move(car_grid_x, car_grid_y, new_position_x, new_position_y)
                if move_valid:
                    possible_moves.append((new_position_x, new_position_y, new_velocity_x, new_velocity_y))
    return possible_moves

def process_crossed_tiles(crossed_tiles_list):
    global checkpoint1_passed, checkpoint2_passed, current_lap_number
    
    for tile_x, tile_y, tile_type in crossed_tiles_list:
        if tile_type == TRACK_TILE_TYPES['checkpoint1'] and not checkpoint1_passed:
            if (tile_x, tile_y) in checkpoint1_group:
                checkpoint1_passed = True
                print("Checkpoint 1 passed!")
        elif tile_type == TRACK_TILE_TYPES['checkpoint2'] and checkpoint1_passed and not checkpoint2_passed:
            if (tile_x, tile_y) in checkpoint2_group:
                checkpoint2_passed = True
                print("Checkpoint 2 passed!")
        elif tile_type == TRACK_TILE_TYPES['start_finish_line']:
            if checkpoint1_passed and checkpoint2_passed:
                current_lap_number += 1
                checkpoint1_passed = False
                checkpoint2_passed = False
                print(f"Lap {current_lap_number-1}/{number_of_laps} completed!")
                if current_lap_number > number_of_laps:
                    print(f"Race finished in {total_moves_made} moves!")
                    return True
            else:
                if not checkpoint1_passed:
                    print("Crossed finish line but missed Checkpoint 1!")
                elif not checkpoint2_passed:
                    print("Crossed finish line but missed Checkpoint 2!")
    return False

# Game Initialization
load_racetrack()
number_of_laps = int(input("Enter number of laps to complete: "))
starting_positions = find_start_positions()
if not starting_positions:
    print("No starting positions found on track.")
    sys.exit()

# Place car at random starting position
car_grid_x, car_grid_y = random.choice(starting_positions)
car_path_history = [(car_grid_x, car_grid_y)]
position_markers = [(car_grid_x, car_grid_y)]

game_clock = pygame.time.Clock()

# Main Game Loop
while game_running:
    game_clock.tick(60)

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game_running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and not is_animating:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            clicked_grid_x = mouse_x // GRID_CELL_SIZE
            clicked_grid_y = mouse_y // GRID_CELL_SIZE
            for position in possible_next_positions:
                pos_x, pos_y, vel_x, vel_y = position
                if clicked_grid_x == pos_x and clicked_grid_y == pos_y:
                    is_animating = True
                    current_animation_step = 0
                    animation_start = (car_grid_x, car_grid_y)
                    animation_end = (pos_x, pos_y)
                    new_velocity_x = vel_x
                    new_velocity_y = vel_y
                    total_moves_made += 1
                    
                    # Record tiles crossed during this move
                    _, tiles_crossed_during_move = validate_move(car_grid_x, car_grid_y, pos_x, pos_y)
                    break

    # Handle animation
    if is_animating:
        interpolation_factor = (current_animation_step + 1) / animation_total_steps
        animated_x = (1 - interpolation_factor) * animation_start[0] + interpolation_factor * animation_end[0]
        animated_y = (1 - interpolation_factor) * animation_start[1] + interpolation_factor * animation_end[1]
        current_animation_step += 1
        
        if current_animation_step >= animation_total_steps:
            is_animating = False
            car_grid_x, car_grid_y = animation_end
            car_velocity_x = new_velocity_x
            car_velocity_y = new_velocity_y
            car_path_history.append((car_grid_x, car_grid_y))
            position_markers.append((car_grid_x, car_grid_y))
            
            # Check for lap completion
            if process_crossed_tiles(tiles_crossed_during_move):
                game_running = False

    # Calculate possible moves when not animating
    possible_next_positions = calculate_possible_moves() if not is_animating else []

    # Draw game elements
    game_window.fill(WHITE)
    
    # Draw track tiles
    for row in range(GRID_ROWS):
        for column in range(GRID_COLUMNS):
            tile_value = track_layout[row][column]
            color = TILE_COLOR_MAPPING.get(tile_value, WHITE)
            rect = pygame.Rect(column * GRID_CELL_SIZE, row * GRID_CELL_SIZE, GRID_CELL_SIZE, GRID_CELL_SIZE)
            pygame.draw.rect(game_window, color, rect)
            
            if color == WHITE:
                grid_color = GRAY
            elif color == GREEN:
                grid_color = (0, 100, 0)  # Darker green
            elif color == RED:
                grid_color = (139, 0, 0)  # Darker red
            else:
                grid_color = color
            
            pygame.draw.rect(game_window, grid_color, rect, 1)  # Grid lines

    # Draw car path
    if len(car_path_history) > 1:
        for segment in range(1, len(car_path_history)):
            start_point = (car_path_history[segment-1][0]*GRID_CELL_SIZE+GRID_CELL_SIZE//2,
                          car_path_history[segment-1][1]*GRID_CELL_SIZE+GRID_CELL_SIZE//2)
            end_point = (car_path_history[segment][0]*GRID_CELL_SIZE+GRID_CELL_SIZE//2,
                        car_path_history[segment][1]*GRID_CELL_SIZE+GRID_CELL_SIZE//2)
            pygame.draw.line(game_window, BLACK, start_point, end_point, 4)

    # Draw position markers
    for position in position_markers:
        marker_position = (position[0]*GRID_CELL_SIZE+GRID_CELL_SIZE // 2, position[1]*GRID_CELL_SIZE+GRID_CELL_SIZE // 2)
        pygame.draw.circle(game_window, BLUE, marker_position, 4)

    # Draw car
    car_rect = pygame.Rect(car_grid_x*GRID_CELL_SIZE, car_grid_y*GRID_CELL_SIZE, GRID_CELL_SIZE, GRID_CELL_SIZE)
    pygame.draw.rect(game_window, RED, car_rect)

    # Draw possible move locations
    for position in possible_next_positions:
        pos_x, pos_y, _, _ = position
        position_rect = pygame.Rect(pos_x*GRID_CELL_SIZE, pos_y*GRID_CELL_SIZE, GRID_CELL_SIZE, GRID_CELL_SIZE)
        pygame.draw.rect(game_window, BLUE, position_rect, 2)

    pygame.display.update()

pygame.quit()
sys.exit()