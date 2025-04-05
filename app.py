from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from game_manager import GameManager
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app)

game_manager = GameManager()
players = {}  # Store player information (username, admin status)
spectators = set()  # Track spectator IDs
game_in_progress = False
last_game_state = None  # Track the last game state to check for game over

# Background thread for updating game state
def game_state_updater():
    global game_in_progress, last_game_state
    
    while True:
        if game_in_progress:
            # Get the raw game state from the game manager
            game_state = game_manager.get_game_state()
            
            # Check for game over
            if "_metadata" in game_state and game_state["_metadata"]["game_over"]:
                # Game has ended
                winner_id = game_state["_metadata"]["winner"]
                
                # Prepare winner announcement
                winner_data = None
                if winner_id and winner_id in players:
                    winner_data = {
                        "id": winner_id,
                        "username": players[winner_id]["username"],
                        "score": game_state[winner_id]["score"] if winner_id in game_state else 0
                    }
                
                # Emit game over event
                socketio.emit('game_over', {
                    "winner": winner_data,
                    "all_dead": winner_id is None
                })
                
                # Game is no longer in progress
                game_in_progress = False
            
            # Enhance the game state with player information
            enhanced_state = {
                "game_data": game_state,
                "players_info": {}
            }
            
            # Add player details to the enhanced state
            for player_id, player_info in players.items():
                # Create default player data
                player_data = {
                    "id": player_id,
                    "username": player_info["username"],
                    "isAdmin": player_info["isAdmin"],
                    "score": 0,
                    "alive": False
                }
                
                # Update with game state if available
                if player_id in game_state:
                    player_data["score"] = game_state[player_id]["score"]
                    player_data["alive"] = game_state[player_id]["alive"]
                
                enhanced_state["players_info"][player_id] = player_data
            
            # Send the enhanced state to all clients
            socketio.emit('game_state', enhanced_state)
            
            # Store the last game state
            last_game_state = enhanced_state
            
        elif last_game_state is not None:
            # If game is over but we still have a last state, continue to send it
            # This ensures clients who connect after game over still see the results
            socketio.emit('game_state', last_game_state)
            
        time.sleep(0.1)  # Update 10 times per second

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    player_id = request.sid
    # Don't add to game_manager yet until they join the game
    
    # Send current game state to the new connection
    if last_game_state:
        emit('game_state', last_game_state)
    else:
        emit('game_state', {"game_data": game_manager.get_game_state(), "players_info": players})
        
    # If game is in progress, send game_started event
    if game_in_progress:
        emit('game_started')

@socketio.on('disconnect')
def handle_disconnect():
    player_id = request.sid
    # Check if this was a player or spectator
    if player_id in players:
        del players[player_id]
        game_manager.remove_player(player_id)
    elif player_id in spectators:
        spectators.remove(player_id)
        
    emit('lobby_update', {'players': list(players.values()), 'spectators': len(spectators)}, broadcast=True)
    
    # Send updated enhanced state
    game_state = game_manager.get_game_state()
    enhanced_state = {
        "game_data": game_state,
        "players_info": players
    }
    emit('game_state', enhanced_state, broadcast=True)

@socketio.on('join_game')
def handle_join_game(data):
    player_id = request.sid
    username = data.get('username', f'Player_{player_id[:5]}')
    is_admin = data.get('isAdmin', False)
    is_spectator = data.get('isSpectator', False)
    
    # Handle spectator join
    if is_spectator:
        spectators.add(player_id)
        if game_in_progress:
            emit('game_started')
    else:
        # Store player info
        players[player_id] = {
            'id': player_id,
            'username': username,
            'isAdmin': is_admin
        }
    
    # Send updated lobby info to all clients
    emit('lobby_update', {
        'players': list(players.values()), 
        'spectators': len(spectators),
        'allPlayersReady': len(players) > 1
    }, broadcast=True)

@socketio.on('start_game')
def handle_start_game():
    global game_in_progress, last_game_state
    player_id = request.sid
    
    # Check if request is from an admin
    if player_id in players and players[player_id]['isAdmin']:
        # Reset any previous game state
        last_game_state = None
        game_manager.reset_game()
        
        # Add all players to the game manager
        for pid in players:
            game_manager.add_player(pid)
        
        game_in_progress = True
        # Notify all clients (including spectators) that game has started
        emit('game_started', broadcast=True)
        
        # Start the game in GameManager
        game_manager.start_game()

@socketio.on('update_position')
def update_position(data):
    player_id = data.get('playerId')
    action = data.get('action')
    # Only process if player is in game
    if player_id in players:
        game_manager.update_player_action(player_id, action)

@socketio.on('get_all_players')
def get_all_players():
    """Return information about all players to the requesting client"""
    game_state = game_manager.get_game_state()
    
    # Combine player info with game state
    players_with_game_data = {}
    for player_id, player_info in players.items():
        player_data = {
            "id": player_id,
            "username": player_info["username"],
            "isAdmin": player_info["isAdmin"],
            "score": 0,
            "alive": False
        }
        
        # Update with game state if available
        if player_id in game_state:
            player_data["score"] = game_state[player_id]["score"]
            player_data["alive"] = game_state[player_id]["alive"]
        
        players_with_game_data[player_id] = player_data
    
    emit('all_players_info', {
        'players': players_with_game_data,
        'spectators': len(spectators)
    })

@socketio.on('reset_game')
def reset_game():
    global game_in_progress, last_game_state
    player_id = request.sid
    
    # Only admins can reset the game
    if player_id in players and players[player_id]['isAdmin']:
        game_manager.reset_game()
        game_in_progress = False
        last_game_state = None
        
        # Notify all clients that the game has been reset
        emit('game_reset', broadcast=True)

@socketio.on('spectate_game')
def spectate_game():
    """Allow a user to spectate the current game without participating"""
    player_id = request.sid
    
    # Add to spectators if not already a player
    if player_id not in players:
        spectators.add(player_id)
        
        # If game is in progress, send game_started event to the spectator
        if game_in_progress:
            emit('game_started')
        
        # Update lobby info
        emit('lobby_update', {
            'players': list(players.values()), 
            'spectators': len(spectators)
        }, broadcast=True)

@socketio.on('toggle_test_mode')
def toggle_test_mode(data):
    player_id = request.sid
    enabled = data.get('enabled')
    
    # Only admins can toggle test mode
    if player_id in players and players[player_id]['isAdmin']:
        # Toggle test mode in game manager
        game_manager.set_test_mode(enabled)
        
        # Notify all clients about the test mode status
        emit('test_mode_status', {
            'enabled': enabled
        }, broadcast=True)

if __name__ == '__main__':
    # Start background thread for game state updates
    state_thread = threading.Thread(target=game_state_updater)
    state_thread.daemon = True
    state_thread.start()
    
    # Start the Flask app
    socketio.run(app, host='0.0.0.0', port=8000, debug=True, allow_unsafe_werkzeug=True)