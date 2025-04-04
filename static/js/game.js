const socket = io();

function initGame() {
    // Initialize game canvas and logic
}

function renderOtherPlayers(players) {
    // Render other players with reduced opacity
}

socket.on('update', (data) => {
    renderOtherPlayers(data.players);
});