import pygame
import sys
import json
import random
import heapq
import time
import os
from collections import deque

pygame.init()

WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Racetrack Pathfinder")

GRID_SIZE = 20
GRID_WIDTH = WIDTH // GRID_SIZE
GRID_HEIGHT = HEIGHT // GRID_SIZE

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 200, 0)
PURPLE = (160, 32, 240)
LIGHT_GRAY = (220, 220, 220)

TILE_TYPES = {
    'out_of_bounds': 0,
    'road': 1,
    'start_finish': 2,
    'checkpoint1': 3,
    'checkpoint2': 4
}

TILE_COLORS = {
    0: BLACK,
    1: WHITE,
    2: GREEN,
    3: BLUE,
    4: PURPLE
}

# Initialize track and game state
track_grid = []
checkpoint1_group = []
checkpoint2_group = []
car_x, car_y = 0, 0
car_vx, car_vy = 0, 0
running = True
animating = False
animation_steps = 10
current_step = 0
computed_path = []
moves_made = 0
required_laps = 1

class State:
    def __init__(self, x, y, vx, vy, cp1, cp2, lap):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.cp1 = cp1  
        self.cp2 = cp2  
        self.lap = lap

    def __lt__(self, other):
        return False  

def load_track(filename):
    global track_grid, checkpoint1_group, checkpoint2_group, cp1_centroid, cp2_centroid, finish_centroid, start_positions
    try:
        with open(filename, 'r') as f:
            track_grid = json.load(f)
        print(f"Track loaded from {filename}")
        
        visited = [[False for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if track_grid[y][x] == TILE_TYPES['checkpoint1'] and not visited[y][x]:
                    checkpoint1_group = bfs((x, y), TILE_TYPES['checkpoint1'], visited)
                    break
            if checkpoint1_group:
                break
        
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if track_grid[y][x] == TILE_TYPES['checkpoint2'] and not visited[y][x]:
                    checkpoint2_group = bfs((x, y), TILE_TYPES['checkpoint2'], visited)
                    break
            if checkpoint2_group:
                break

        start_positions = find_start_positions()
        
        if not checkpoint1_group or not checkpoint2_group:
            print("Two checkpoint groups required")
            sys.exit()
        else:
            print(f"Checkpoint1: {len(checkpoint1_group)} tiles")
            print(f"Checkpoint2: {len(checkpoint2_group)} tiles")
            cp1_centroid = (sum(x for x, y in checkpoint1_group)/len(checkpoint1_group), 
                sum(y for x, y in checkpoint1_group)/len(checkpoint1_group))
            cp2_centroid = (sum(x for x, y in checkpoint2_group)/len(checkpoint2_group), 
                            sum(y for x, y in checkpoint2_group)/len(checkpoint2_group))
            finish_centroid = (sum(x for x, y in start_positions) / len(start_positions),
                                sum(y for x, y in start_positions) / len(start_positions) )

        
            
    except FileNotFoundError:
        print(f"File {filename} not found.")
        sys.exit()

def bfs(start_pos, tile_type, visited):
    queue = [start_pos]
    connected = []
    while queue:
        x, y = queue.pop(0)
        if visited[y][x]:
            continue
        visited[y][x] = True
        if track_grid[y][x] == tile_type:
            connected.append((x, y))
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = x+dx, y+dy
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    if not visited[ny][nx] and track_grid[ny][nx] == tile_type:
                        queue.append((nx, ny))
    return connected

def find_start_positions():
    return [(x, y) for y in range(GRID_HEIGHT) for x in range(GRID_WIDTH)
            if track_grid[y][x] == TILE_TYPES['start_finish']]

def bresenham_line(x0, y0, x1, y1):
    points = []
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = -1 if x0 > x1 else 1
    sy = -1 if y0 > y1 else 1
    err = dx - dy
    
    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return points

def is_move_valid(x0, y0, x1, y1):
    for x, y in bresenham_line(x0, y0, x1, y1):
        if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT) or \
           track_grid[y][x] == TILE_TYPES['out_of_bounds']:
            return False, []
    
    crossed = []
    for x, y in bresenham_line(x0, y0, x1, y1):
        tile = track_grid[y][x]
        if tile == TILE_TYPES['checkpoint1']:
            crossed.append(('cp1', (x,y)))
        elif tile == TILE_TYPES['checkpoint2']:
            crossed.append(('cp2', (x,y)))
        elif tile == TILE_TYPES['start_finish']:
            crossed.append(('finish', (x,y)))
    return True, crossed

# Manhattan Distance to target
def heuristic1(x, y, target_x, target_y):
    return abs(target_x - x) + abs(target_y - y)

# Manhattan Distance to finish line
def heuristic2(x, y, target_x, target_y):
    start_finish_x, start_finish_y = start_positions[0]
    return abs(start_finish_x - x) + abs(start_finish_y - y)

# Chebyshev Distance to target
def heuristic3(x, y, target_x, target_y):
    return max(abs(target_x - x), abs(target_y - y))

# Chebyshev Distance to finish line
def heuristic4(x, y, target_x, target_y):
    start_finish_x, start_finish_y = start_positions[0]
    return max(abs(start_finish_x - x), abs(start_finish_y - y))

# Euclidean Distance to target
def heuristic5(x, y, target_x, target_y):
    dx = target_x - x
    dy = target_y - y
    return (dx**2 + dy**2)**0.5

# Euclidean Distance to finish line
def heuristic6(x, y, target_x, target_y):
    start_finish_x, start_finish_y = start_positions[0]
    dx = start_finish_x - x
    dy = start_finish_y - y
    return (dx**2 + dy**2)**0.5

def get_target(state):
    if state.lap > required_laps:
        return None
    
    if not state.cp1:
        return cp1_centroid  
    elif not state.cp2:
        return cp2_centroid  
    else:
        return finish_centroid  
    

def render_results(screen, all_results):
    pygame.font.init()
    title_font = pygame.font.Font(None, 48)
    header_font = pygame.font.Font(None, 36)
    text_font = pygame.font.Font(None, 28)
    
    TITLE_COLOR = (50, 50, 50)
    HEADER_COLOR = (80, 80, 80)
    TEXT_COLOR = (100, 100, 100)
    BG_COLOR = (240, 240, 240)
    
    total_height = 150
    total_height += len(all_results) * 40
    total_height += 90
    
    for _ in all_results:
        total_height += 150
    
    total_height += 100
    
    content_surface = pygame.Surface((WIDTH, total_height))
    content_surface.fill(BG_COLOR)
    
    title = title_font.render("Heuristic Performance Results", True, TITLE_COLOR)
    content_surface.blit(title, (WIDTH//2 - title.get_width()//2, 20))
    
    instructions = text_font.render("Press T to sort by Time, M to sort by Moves, ESC to return to menu", True, TEXT_COLOR)
    content_surface.blit(instructions, (WIDTH//2 - instructions.get_width()//2, 50))
    
    headers = ["Heuristic", "Success Rate", "Avg Time (s)", "Avg Moves"]
    header_y = 80
    x_positions = [50, 300, 500, 700]
    for header, x in zip(headers, x_positions):
        header_text = header_font.render(header, True, HEADER_COLOR)
        content_surface.blit(header_text, (x, header_y))
    
    def sort_results(results, sort_by='time'):
        if sort_by == 'time':
            return sorted(results.items(), key=lambda x: x[1]['avg_time'])
        else:  
            return sorted(results.items(), key=lambda x: x[1]['avg_moves'])
    
    sort_mode = 'time'
    sorted_results = sort_results(all_results, sort_mode)
    
    def render_content():
        content_surface.fill(BG_COLOR)
        
        content_surface.blit(title, (WIDTH//2 - title.get_width()//2, 20))
        content_surface.blit(instructions, (WIDTH//2 - instructions.get_width()//2, 50))
        for header, x in zip(headers, x_positions):
            header_text = header_font.render(header, True, HEADER_COLOR)
            content_surface.blit(header_text, (x, header_y))
        
        y = header_y + 50
        for heuristic_name, results in sorted_results:
            name_text = text_font.render(heuristic_name, True, TEXT_COLOR)
            content_surface.blit(name_text, (50, y))
            
            success_text = text_font.render(f"{results['success_rate']:.1f}%", True, TEXT_COLOR)
            content_surface.blit(success_text, (300, y))
            
            time_text = text_font.render(f"{results['avg_time']:.3f}", True, TEXT_COLOR)
            content_surface.blit(time_text, (500, y))
            
            moves_text = text_font.render(f"{results['avg_moves']:.1f}", True, TEXT_COLOR)
            content_surface.blit(moves_text, (700, y))
            
            y += 40
        
        y += 40
        detail_title = header_font.render("Detailed Statistics", True, HEADER_COLOR)
        content_surface.blit(detail_title, (50, y))
        y += 50
        
        for heuristic_name, results in sorted_results:
            algo_header = header_font.render(heuristic_name, True, HEADER_COLOR)
            content_surface.blit(algo_header, (50, y))
            y += 30
            
            stats = [
                f"Success Rate: {results['success_rate']:.1f}%",
                f"Average Time: {results['avg_time']:.3f} seconds",
                f"Average Moves: {results['avg_moves']:.1f}"
            ]
            
            successful_times = [t for t in results['raw_times'] if t is not None]
            if successful_times:
                stats.extend([
                    f"Best Time: {min(successful_times):.3f} seconds",
                    f"Worst Time: {max(successful_times):.3f} seconds"
                ])
            
            for stat in stats:
                stat_text = text_font.render(stat, True, TEXT_COLOR)
                content_surface.blit(stat_text, (70, y))
                y += 25
            
            y += 20
    
    render_content()
    
    scroll_y = 0
    scroll_speed = 50
    
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False  
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True  
                elif event.key == pygame.K_UP:
                    scroll_y = max(0, scroll_y - scroll_speed)
                elif event.key == pygame.K_DOWN:
                    scroll_y = min(total_height - HEIGHT, scroll_y + scroll_speed)
                elif event.key == pygame.K_t:  
                    sort_mode = 'time'
                    sorted_results = sort_results(all_results, sort_mode)
                    render_content()
                elif event.key == pygame.K_m:  
                    sort_mode = 'moves'
                    sorted_results = sort_results(all_results, sort_mode)
                    render_content()
            elif event.type == pygame.MOUSEWHEEL:
                scroll_y = max(0, min(total_height - HEIGHT, scroll_y - event.y * scroll_speed))
        
        screen.fill(BG_COLOR)
        
        screen.blit(content_surface, (0, -scroll_y))
        
        if total_height > HEIGHT:
            if scroll_y > 0:
                pygame.draw.polygon(screen, HEADER_COLOR, [(WIDTH-30, 20), (WIDTH-20, 10), (WIDTH-10, 20)])
            if scroll_y < total_height - HEIGHT:
                pygame.draw.polygon(screen, HEADER_COLOR, [(WIDTH-30, HEIGHT-20), (WIDTH-20, HEIGHT-10), (WIDTH-10, HEIGHT-20)])
        
        pygame.display.flip()
        clock.tick(60)
    
    return True  

def show_loading_screen(screen, message):
    screen.fill((0, 0, 0))  
    font = pygame.font.Font(None, 36)
    text = font.render(message, True, (255, 255, 255))  
    text_rect = text.get_rect(center=(WIDTH/2, HEIGHT/2))
    screen.blit(text, text_rect)
    pygame.display.flip()

def get_available_tracks():
    tracks = []
    for file in os.listdir():
        if file.endswith('.json'):
            tracks.append(file)
    return tracks

def select_track():
    tracks = get_available_tracks()
    if not tracks:
        print("No track files found!")
        return None
        
    font = pygame.font.Font(None, 36)
    title_font = pygame.font.Font(None, 48)
    
    buttons = []
    button_height = 50
    button_width = 300
    start_y = 200
    spacing = 20
    
    for i, track in enumerate(tracks):
        y = start_y + i * (button_height + spacing)
        buttons.append({
            'rect': pygame.Rect(WIDTH//2 - button_width//2, y, button_width, button_height),
            'text': track,
            'color': LIGHT_GRAY,
            'hover_color': WHITE
        })
    
    back_button = {
        'rect': pygame.Rect(20, 20, 100, 40),
        'text': "Back",
        'color': LIGHT_GRAY,
        'hover_color': WHITE
    }
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: 
                    mouse_clicked = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
        
        screen.fill(WHITE)
        
        title = title_font.render("Select Track", True, BLACK)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        
        instructions = font.render("Click a track to select, or press ESC to go back", True, GRAY)
        screen.blit(instructions, (WIDTH//2 - instructions.get_width()//2, 150))
        
        back_hovered = back_button['rect'].collidepoint(mouse_pos)
        pygame.draw.rect(screen, back_button['hover_color'] if back_hovered else back_button['color'], back_button['rect'])
        pygame.draw.rect(screen, BLACK, back_button['rect'], 2)
        back_text = font.render(back_button['text'], True, BLACK)
        screen.blit(back_text, (back_button['rect'].centerx - back_text.get_width()//2,
                               back_button['rect'].centery - back_text.get_height()//2))
        
        if back_hovered and mouse_clicked:
            return None
        
        for button in buttons:
            hovered = button['rect'].collidepoint(mouse_pos)
            pygame.draw.rect(screen, button['hover_color'] if hovered else button['color'], button['rect'])
            pygame.draw.rect(screen, BLACK, button['rect'], 2)
            text = font.render(button['text'], True, BLACK)
            screen.blit(text, (button['rect'].centerx - text.get_width()//2,
                              button['rect'].centery - text.get_height()//2))
            
            if hovered and mouse_clicked:
                return button['text']
        
        pygame.display.flip()
    
    return None

def test_heuristics():
    heuristics = {
        "Manhattan to Target": heuristic1,
        "Manhattan to Finish": heuristic2,
        "Chebyshev to Target": heuristic3,
        "Chebyshev to Finish": heuristic4,
        "Euclidean to Target": heuristic5,
        "Euclidean to Finish": heuristic6
    }
    
    pathfinder = compute_optimal_path_heap
    
    track_filename = select_track()
    if not track_filename:
        return
    
    laps = 1
    num_trials = 1
    
    show_loading_screen(screen, "Loading track and initializing tests...")
    
    load_track(track_filename)  
    start_positions = find_start_positions()
    if not start_positions:
        print("No start positions found.")
        return
    
    start_x, start_y = start_positions[0]
    
    all_results = {}
    
    for heuristic_name, heuristic_func in heuristics.items():
        show_loading_screen(screen, f"Testing {heuristic_name}...")
        
        times = []
        moves = []
        successes = 0
        
        for trial in range(num_trials):
            def modified_pathfinder(start_x, start_y, laps):
                heap = []
                initial_state = State(start_x, start_y, 0, 0, False, False, 1)
                heapq.heappush(heap, (0, initial_state))
                
                visited = {}
                came_from = {}
                
                while heap:
                    cost, current = heapq.heappop(heap)
                    
                    if current.lap > laps:
                        path = []
                        while current in came_from:
                            path.append((current.x, current.y))
                            current = came_from[current]
                        path.append((start_x, start_y))
                        path.reverse()
                        return path
                    
                    state_key = (current.x, current.y, current.vx, current.vy, current.cp1, current.cp2, current.lap)
                    if state_key in visited and visited[state_key] <= cost:
                        continue
                    visited[state_key] = cost
                    
                    for dvx in (-1, 0, 1):
                        for dvy in (-1, 0, 1):
                            new_vx = current.vx + dvx
                            new_vy = current.vy + dvy
                            new_x = current.x + new_vx
                            new_y = current.y + new_vy
                            
                            if not (0 <= new_x < GRID_WIDTH and 0 <= new_y < GRID_HEIGHT):
                                continue
                            
                            valid, crossed = is_move_valid(current.x, current.y, new_x, new_y)
                            if not valid:
                                continue
                            
                            cp1 = current.cp1
                            cp2 = current.cp2
                            lap = current.lap
                            for c in crossed:
                                if c[0] == 'cp1' and not cp1 and c[1] in checkpoint1_group:
                                    cp1 = True
                                elif c[0] == 'cp2' and cp1 and not cp2 and c[1] in checkpoint2_group:
                                    cp2 = True
                                elif c[0] == 'finish':
                                    if cp1 and cp2:
                                        lap += 1
                                        cp1 = False
                                        cp2 = False
                                    else:
                                        cp1 = False
                                        cp2 = False
                            
                            new_state = State(new_x, new_y, new_vx, new_vy, cp1, cp2, lap)
                            new_cost = cost + 1

                            target = get_target(new_state)
                            if target is None:
                                target_x, target_y = finish_centroid  
                            else:
                                target_x, target_y = target
                            
                            new_state_key = (new_state.x, new_state.y, new_state.vx, new_state.vy, new_state.cp1, new_state.cp2, new_state.lap)
                            if new_state_key not in visited or new_cost < visited[new_state_key]:
                                h_value = heuristic_func(new_x, new_y, target_x, target_y)
                                priority = new_cost + h_value
                                heapq.heappush(heap, (priority, new_state))
                                came_from[new_state] = current
                return None
            
            start_time = time.time()
            path = modified_pathfinder(start_x, start_y, laps)
            duration = time.time() - start_time
            
            if path:
                successes += 1
                times.append(duration)
                moves.append(len(path) - 1)
            else:
                times.append(None)
                moves.append(None)
        
        if successes > 0:
            avg_time = sum(t for t in times if t is not None) / successes
            avg_moves = sum(m for m in moves if m is not None) / successes
            success_rate = (successes / num_trials) * 100
        else:
            avg_time = float('inf')
            avg_moves = float('inf')
            success_rate = 0
            
        all_results[heuristic_name] = {
            "avg_time": avg_time,
            "avg_moves": avg_moves,
            "success_rate": success_rate,
            "raw_times": times,
            "raw_moves": moves
        }
    
    show_loading_screen(screen, "Preparing results display...")
    
    running = render_results(screen, all_results)
    
    if running:
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    waiting = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        waiting = False

def calculate_priority(new_cost, new_state, new_x, new_y, target_x, target_y, heuristic_func=None, dvx=None, dvy=None):
    if heuristic_func is None:
        heuristic_func = heuristic1
        
    h_value = heuristic_func(new_x, new_y, target_x, target_y)
    return new_cost + h_value

def compute_optimal_path_heap(start_x, start_y, laps):
    heap = []
    initial_state = State(start_x, start_y, 0, 0, False, False, 1)
    heapq.heappush(heap, (0, initial_state))

    
    
    visited = {}
    came_from = {}
    
    while heap:
        cost, current = heapq.heappop(heap)
        
        if current.lap > laps:
            path = []
            while current in came_from:
                path.append((current.x, current.y))
                current = came_from[current]
            path.append((start_x, start_y))
            path.reverse()
            return path
        
        state_key = (current.x, current.y, current.vx, current.vy, current.cp1, current.cp2, current.lap)
        if state_key in visited and visited[state_key] <= cost:
            continue
        visited[state_key] = cost
        

        for dvx in (-1, 0, 1):
            for dvy in (-1, 0, 1):
                new_vx = current.vx + dvx
                new_vy = current.vy + dvy
                new_x = current.x + new_vx
                new_y = current.y + new_vy
                
                if not (0 <= new_x < GRID_WIDTH and 0 <= new_y < GRID_HEIGHT):
                    continue
                
                valid, crossed = is_move_valid(current.x, current.y, new_x, new_y)
                if not valid:
                    continue
                
                cp1 = current.cp1
                cp2 = current.cp2
                lap = current.lap
                for c in crossed:
                    if c[0] == 'cp1' and not cp1 and c[1] in checkpoint1_group:
                        cp1 = True
                    elif c[0] == 'cp2' and cp1 and not cp2 and c[1] in checkpoint2_group:
                        cp2 = True

                    elif c[0] == 'finish':
                        if cp1 and cp2:
                            lap += 1
                            cp1 = False
                            cp2 = False
                        else:
                            cp1 = False
                            cp2 = False
                
                new_state = State(new_x, new_y, new_vx, new_vy, cp1, cp2, lap)
                new_cost = cost + 1

                target = get_target(new_state)
                if target is None:
                    target_x, target_y = finish_centroid  
                else:
                    target_x, target_y = target
                
                new_state_key = (new_state.x, new_state.y, new_state.vx, new_state.vy, new_state.cp1, new_state.cp2, new_state.lap)
                if new_state_key not in visited or new_cost < visited[new_state_key]:
                    priority = calculate_priority(new_cost, new_state, new_x, new_y, target_x, target_y, dvx=dvx, dvy=dvy)
                    heapq.heappush(heap, (priority, new_state))
                    came_from[new_state] = current
    return None

