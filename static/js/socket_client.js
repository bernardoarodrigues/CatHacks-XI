const socket = io();

let playerId = null;

socket.on('connect', () => {
    playerId = socket.id;
    console.log(`Connected as player: ${playerId}`);
});

function sendPlayerAction(action) {
    socket.emit('update_position', { playerId, action });
}

socket.on('game_state', (data) => {
    console.log('Game state updated:', data);
    renderOtherPlayers(data.players);
});