from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from game_manager import GameManager
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app)

game_manager = GameManager()
players = {}  # Store player information (username, admin status)
game_in_progress = False

# Background thread for updating game state
def game_state_updater():
    while True:
        if game_in_progress:
            game_state = game_manager.get_game_state()
            socketio.emit('game_state', game_state)
        time.sleep(0.1)  # Update 10 times per second

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    player_id = request.sid
    # Don't add to game_manager yet until they join the game
    emit('game_state', game_manager.get_game_state(), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    player_id = request.sid
    if player_id in players:
        del players[player_id]
    game_manager.remove_player(player_id)
    emit('lobby_update', {'players': list(players.values())}, broadcast=True)
    emit('game_state', game_manager.get_game_state(), broadcast=True)

@socketio.on('join_game')
def handle_join_game(data):
    player_id = request.sid
    username = data.get('username', f'Player_{player_id[:5]}')
    is_admin = data.get('isAdmin', False)
    
    # Store player info
    players[player_id] = {
        'id': player_id,
        'username': username,
        'isAdmin': is_admin
    }
    
    # Send updated lobby info to all clients
    emit('lobby_update', {'players': list(players.values()), 'allPlayersReady': len(players) > 1}, broadcast=True)

@socketio.on('start_game')
def handle_start_game():
    global game_in_progress
    player_id = request.sid
    
    # Check if request is from an admin
    if player_id in players and players[player_id]['isAdmin']:
        # Add all players to the game manager
        for pid in players:
            game_manager.add_player(pid)
        
        game_in_progress = True
        # Notify all clients that game has started
        emit('game_started', broadcast=True)
        
        # Start the game in GameManager
        game_manager.start_game()

@socketio.on('update_position')
def update_position(data):
    player_id = data.get('playerId')
    action = data.get('action')
    game_manager.update_player_action(player_id, action)

if __name__ == '__main__':
    # Start background thread for game state updates
    state_thread = threading.Thread(target=game_state_updater)
    state_thread.daemon = True
    state_thread.start()
    
    # Start the Flask app
    socketio.run(app)