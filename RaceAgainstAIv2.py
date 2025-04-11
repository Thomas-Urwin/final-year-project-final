import pygame
import sys
import json
import random
import heapq
import time
import copy
import os

# Initialize Pygame
pygame.init()

# Game Window Settings
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
game_window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Race Against AI")

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

class Game:
    def __init__(self):
        self.track_layout = []
        self.checkpoint1_group = []
        self.checkpoint2_group = []
        self.cp1_centroid = None
        self.cp2_centroid = None
        self.finish_centroid = None
        
        # Player state
        self.player_x = 0
        self.player_y = 0
        self.player_vx = 0
        self.player_vy = 0
        self.player_cp1 = False
        self.player_cp2 = False
        self.player_lap = 1
        self.player_path_history = []
        self.player_position_markers = []
        self.player_moves = 0
        self.player_has_won = False
        
        # AI state
        self.ai_x = 0
        self.ai_y = 0
        self.ai_vx = 0
        self.ai_vy = 0
        self.ai_cp1 = False
        self.ai_cp2 = False
        self.ai_lap = 1
        self.ai_path_history = []
        self.ai_position_markers = []
        self.ai_moves = 0
        self.ai_has_won = False
        
        # Animation state
        self.is_animating = False
        self.animation_steps = 10
        self.current_step = 0
        self.animation_start = None
        self.animation_end = None
        self.is_player_turn = True
        
        # Game state
        self.game_running = True
        self.required_laps = 1
        self.ai_path = []
        self.ai_path_index = 0
        self.game_over_reason = None
        self.show_stats = False
        self.game_start_time = None
        self.show_ai_path = True  
        
        # Path recalculation
        self.is_recalculating_path = False
        self.show_recalculating_message = False
        self.recalculation_message_timer = 0
        self.recalculation_message_duration = 60  
        
        # Blocked message state
        self.show_blocked_message = False
        self.blocked_message_timer = 0
        self.blocked_message_duration = 60 
        
        # Colors for AI
        self.AI_COLOR = (255, 140, 0)  
        self.AI_PATH_COLOR = (255, 165, 0)  
        self.AI_MARKER_COLOR = (255, 69, 0)  

    def show_loading_screen(self, message):
        game_window.fill(BLACK)
        font = pygame.font.Font(None, 48)
        text = font.render(message, True, WHITE)
        text_rect = text.get_rect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2))
        game_window.blit(text, text_rect)
        pygame.display.flip()

    def load_track(self, filename):
        try:
            with open(filename, 'r') as f:
                self.track_layout = json.load(f)
            print(f"Track loaded from {filename}")
            
            self.show_loading_screen("Loading track...")
            
            visited = [[False for _ in range(GRID_COLUMNS)] for _ in range(GRID_ROWS)]
            
            for y in range(GRID_ROWS):
                for x in range(GRID_COLUMNS):
                    if self.track_layout[y][x] == TRACK_TILE_TYPES['checkpoint1'] and not visited[y][x]:
                        self.checkpoint1_group = self.find_connected_checkpoints((x, y), TRACK_TILE_TYPES['checkpoint1'], visited)
                        break
                if self.checkpoint1_group:
                    break
            
            for y in range(GRID_ROWS):
                for x in range(GRID_COLUMNS):
                    if self.track_layout[y][x] == TRACK_TILE_TYPES['checkpoint2'] and not visited[y][x]:
                        self.checkpoint2_group = self.find_connected_checkpoints((x, y), TRACK_TILE_TYPES['checkpoint2'], visited)
                        break
                if self.checkpoint2_group:
                    break
            
            if self.checkpoint1_group:
                self.cp1_centroid = (sum(x for x, y in self.checkpoint1_group)/len(self.checkpoint1_group),
                                   sum(y for x, y in self.checkpoint1_group)/len(self.checkpoint1_group))
            if self.checkpoint2_group:
                self.cp2_centroid = (sum(x for x, y in self.checkpoint2_group)/len(self.checkpoint2_group),
                                   sum(y for x, y in self.checkpoint2_group)/len(self.checkpoint2_group))
            
            start_positions = self.find_start_positions()
            if not start_positions:
                print("No starting positions found!")
                sys.exit()
            
            self.finish_centroid = (sum(x for x, y in start_positions)/len(start_positions),
                                  sum(y for x, y in start_positions)/len(start_positions))
            
            start_pos = random.choice(start_positions)
            self.player_x, self.player_y = start_pos
            self.player_path_history = [(self.player_x, self.player_y)]
            self.player_position_markers = [(self.player_x, self.player_y)]
            
            remaining_positions = [pos for pos in start_positions if pos != start_pos]
            ai_start = random.choice(remaining_positions) if remaining_positions else start_pos
            self.ai_x, self.ai_y = ai_start
            self.ai_path_history = [(self.ai_x, self.ai_y)]
            self.ai_position_markers = [(self.ai_x, self.ai_y)]
            
            self.show_loading_screen("AI is calculating optimal route...")
            
            self.ai_path = self.compute_optimal_path(self.ai_x, self.ai_y)
            if not self.ai_path:
                print("No valid path found for AI!")
                sys.exit()
            
        except FileNotFoundError:
            print(f"File {filename} not found.")
            sys.exit()

    def find_connected_checkpoints(self, start_pos, tile_type, visited):
        queue = [start_pos]
        connected = []
        while queue:
            x, y = queue.pop(0)
            if visited[y][x]:
                continue
            visited[y][x] = True
            if self.track_layout[y][x] == tile_type:
                connected.append((x, y))
                for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < GRID_COLUMNS and 0 <= ny < GRID_ROWS:
                        if not visited[ny][nx] and self.track_layout[ny][nx] == tile_type:
                            queue.append((nx, ny))
        return connected

    def find_start_positions(self):
        return [(x, y) for y in range(GRID_ROWS) for x in range(GRID_COLUMNS)
                if self.track_layout[y][x] == TRACK_TILE_TYPES['start_finish']]

    def euclidean_distance(self, x1, y1, x2, y2):
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

    def get_target(self, state):
        if state.lap > self.required_laps:
            return None
        if not state.cp1:
            return self.cp1_centroid
        elif not state.cp2:
            return self.cp2_centroid
        else:
            return self.finish_centroid

    def calculate_priority(self, cost, state, x, y, target_x, target_y):
        return cost + self.euclidean_distance(x, y, target_x, target_y)

    def is_move_valid(self, x0, y0, x1, y1):
        for x, y in self.bresenham_line(x0, y0, x1, y1):
            if not (0 <= x < GRID_COLUMNS and 0 <= y < GRID_ROWS) or \
               self.track_layout[y][x] == TRACK_TILE_TYPES['out_of_bounds']:
                return False, []
        
        crossed = []
        for x, y in self.bresenham_line(x0, y0, x1, y1):
            tile = self.track_layout[y][x]
            if tile == TRACK_TILE_TYPES['checkpoint1']:
                crossed.append(('cp1', (x,y)))
            elif tile == TRACK_TILE_TYPES['checkpoint2']:
                crossed.append(('cp2', (x,y)))
            elif tile == TRACK_TILE_TYPES['start_finish']:
                crossed.append(('finish', (x,y)))
        return True, crossed

    def bresenham_line(self, x0, y0, x1, y1):
        points = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        sx = -1 if x0 > x1 else 1
        sy = -1 if y0 > y1 else 1
        
        if dx > dy:
            err = dx / 2.0
            while x != x1:
                points.append((x, y))
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
        else:
            err = dy / 2.0
            while y != y1:
                points.append((x, y))
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy
                
        points.append((x1, y1))
        return points

    def compute_optimal_path(self, start_x, start_y):
        heap = []
        initial_state = State(start_x, start_y, 0, 0, False, False, 1)
        heapq.heappush(heap, (0, initial_state))
        
        visited = {}
        came_from = {}
        
        while heap:
            cost, current = heapq.heappop(heap)
            
            if current.lap > self.required_laps:
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
                    
                    if not (0 <= new_x < GRID_COLUMNS and 0 <= new_y < GRID_ROWS):
                        continue
                    
                    valid, crossed = self.is_move_valid(current.x, current.y, new_x, new_y)
                    if not valid:
                        continue
                    
                    cp1 = current.cp1
                    cp2 = current.cp2
                    lap = current.lap
                    
                    for c in crossed:
                        if c[0] == 'cp1' and not cp1 and c[1] in self.checkpoint1_group:
                            cp1 = True
                        elif c[0] == 'cp2' and cp1 and not cp2 and c[1] in self.checkpoint2_group:
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
                    
                    target = self.get_target(new_state)
                    if target is None:
                        target_x, target_y = self.finish_centroid
                    else:
                        target_x, target_y = target
                    
                    new_state_key = (new_x, new_y, new_vx, new_vy, cp1, cp2, lap)
                    if new_state_key not in visited or new_cost < visited[new_state_key]:
                        priority = self.calculate_priority(new_cost, new_state, new_x, new_y, target_x, target_y)
                        heapq.heappush(heap, (priority, new_state))
                        came_from[new_state] = current
        
        return None

    def process_move(self, x, y, vx, vy, is_player):
        if is_player:
            state_vars = (self.player_cp1, self.player_cp2, self.player_lap)
        else:
            state_vars = (self.ai_cp1, self.ai_cp2, self.ai_lap)
        
        cp1, cp2, lap = state_vars
        _, crossed = self.is_move_valid(x, y, x + vx, y + vy)
        
        for c in crossed:
            if c[0] == 'cp1' and not cp1 and c[1] in self.checkpoint1_group:
                cp1 = True
            elif c[0] == 'cp2' and cp1 and not cp2 and c[1] in self.checkpoint2_group:
                cp2 = True
            elif c[0] == 'finish':
                if cp1 and cp2:
                    lap += 1
                    if lap > self.required_laps:
                        if is_player:
                            self.player_has_won = True
                        else:
                            self.ai_has_won = True
                    cp1 = False
                    cp2 = False
                else:
                    cp1 = False
                    cp2 = False
        
        if is_player:
            self.player_cp1, self.player_cp2, self.player_lap = cp1, cp2, lap
        else:
            self.ai_cp1, self.ai_cp2, self.ai_lap = cp1, cp2, lap
        
        return self.player_has_won or self.ai_has_won

    def handle_player_move(self, mouse_pos):
        if self.is_animating:
            return
        
        clicked_x = mouse_pos[0] // GRID_CELL_SIZE
        clicked_y = mouse_pos[1] // GRID_CELL_SIZE
        
        possible_moves = []
        for dvx in (-1, 0, 1):
            for dvy in (-1, 0, 1):
                new_vx = self.player_vx + dvx
                new_vy = self.player_vy + dvy
                new_x = self.player_x + new_vx
                new_y = self.player_y + new_vy
                
                if 0 <= new_x < GRID_COLUMNS and 0 <= new_y < GRID_ROWS:
                    valid, crossed = self.is_move_valid(self.player_x, self.player_y, new_x, new_y)
                    if valid and not self.would_collide_with_ai(self.player_x, self.player_y, new_x, new_y):
                        possible_moves.append((new_x, new_y, new_vx, new_vy, crossed))
        
        for move in possible_moves:
            new_x, new_y, new_vx, new_vy, _ = move
            if clicked_x == new_x and clicked_y == new_y:
                self.is_animating = True
                self.current_step = 0
                self.animation_start = (self.player_x, self.player_y)
                self.animation_end = (new_x, new_y)
                self.player_vx = new_vx
                self.player_vy = new_vy
                break

    def has_valid_moves(self):
        for dvx in (-1, 0, 1):
            for dvy in (-1, 0, 1):
                new_vx = self.player_vx + dvx
                new_vy = self.player_vy + dvy
                new_x = self.player_x + new_vx
                new_y = self.player_y + new_vy
                
                if 0 <= new_x < GRID_COLUMNS and 0 <= new_y < GRID_ROWS:
                    valid, _ = self.is_move_valid(self.player_x, self.player_y, new_x, new_y)
                    if valid:
                        return True
        return False

    def update(self):
        if self.is_animating:
            self.current_step += 1
            if self.current_step >= self.animation_steps:
                self.is_animating = False
                
                if self.is_player_turn:
                    self.player_x, self.player_y = self.animation_end
                    self.player_path_history.append((self.player_x, self.player_y))
                    self.player_position_markers.append((self.player_x, self.player_y))
                    self.player_moves += 1
                    
                    game_over = self.process_move(self.player_x - self.player_vx, self.player_y - self.player_vy, 
                                                self.player_vx, self.player_vy, True)
                    
                    if game_over:
                        pygame.time.wait(500) 
                        self.game_running = False
                        self.game_over_reason = "Race Complete!" if self.player_has_won else "AI Wins!"
                        self.show_stats = True
                    elif not self.has_valid_moves():
                        self.game_running = False
                        self.game_over_reason = "No Valid Moves - Crashed!"
                        self.show_stats = True
                    else:
                        self.is_player_turn = False
                        
                        if self.is_player_on_ai_path():
                            self.is_recalculating_path = True
                            self.show_recalculating_message = True
                            self.recalculation_message_timer = 0
                else:
                    self.ai_x, self.ai_y = self.animation_end
                    self.ai_path_history.append((self.ai_x, self.ai_y))
                    self.ai_position_markers.append((self.ai_x, self.ai_y))
                    self.ai_moves += 1
                    
                    game_over = self.process_move(self.ai_x - self.ai_vx, self.ai_y - self.ai_vy, 
                                                self.ai_vx, self.ai_vy, False)
                    
                    self.is_player_turn = True
                    self.ai_path_index += 1
                    
                    if game_over:
                        pygame.time.wait(500)  
                        self.game_running = False
                        self.game_over_reason = "AI Wins!" if self.ai_has_won else "Race Complete!"
                        self.show_stats = True
        
        if self.show_recalculating_message:
            self.recalculation_message_timer += 1
            if self.recalculation_message_timer >= self.recalculation_message_duration:
                self.show_recalculating_message = False
            
        if self.is_recalculating_path:
            temp_track = copy.deepcopy(self.track_layout)
            temp_track[self.player_y][self.player_x] = TRACK_TILE_TYPES['out_of_bounds']
            
            original_track = self.track_layout
            self.track_layout = temp_track
            
            new_path = self.compute_optimal_path(self.ai_x, self.ai_y)
            
            self.track_layout = original_track
            
            if new_path:
                self.ai_path = self.ai_path[:self.ai_path_index] + new_path
                self.ai_path_index = min(self.ai_path_index, len(self.ai_path) - 1)
            
            self.is_recalculating_path = False
            
        if not self.is_animating and not self.is_recalculating_path and self.game_running:
            if self.is_player_turn:
                if not self.has_valid_moves_considering_opponent(True):
                    self.is_player_turn = False
                    self.show_blocked_message = True
                    self.blocked_message_timer = 0
            else:
                if not self.has_valid_moves_considering_opponent(False):
                    self.is_player_turn = True
                    self.show_blocked_message = True
                    self.blocked_message_timer = 0
            
        if not self.is_player_turn and not self.is_animating and not self.is_recalculating_path and self.ai_path_index < len(self.ai_path) - 1:
            next_pos = self.ai_path[self.ai_path_index + 1]
            self.ai_vx = next_pos[0] - self.ai_x
            self.ai_vy = next_pos[1] - self.ai_y
            
            if not (next_pos[0] == self.player_x and next_pos[1] == self.player_y) and \
               not any(p == (self.player_x, self.player_y) for p in self.bresenham_line(self.ai_x, self.ai_y, next_pos[0], next_pos[1])):
                self.is_animating = True
                self.current_step = 0
                self.animation_start = (self.ai_x, self.ai_y)
                self.animation_end = next_pos
            else:
                self.is_recalculating_path = True
                self.show_recalculating_message = True
                self.recalculation_message_timer = 0

    def draw_stats_screen(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(200)
        game_window.blit(overlay, (0, 0))

        title_font = pygame.font.Font(None, 74)
        text_font = pygame.font.Font(None, 48)

        TITLE_COLOR = (255, 0, 0)
        TEXT_COLOR = (255, 255, 255)

        if self.game_over_reason == "Race Complete!":
            winner_text = "Player Wins!"
            moves = self.player_moves
        elif self.game_over_reason == "AI Wins!":
            winner_text = "AI Wins!"
            moves = self.ai_moves
        else:
            winner_text = "Game Over - Crashed!"
            moves = self.player_moves

        winner = title_font.render(winner_text, True, TITLE_COLOR)
        winner_rect = winner.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 50))
        game_window.blit(winner, winner_rect)

        if winner_text != "Game Over - Crashed!":
            moves_text = text_font.render(f"Moves: {moves}", True, TEXT_COLOR)
            moves_rect = moves_text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + 30))
            game_window.blit(moves_text, moves_rect)

        exit_text = text_font.render("Press any key to exit", True, TEXT_COLOR)
        exit_rect = exit_text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT - 100))
        game_window.blit(exit_text, exit_rect)

    def draw(self):
        game_window.fill(WHITE)
        
        for y in range(GRID_ROWS):
            for x in range(GRID_COLUMNS):
                tile_value = self.track_layout[y][x]
                color = TILE_COLORS.get(tile_value, WHITE)
                rect = pygame.Rect(x * GRID_CELL_SIZE, y * GRID_CELL_SIZE, 
                                 GRID_CELL_SIZE, GRID_CELL_SIZE)
                pygame.draw.rect(game_window, color, rect)
                
                if color == WHITE or color == LIGHT_GRAY:
                    grid_color = GRAY
                elif color == GREEN:
                    grid_color = (0, 100, 0) 
                elif color == RED:
                    grid_color = (139, 0, 0)  
                else:
                    grid_color = color
                
                pygame.draw.rect(game_window, grid_color, rect, 1)  
        
        if self.is_player_turn and not self.is_animating and self.game_running:
            for dvx in (-1, 0, 1):
                for dvy in (-1, 0, 1):
                    new_vx = self.player_vx + dvx
                    new_vy = self.player_vy + dvy
                    new_x = self.player_x + new_vx
                    new_y = self.player_y + new_vy
                    
                    if 0 <= new_x < GRID_COLUMNS and 0 <= new_y < GRID_ROWS:
                        valid, _ = self.is_move_valid(self.player_x, self.player_y, new_x, new_y)
                        if valid:
                            rect = pygame.Rect(new_x * GRID_CELL_SIZE, new_y * GRID_CELL_SIZE, 
                                             GRID_CELL_SIZE, GRID_CELL_SIZE)
                            
                            if self.would_collide_with_ai(self.player_x, self.player_y, new_x, new_y):
                                pygame.draw.rect(game_window, (255, 200, 200), rect)  
                                pygame.draw.line(game_window, (255, 0, 0), 
                                               (new_x * GRID_CELL_SIZE + 5, new_y * GRID_CELL_SIZE + 5),
                                               (new_x * GRID_CELL_SIZE + GRID_CELL_SIZE - 5, new_y * GRID_CELL_SIZE + GRID_CELL_SIZE - 5), 3)
                                pygame.draw.line(game_window, (255, 0, 0), 
                                               (new_x * GRID_CELL_SIZE + GRID_CELL_SIZE - 5, new_y * GRID_CELL_SIZE + 5),
                                               (new_x * GRID_CELL_SIZE + 5, new_y * GRID_CELL_SIZE + GRID_CELL_SIZE - 5), 3)
                            else:
                                pygame.draw.rect(game_window, (200, 255, 200), rect)  
                                pygame.draw.rect(game_window, (0, 200, 0), rect, 2)  
        
        if self.show_ai_path and self.ai_path and not self.is_recalculating_path and self.ai_path_index < len(self.ai_path) - 1:
            path_color = list(self.AI_PATH_COLOR) + [150] 
            path_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            
            for i in range(self.ai_path_index, len(self.ai_path) - 1):
                start_point = (self.ai_path[i][0]*GRID_CELL_SIZE+GRID_CELL_SIZE//2,
                             self.ai_path[i][1]*GRID_CELL_SIZE+GRID_CELL_SIZE//2)
                end_point = (self.ai_path[i+1][0]*GRID_CELL_SIZE+GRID_CELL_SIZE//2,
                           self.ai_path[i+1][1]*GRID_CELL_SIZE+GRID_CELL_SIZE//2)
                pygame.draw.line(game_window, self.AI_PATH_COLOR, start_point, end_point, 2)
                pygame.draw.circle(game_window, self.AI_PATH_COLOR, end_point, 3)
        
        if len(self.player_path_history) > 1:
            for i in range(1, len(self.player_path_history)):
                start_point = (self.player_path_history[i-1][0]*GRID_CELL_SIZE+GRID_CELL_SIZE//2,
                             self.player_path_history[i-1][1]*GRID_CELL_SIZE+GRID_CELL_SIZE//2)
                end_point = (self.player_path_history[i][0]*GRID_CELL_SIZE+GRID_CELL_SIZE//2,
                           self.player_path_history[i][1]*GRID_CELL_SIZE+GRID_CELL_SIZE//2)
                pygame.draw.line(game_window, BLACK, start_point, end_point, 4)
        
        if len(self.ai_path_history) > 1:
            for i in range(1, len(self.ai_path_history)):
                start_point = (self.ai_path_history[i-1][0]*GRID_CELL_SIZE+GRID_CELL_SIZE//2,
                             self.ai_path_history[i-1][1]*GRID_CELL_SIZE+GRID_CELL_SIZE//2)
                end_point = (self.ai_path_history[i][0]*GRID_CELL_SIZE+GRID_CELL_SIZE//2,
                           self.ai_path_history[i][1]*GRID_CELL_SIZE+GRID_CELL_SIZE//2)
                pygame.draw.line(game_window, self.AI_PATH_COLOR, start_point, end_point, 4)
        
        for position in self.player_position_markers:
            marker_position = (position[0]*GRID_CELL_SIZE+GRID_CELL_SIZE//2,
                             position[1]*GRID_CELL_SIZE+GRID_CELL_SIZE//2)
            pygame.draw.circle(game_window, BLUE, marker_position, 4)
        
        for position in self.ai_position_markers:
            marker_position = (position[0]*GRID_CELL_SIZE+GRID_CELL_SIZE//2,
                             position[1]*GRID_CELL_SIZE+GRID_CELL_SIZE//2)
            pygame.draw.circle(game_window, self.AI_MARKER_COLOR, marker_position, 4)
        
        if self.is_animating and self.is_player_turn:
            progress = (self.current_step + 1) / self.animation_steps
            x = int(self.animation_start[0] * (1 - progress) + self.animation_end[0] * progress)
            y = int(self.animation_start[1] * (1 - progress) + self.animation_end[1] * progress)
        else:
            x, y = self.player_x, self.player_y
        
        player_rect = pygame.Rect(x * GRID_CELL_SIZE, y * GRID_CELL_SIZE,
                                GRID_CELL_SIZE, GRID_CELL_SIZE)
        pygame.draw.rect(game_window, RED, player_rect)
        
        if self.is_animating and not self.is_player_turn:
            progress = (self.current_step + 1) / self.animation_steps
            x = int(self.animation_start[0] * (1 - progress) + self.animation_end[0] * progress)
            y = int(self.animation_start[1] * (1 - progress) + self.animation_end[1] * progress)
        else:
            x, y = self.ai_x, self.ai_y
        
        ai_rect = pygame.Rect(x * GRID_CELL_SIZE, y * GRID_CELL_SIZE,
                            GRID_CELL_SIZE, GRID_CELL_SIZE)
        pygame.draw.rect(game_window, self.AI_COLOR, ai_rect)
        
        if self.show_recalculating_message or self.is_recalculating_path:
            font = pygame.font.Font(None, 36)
            text = font.render("AI Recalculating Path to Avoid Player!", True, (255, 0, 0))
            text_rect = text.get_rect(center=(WINDOW_WIDTH//2, 30))
            bg_rect = text_rect.copy()
            bg_rect.inflate_ip(20, 10)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, 180))
            game_window.blit(bg_surface, bg_rect)
            game_window.blit(text, text_rect)
            
        if self.show_blocked_message:
            font = pygame.font.Font(None, 36)
            if self.is_player_turn:
                text = font.render("AI was blocked! Player's turn", True, (255, 165, 0))
            else:
                text = font.render("Player was blocked! AI's turn", True, (255, 165, 0))
            text_rect = text.get_rect(center=(WINDOW_WIDTH//2, 70))
            bg_rect = text_rect.copy()
            bg_rect.inflate_ip(20, 10)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, 180))
            game_window.blit(bg_surface, bg_rect)
            game_window.blit(text, text_rect)
            
            self.blocked_message_timer += 1
            if self.blocked_message_timer >= self.blocked_message_duration:
                self.show_blocked_message = False
                self.blocked_message_timer = 0
        
        if self.is_player_turn and not self.is_animating and self.game_running:
            has_collision_moves = False
            for dvx in (-1, 0, 1):
                for dvy in (-1, 0, 1):
                    new_vx = self.player_vx + dvx
                    new_vy = self.player_vy + dvy
                    new_x = self.player_x + new_vx
                    new_y = self.player_y + new_vy
                    
                    if 0 <= new_x < GRID_COLUMNS and 0 <= new_y < GRID_ROWS:
                        valid, _ = self.is_move_valid(self.player_x, self.player_y, new_x, new_y)
                        if valid and self.would_collide_with_ai(self.player_x, self.player_y, new_x, new_y):
                            has_collision_moves = True
                            break
            
            if has_collision_moves:
                font = pygame.font.Font(None, 28)
                text = font.render("Red X indicates moves that would collide with AI (not allowed)", True, (200, 0, 0))
                text_rect = text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT - 30))
                bg_rect = text_rect.copy()
                bg_rect.inflate_ip(20, 10)
                bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                bg_surface.fill((0, 0, 0, 150))
                game_window.blit(bg_surface, bg_rect)
                game_window.blit(text, text_rect)
        
        if self.game_running:
            mouse_pos = pygame.mouse.get_pos()
            font = pygame.font.Font(None, 24)  
            

            overlay_width = 200  
            overlay_height = 60  
            overlay_x = WINDOW_WIDTH - overlay_width - 10
            overlay_y = 10
            overlay_rect = pygame.Rect(overlay_x, overlay_y, overlay_width, overlay_height)
            
            if not overlay_rect.collidepoint(mouse_pos):
                bg_surface = pygame.Surface((overlay_width, overlay_height), pygame.SRCALPHA)
                bg_surface.fill((0, 0, 0, 180))
                game_window.blit(bg_surface, overlay_rect)
                pygame.draw.rect(game_window, WHITE, overlay_rect, 2)
                
                checkpoint_text = font.render("Checkpoint Order:", True, WHITE)
                game_window.blit(checkpoint_text, (overlay_x + 5, overlay_y + 5))
                
                blue_rect = pygame.Rect(overlay_x + 5, overlay_y + 30, 15, 15)  
                pygame.draw.rect(game_window, BLUE, blue_rect)
                blue_text = font.render("1. Blue", True, WHITE)
                game_window.blit(blue_text, (overlay_x + 25, overlay_y + 30))
                
                purple_rect = pygame.Rect(overlay_x + 5, overlay_y + 45, 15, 15)  
                pygame.draw.rect(game_window, PURPLE, purple_rect)
                purple_text = font.render("2. Purple", True, WHITE)
                game_window.blit(purple_text, (overlay_x + 25, overlay_y + 45))
        
        if self.show_stats:
            self.draw_stats_screen()
        
        pygame.display.flip()

    def is_player_on_ai_path(self):
        if not self.ai_path or self.ai_path_index >= len(self.ai_path) - 1:
            return False
            
        current_pos = self.ai_path[self.ai_path_index]
        next_pos = self.ai_path[self.ai_path_index + 1]
        
        path_points = self.bresenham_line(current_pos[0], current_pos[1], next_pos[0], next_pos[1])
        
        for x, y in path_points:
            if self.player_x == x and self.player_y == y:
                return True
            
        check_ahead = min(3, len(self.ai_path) - self.ai_path_index - 1)
        for i in range(1, check_ahead):
            next_pos = self.ai_path[self.ai_path_index + i]
            prev_pos = self.ai_path[self.ai_path_index + i - 1]
            path_points = self.bresenham_line(prev_pos[0], prev_pos[1], next_pos[0], next_pos[1])
            for x, y in path_points:
                if self.player_x == x and self.player_y == y:
                    return True
                    
        return False
        
    def would_collide_with_ai(self, start_x, start_y, end_x, end_y):
        if end_x == self.ai_x and end_y == self.ai_y:
            return True
            
        path_points = self.bresenham_line(start_x, start_y, end_x, end_y)
        for x, y in path_points:
            if x == self.ai_x and y == self.ai_y:
                return True
                
        return False

    def has_valid_moves_considering_opponent(self, is_player):
        current_x = self.player_x if is_player else self.ai_x
        current_y = self.player_y if is_player else self.ai_y
        current_vx = self.player_vx if is_player else self.ai_vx
        current_vy = self.player_vy if is_player else self.ai_vy
        
        for dvx in (-1, 0, 1):
            for dvy in (-1, 0, 1):
                new_vx = current_vx + dvx
                new_vy = current_vy + dvy
                new_x = current_x + new_vx
                new_y = current_y + new_vy
                
                if 0 <= new_x < GRID_COLUMNS and 0 <= new_y < GRID_ROWS:
                    valid, _ = self.is_move_valid(current_x, current_y, new_x, new_y)
                    if valid:
                        if is_player:
                            if not self.would_collide_with_ai(current_x, current_y, new_x, new_y):
                                return True
                        else:
                            if not (new_x == self.player_x and new_y == self.player_y) and \
                               not any(p == (self.player_x, self.player_y) for p in self.bresenham_line(current_x, current_y, new_x, new_y)):
                                return True
        return False

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
            'rect': pygame.Rect(WINDOW_WIDTH//2 - button_width//2, y, button_width, button_height),
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
    
    lap_buttons = []
    lap_button_width = 80
    lap_button_height = 80
    lap_spacing = 20
    total_lap_buttons_width = (lap_button_width * 3) + (lap_spacing * 2)
    start_x = WINDOW_WIDTH//2 - total_lap_buttons_width//2
    
    for i in range(1, 4):
        x = start_x + (i-1) * (lap_button_width + lap_spacing)
        lap_buttons.append({
            'rect': pygame.Rect(x, WINDOW_HEIGHT//2, lap_button_width, lap_button_height),
            'text': str(i),
            'color': LIGHT_GRAY,
            'hover_color': WHITE
        })
    
    checkbox_size = 30
    checkbox_rect = pygame.Rect(WINDOW_WIDTH//2 - 150, WINDOW_HEIGHT//2 + 100, checkbox_size, checkbox_size)
    show_ai_path = True
    
    selected_track = None
    show_lap_selection = False
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
                    if show_lap_selection and checkbox_rect.collidepoint(event.pos):
                        show_ai_path = not show_ai_path
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if show_lap_selection:
                        show_lap_selection = False
                        selected_track = None
                    else:
                        return None
        
        game_window.fill(WHITE)
        
        if not show_lap_selection:
            title = title_font.render("Select Track", True, BLACK)
            game_window.blit(title, (WINDOW_WIDTH//2 - title.get_width()//2, 100))
            
            instructions = font.render("Click a track to select, or press ESC to go back", True, GRAY)
            game_window.blit(instructions, (WINDOW_WIDTH//2 - instructions.get_width()//2, 150))
            
            back_hovered = back_button['rect'].collidepoint(mouse_pos)
            pygame.draw.rect(game_window, back_button['hover_color'] if back_hovered else back_button['color'], back_button['rect'])
            pygame.draw.rect(game_window, BLACK, back_button['rect'], 2)
            back_text = font.render(back_button['text'], True, BLACK)
            game_window.blit(back_text, (back_button['rect'].centerx - back_text.get_width()//2,
                                       back_button['rect'].centery - back_text.get_height()//2))
            
            if back_hovered and mouse_clicked:
                return None
            
            for button in buttons:
                hovered = button['rect'].collidepoint(mouse_pos)
                pygame.draw.rect(game_window, button['hover_color'] if hovered else button['color'], button['rect'])
                pygame.draw.rect(game_window, BLACK, button['rect'], 2)
                text = font.render(button['text'], True, BLACK)
                game_window.blit(text, (button['rect'].centerx - text.get_width()//2,
                                      button['rect'].centery - text.get_height()//2))
                
                if hovered and mouse_clicked:
                    selected_track = button['text']
                    show_lap_selection = True
        else:
            title = title_font.render("Select Number of Laps", True, BLACK)
            game_window.blit(title, (WINDOW_WIDTH//2 - title.get_width()//2, 100))
            
            instructions = font.render("Click a number to select laps, or press ESC to go back", True, GRAY)
            game_window.blit(instructions, (WINDOW_WIDTH//2 - instructions.get_width()//2, 150))
            
            for button in lap_buttons:
                hovered = button['rect'].collidepoint(mouse_pos)
                pygame.draw.rect(game_window, button['hover_color'] if hovered else button['color'], button['rect'])
                pygame.draw.rect(game_window, BLACK, button['rect'], 2)
                text = font.render(button['text'], True, BLACK)
                game_window.blit(text, (button['rect'].centerx - text.get_width()//2,
                                      button['rect'].centery - text.get_height()//2))
                
                if hovered and mouse_clicked:
                    return selected_track, int(button['text']), show_ai_path
            
            pygame.draw.rect(game_window, BLACK, checkbox_rect, 2)
            if show_ai_path:
                pygame.draw.rect(game_window, BLACK, checkbox_rect.inflate(-10, -10))
            
            checkbox_text = font.render("Show AI Path", True, BLACK)
            game_window.blit(checkbox_text, (checkbox_rect.right + 10, checkbox_rect.centery - checkbox_text.get_height()//2))
        
        pygame.display.flip()
    
    return None

def main():
    game = Game()
    
    result = select_track()
    if not result:
        return
    
    track_filename, laps, show_ai_path = result
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
    

if __name__ == "__main__":
    main()
