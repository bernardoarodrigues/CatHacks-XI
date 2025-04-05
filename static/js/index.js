const socket = io();
let currentUser = {
    id: '',
    username: '',
    isAdmin: false,
    inGame: false
};

// Game assets
const gameAssets = {
    bird: {
        blue: null,
        red: null,
        yellow: null
    },
    background: null,
    ground: null,
    pipe: {
        green: {
            top: null,
            bottom: null
        }
    },
    loaded: false
};

// Load game assets
function loadGameAssets() {
    // Bird sprites
    gameAssets.bird.blue = new Image();
    gameAssets.bird.blue.src = '/static/sprites/bluebird-midflap.png';
    
    gameAssets.bird.red = new Image();
    gameAssets.bird.red.src = '/static/sprites/redbird-midflap.png';
    
    gameAssets.bird.yellow = new Image();
    gameAssets.bird.yellow.src = '/static/sprites/yellowbird-midflap.png';
    
    // Background
    gameAssets.background = new Image();
    gameAssets.background.src = '/static/sprites/background-day.png';
    
    // Ground
    gameAssets.ground = new Image();
    gameAssets.ground.src = '/static/sprites/base.png';
    
    // Pipes - only need one since we'll create the patterns ourselves
    gameAssets.pipe.green.image = new Image();
    gameAssets.pipe.green.image.src = '/static/sprites/pipe-green.png';
    
    // Wait for pipe image to load before creating patterns
    gameAssets.pipe.green.image.onload = () => {
        // Create a temporary canvas for the top pipe pattern
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = gameAssets.pipe.green.image.width;
        tempCanvas.height = gameAssets.pipe.green.image.height;
        const tempCtx = tempCanvas.getContext('2d');
        
        // Draw the original pipe
        tempCtx.drawImage(gameAssets.pipe.green.image, 0, 0);
        
        // Create patterns
        gameAssets.pipe.green.bottom = gameCanvasContext.createPattern(tempCanvas, 'repeat');
        
        // Now flip the image vertically for top pipe
        tempCtx.clearRect(0, 0, tempCanvas.width, tempCanvas.height);
        tempCtx.save();
        tempCtx.translate(tempCanvas.width/2, tempCanvas.height/2);
        tempCtx.scale(1, -1);
        tempCtx.drawImage(gameAssets.pipe.green.image, -tempCanvas.width/2, -tempCanvas.height/2);
        tempCtx.restore();
        
        gameAssets.pipe.green.top = gameCanvasContext.createPattern(tempCanvas, 'repeat');
    };
    
    // Mark assets as loaded when background loads
    gameAssets.background.onload = () => {
        gameAssets.loaded = true;
        loadingIndicator.style.display = 'none';
        resizeGameCanvas(); // Make sure canvas is properly sized
    };
}

// DOM Elements
const loginSection = document.getElementById('login-section');
const lobbySection = document.getElementById('lobby-section');
const gameSection = document.getElementById('game-section');
const adminControls = document.getElementById('admin-controls');
const adminGameControls = document.getElementById('admin-game-controls');
const adminResetControls = document.getElementById('admin-reset-controls');
const playersList = document.getElementById('players');
const gameCanvas = document.getElementById('game-canvas');
const gameCanvasContext = gameCanvas.getContext('2d');
const gameOverlayScore = document.getElementById('game-overlay-score');
const loadingIndicator = document.getElementById('loading-indicator');
const playersScores = document.getElementById('players-scores');
const gameOverModal = document.getElementById('game-over-modal');
const winnerAnnouncement = document.getElementById('winner-announcement');
const playersAliveElem = document.getElementById('players-alive');

// Game state
let gameState = null;
let playersInfo = {};
let animationFrameId = null;
let showDebugBoxes = false; // Debug flag
let countdownActive = false;
let countdownValue = 0;

// Canvas sizing
function resizeGameCanvas() {
    const container = document.getElementById('game-canvas-container');
    const containerHeight = container.clientHeight;
    
    // Get the container's current computed dimensions
    const computedStyle = window.getComputedStyle(container);
    
    // Set canvas dimensions to match container
    gameCanvas.width = parseInt(computedStyle.width);
    gameCanvas.height = containerHeight;
    
    // Force the container to be visible
    container.style.display = 'block';
    
    // If we have a game state, render it
    if (gameState && gameAssets.loaded) {
        renderGame();
    } else {
        // Draw something on the canvas to make sure it's visible even without game state
        const ctx = gameCanvasContext;
        ctx.clearRect(0, 0, gameCanvas.width, gameCanvas.height);
        ctx.fillStyle = '#87CEEB'; // Sky blue
        ctx.fillRect(0, 0, gameCanvas.width, gameCanvas.height);
        ctx.fillStyle = 'white';
        ctx.font = '20px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Game loading...', gameCanvas.width / 2, gameCanvas.height / 2);
    }
    
    console.log(`Canvas resized: ${gameCanvas.width}x${gameCanvas.height}`);
}

// Call resize on window resize
window.addEventListener('resize', resizeGameCanvas);
window.addEventListener('load', resizeGameCanvas);

// Join game button
document.getElementById('join-btn').addEventListener('click', () => {
    const username = document.getElementById('username').value.trim();
    if (!username) {
        alert('Please enter a username');
        return;
    }
    
    currentUser.username = username;
    currentUser.isAdmin = document.getElementById('admin-checkbox').checked;
    
    socket.emit('join_game', {
        username: currentUser.username,
        isAdmin: currentUser.isAdmin
    });
    
    // Show lobby section, hide login
    loginSection.style.display = 'none';
    lobbySection.style.display = 'block';
    
    // Show admin controls if user is admin
    if (currentUser.isAdmin) {
        adminControls.style.display = 'block';
        adminGameControls.style.display = 'block';
        adminResetControls.style.display = 'block';
    }
});

// Admin: Start game button
document.getElementById('start-game-btn').addEventListener('click', () => {
    if (currentUser.isAdmin) {
        socket.emit('start_game');
    }
});

// Admin: Reset game buttons
document.getElementById('reset-game-btn').addEventListener('click', resetGame);
document.getElementById('modal-reset-btn').addEventListener('click', resetGame);

function resetGame() {
    if (currentUser.isAdmin) {
        socket.emit('reset_game');
        gameOverModal.classList.add('hidden');
    }
}

// Socket events
socket.on('connect', () => {
    currentUser.id = socket.id;
});

socket.on('lobby_update', (data) => {
    // Update players list
    playersList.innerHTML = '';
    data.players.forEach(player => {
        const li = document.createElement('li');
        li.textContent = player.username + (player.isAdmin ? ' (Admin)' : '');
        playersList.appendChild(li);
    });
});

socket.on('game_started', () => {
    // Load game assets if not already loaded
    if (!gameAssets.loaded) {
        loadGameAssets();
    } else {
        loadingIndicator.style.display = 'none';
    }
    
    // Hide lobby, show game
    lobbySection.style.display = 'none';
    gameSection.style.display = 'block';
    currentUser.inGame = true;
    
    // Hide game over modal if visible
    gameOverModal.classList.add('hidden');
    
    // Setup canvas size
    resizeGameCanvas();
    
    // Request player info
    socket.emit('get_all_players');
    
    // Show admin game controls if user is admin
    if (currentUser.isAdmin) {
        adminGameControls.style.display = 'block';
    }
    
    // Start game loop
    startGameLoop();
});

socket.on('game_state', (enhancedState) => {
    if (currentUser.inGame) {
        gameState = enhancedState.game_data;
        playersInfo = enhancedState.players_info;
        updateGameDisplay(enhancedState);
    }
});

socket.on('all_players_info', (playersInfo) => {
    // Update player scoreboard with all players
    updatePlayersScoreboard(playersInfo);
});

socket.on('game_over', (data) => {
    // Stop game loop
    stopGameLoop();
    
    // Display game over modal with winner information
    if (data.winner) {
        winnerAnnouncement.innerHTML = `
            <p>Winner is:</p>
            <div class="winner-name">${data.winner.username}</div>
            <p>with a score of ${data.winner.score}</p>
        `;
    } else {
        winnerAnnouncement.innerHTML = `
            <p>All players died!</p>
            <p>No winner this round.</p>
        `;
    }
    
    gameOverModal.classList.remove('hidden');
});

socket.on('game_reset', () => {
    // Stop game loop
    stopGameLoop();
    
    // Return to lobby
    gameSection.style.display = 'none';
    lobbySection.style.display = 'block';
    currentUser.inGame = false;
    
    // Reset game state
    gameState = null;
    playersInfo = {};
    
    // Hide game over modal if visible
    gameOverModal.classList.add('hidden');
});

// Game controls
document.addEventListener('keydown', (event) => {
    if (currentUser.inGame && event.code === 'Space') {
        socket.emit('update_position', {
            playerId: currentUser.id,
            action: 1  // Flap
        });
        event.preventDefault(); // Prevent scrolling on space
    }
    
    // Add debug toggle with 'D' key
    if (event.code === 'KeyD') {
        showDebugBoxes = !showDebugBoxes;
        console.log(`Debug boxes ${showDebugBoxes ? 'enabled' : 'disabled'}`);
    }
});

// Mobile touch control
gameCanvas.addEventListener('touchstart', (event) => {
    if (currentUser.inGame) {
        socket.emit('update_position', {
            playerId: currentUser.id,
            action: 1  // Flap
        });
        event.preventDefault(); // Prevent default touch behavior
    }
});

// Game loop functions
function startGameLoop() {
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
    }
    
    function gameLoop() {
        renderGame();
        animationFrameId = requestAnimationFrame(gameLoop);
    }
    
    animationFrameId = requestAnimationFrame(gameLoop);
}

function stopGameLoop() {
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
    }
}

// Game rendering function
function renderGame() {
    if (!gameState || !gameAssets.loaded) return;
    
    const ctx = gameCanvasContext;
    const canvas = gameCanvas;
    
    // Get metadata from gameState
    const metadata = gameState._metadata || {};
    const gameData = metadata.game_data || {};
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Calculate scale factors for responsive rendering
    const scaleX = canvas.width / (gameData.screen_width || 288);
    const scaleY = canvas.height / (gameData.screen_height || 512);
    
    // Draw background
    ctx.drawImage(gameAssets.background, 0, 0, canvas.width, canvas.height);
    
    // Draw pipes
    if (gameData.pipes) {
        // First draw all lower pipes
        gameData.pipes.forEach(pipe => {
            const pipeX = pipe.x * scaleX;
            const lowerY = pipe.lower_y * scaleY;
            const pipeWidth = (gameData.pipe_width || 52) * scaleX;
            
            // Lower pipe
            ctx.fillStyle = '#74BF2E'; // Green color
            ctx.fillRect(pipeX, lowerY, pipeWidth, canvas.height - lowerY);
            
            // Border
            ctx.strokeStyle = '#528C1E';
            ctx.lineWidth = 4;
            ctx.strokeRect(pipeX, lowerY, pipeWidth, canvas.height - lowerY);
        });
        
        // Now draw all upper pipes with the same green color
        gameData.pipes.forEach(pipe => {
            const pipeX = pipe.x * scaleX;
            const upperY = pipe.upper_y * scaleY;
            const lowerY = pipe.lower_y * scaleY;
            const pipeWidth = (gameData.pipe_width || 52) * scaleX;
            const gap = lowerY - upperY;
            
            // Upper pipe - now use the same green color as lower pipes
            ctx.fillStyle = '#74BF2E'; // Match the lower pipe color
            ctx.fillRect(pipeX, 0, pipeWidth, upperY);
            
            // Border
            ctx.strokeStyle = '#528C1E';
            ctx.lineWidth = 4;
            ctx.strokeRect(pipeX, 0, pipeWidth, upperY);
            
            // Draw a thin line showing the gap (for debugging)
            if (showDebugBoxes) {
                ctx.beginPath();
                ctx.moveTo(pipeX - 5, upperY);
                ctx.lineTo(pipeX - 5, lowerY);
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 2;
                ctx.stroke();
                
                // Add gap measurement text
                ctx.font = '12px Arial';
                ctx.fillStyle = 'white';
                ctx.textAlign = 'right';
                ctx.fillText(`${Math.round(gap)}px`, pipeX - 8, upperY + gap/2);
            }
        });
        
        // Draw debug boxes
        if (showDebugBoxes) {
            gameData.pipes.forEach(pipe => {
                const pipeX = pipe.x * scaleX;
                const upperY = pipe.upper_y * scaleY;
                const lowerY = pipe.lower_y * scaleY;
                const pipeWidth = (gameData.pipe_width || 52) * scaleX;
                const gap = lowerY - upperY;
                
                // Upper pipe collision box
                ctx.fillStyle = 'rgba(255, 0, 0, 0.2)';
                ctx.fillRect(pipeX, 0, pipeWidth, upperY);
                ctx.strokeStyle = 'rgba(255, 0, 0, 0.7)';
                ctx.lineWidth = 2;
                ctx.strokeRect(pipeX, 0, pipeWidth, upperY);
                
                // Gap area (safe zone) - highlight in blue
                ctx.fillStyle = 'rgba(0, 255, 255, 0.2)';
                ctx.fillRect(pipeX, upperY, pipeWidth, gap);
                
                // Lower pipe collision box
                ctx.fillStyle = 'rgba(0, 0, 255, 0.2)';
                ctx.fillRect(pipeX, lowerY, pipeWidth, canvas.height - lowerY);
                ctx.strokeStyle = 'rgba(0, 0, 255, 0.7)';
                ctx.lineWidth = 2;
                ctx.strokeRect(pipeX, lowerY, pipeWidth, canvas.height - lowerY);
                
                // Add horizontal lines at boundaries
                // Upper pipe bottom edge (boundary)
                ctx.beginPath();
                ctx.moveTo(pipeX, upperY);
                ctx.lineTo(pipeX + pipeWidth, upperY);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
                ctx.lineWidth = 3;
                ctx.stroke();
                
                // Lower pipe top edge (boundary)
                ctx.beginPath();
                ctx.moveTo(pipeX, lowerY);
                ctx.lineTo(pipeX + pipeWidth, lowerY);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
                ctx.lineWidth = 3;
                ctx.stroke();
                
                // Add gap measurement text
                ctx.font = '12px Arial';
                ctx.fillStyle = 'white';
                ctx.textAlign = 'right';
                ctx.fillText(`${Math.round(gap)}px`, pipeX - 8, upperY + gap/2);
            });
        }
    }
    
    // Draw ground
    if (gameData.ground_y) {
        const groundY = gameData.ground_y * scaleY;
        ctx.drawImage(gameAssets.ground, 0, groundY, canvas.width, canvas.height - groundY);
        
        // Debug: Draw ground collision box
        if (showDebugBoxes) {
            ctx.strokeStyle = 'rgba(255, 255, 0, 0.7)';
            ctx.lineWidth = 2;
            ctx.strokeRect(0, groundY, canvas.width, canvas.height - groundY);
        }
    }
    
    // Draw players (birds)
    for (const playerId in gameState) {
        if (playerId === '_metadata') continue;
        
        const player = gameState[playerId];
        if (!player.alive) continue;
        
        // Get player position
        const playerPos = player.position;
        if (!playerPos) continue;
        
        // Scale the positions
        const playerX = playerPos.x * scaleX;
        const playerY = playerPos.y * scaleY;
        const playerWidth = 34 * scaleX;
        const playerHeight = 24 * scaleY;
        
        // Check if this is the current player
        const isCurrentPlayer = playerId === currentUser.id;
        
        // Apply rotation to the bird
        ctx.save();
        ctx.translate(playerX + playerWidth/2, playerY + playerHeight/2);
        ctx.rotate(playerPos.rotation * Math.PI / 180);
        ctx.translate(-(playerX + playerWidth/2), -(playerY + playerHeight/2));
        
        // Set opacity based on whether this is current player or another player
        if (isCurrentPlayer) {
            // Current player: full opacity, orange color (using red bird for orange)
            ctx.globalAlpha = 1.0;
            ctx.drawImage(
                gameAssets.bird.red, // Using red bird for orange color
                playerX, 
                playerY, 
                playerWidth, 
                playerHeight
            );
        } else {
            // Other players: blue with dimmed opacity (ghost-like)
            ctx.globalAlpha = 0.6; // Dimmed opacity for ghost effect
            ctx.drawImage(
                gameAssets.bird.blue,
                playerX, 
                playerY, 
                playerWidth, 
                playerHeight
            );
        }
        
        // Reset opacity
        ctx.globalAlpha = 1.0;
        
        // Restore context
        ctx.restore();
        
        // Debug: Draw bird collision box
        if (showDebugBoxes) {
            ctx.strokeStyle = 'rgba(0, 255, 0, 0.7)';
            ctx.lineWidth = 2;
            ctx.strokeRect(playerX, playerY, playerWidth, playerHeight);
        }
        
        // Display player name above bird
        if (playersInfo && playersInfo[playerId]) {
            const playerName = playersInfo[playerId].username;
            ctx.fillStyle = playerId === currentUser.id ? '#ff8c00' : '#ffffff'; // Orange color for current player
            ctx.strokeStyle = '#000000';
            ctx.lineWidth = 2;
            ctx.font = `${12 * scaleX}px Arial`;
            ctx.textAlign = 'center';
            ctx.strokeText(playerName, playerX + playerWidth/2, playerY - 10 * scaleY);
            ctx.fillText(playerName, playerX + playerWidth/2, playerY - 10 * scaleY);
        }
    }
    
    // Check if countdown is active and draw it
    if (metadata.countdown && metadata.countdown.active) {
        countdownActive = true;
        countdownValue = Math.ceil(metadata.countdown.remaining);
        
        // Draw a semi-transparent overlay
        ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Draw countdown text
        ctx.fillStyle = 'white';
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 8;
        
        // Use a large font size that scales with the canvas
        const fontSize = Math.min(canvas.width, canvas.height) * 0.25;
        ctx.font = `bold ${fontSize}px Arial`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        // Position the countdown in the center of the screen
        const textX = canvas.width / 2;
        const textY = canvas.height / 2;
        
        // Draw "GET READY" text
        const getReadyFontSize = fontSize * 0.3;
        ctx.font = `bold ${getReadyFontSize}px Arial`;
        ctx.strokeText('GET READY!', textX, textY - fontSize * 0.7);
        ctx.fillText('GET READY!', textX, textY - fontSize * 0.7);
        
        // Draw the countdown number with a drop shadow effect
        ctx.font = `bold ${fontSize}px Arial`;
        ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
        ctx.shadowBlur = 10;
        ctx.shadowOffsetX = 5;
        ctx.shadowOffsetY = 5;
        
        ctx.strokeText(countdownValue, textX, textY);
        ctx.fillText(countdownValue, textX, textY);
        
        // Reset shadow
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
    } else {
        countdownActive = false;
    }
}

function updateGameDisplay(enhancedState) {
    const gameData = enhancedState.game_data;
    const playerInfos = enhancedState.players_info;
    
    // Get current player state
    let playerState = null;
    if (gameData && gameData[currentUser.id]) {
        playerState = gameData[currentUser.id];
        
        // Update score in overlay
        const scoreValue = Math.floor(playerState.score);
        gameOverlayScore.textContent = 'Score: ' + scoreValue;
        
        // Show notification if player is dead
        if (!playerState.alive) {
            // Create a toast notification instead of changing the instruction box
            // showNotification('Game Over! Your bird has crashed. Waiting for other players to finish...', 'error');
        }
    }
    
    // Update scoreboard with all players
    updatePlayersScoreboard(playerInfos);
    
    // Count players alive
    let playersAlive = 0;
    if (gameData) {
        // Filter out the metadata key
        const filteredGameState = Object.entries(gameData)
            .filter(([key]) => key !== '_metadata')
            .reduce((obj, [key, value]) => ({ ...obj, [key]: value }), {});
            
        playersAlive = Object.values(filteredGameState).filter(p => p.alive).length;
    }
    playersAliveElem.textContent = 'Players Alive: ' + playersAlive;
}

function updatePlayersScoreboard(playersInfo) {
    // Clear current scoreboard
    playersScores.innerHTML = '';
    
    // Sort players by score (highest first)
    const sortedPlayers = Object.values(playersInfo).sort((a, b) => b.score - a.score);
    
    // Add each player to the scoreboard
    sortedPlayers.forEach(player => {
        const playerRow = document.createElement('div');
        playerRow.className = `player-row ${player.alive ? 'alive' : 'dead'}`;
        
        const isCurrentPlayer = player.id === currentUser.id;
        
        playerRow.innerHTML = `
            <span class="player-name ${isCurrentPlayer ? 'current-player' : ''}">
                ${player.username} ${isCurrentPlayer ? '(You)' : ''}
            </span>
            <span class="player-score">Score: ${Math.floor(player.score)}</span>
        `;
        
        playersScores.appendChild(playerRow);
    });
}

// Initialize game when page loads
window.addEventListener('load', () => {
    loadingIndicator.style.display = 'none';
});

// Show notification function
function showNotification(message, type = 'info') {
    // Create a toast notification
    const toast = document.createElement('div');
    toast.className = 'notification-toast';
    toast.textContent = message;
    
    // Set style based on type
    if (type === 'error') {
        toast.style.backgroundColor = '#ffebee';
        toast.style.borderLeft = '4px solid #f44336';
    } else if (type === 'success') {
        toast.style.backgroundColor = '#e8f5e9';
        toast.style.borderLeft = '4px solid #4caf50';
    } else {
        toast.style.backgroundColor = '#e3f2fd';
        toast.style.borderLeft = '4px solid #2196f3';
    }
    
    document.body.appendChild(toast);
    
    // Remove after 5 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => document.body.removeChild(toast), 500);
    }, 5000);
}

// Keep track of test mode status
let testModeEnabled = false;

// Test mode toggle button
document.getElementById('toggle-test-mode-btn').addEventListener('click', () => {
    if (currentUser.isAdmin) {
        testModeEnabled = !testModeEnabled;
        socket.emit('toggle_test_mode', {
            enabled: testModeEnabled
        });
        
        // Update button appearance
        updateTestModeButton();
    }
});

// Update test mode button appearance
function updateTestModeButton() {
    const btn = document.getElementById('toggle-test-mode-btn');
    if (testModeEnabled) {
        btn.classList.add('test-mode-active');
        btn.textContent = 'Test Mode: ON';
    } else {
        btn.classList.remove('test-mode-active');
        btn.textContent = 'Toggle Test Mode';
    }
}

// Test mode toggle functionality
document.getElementById('test-mode-toggle').addEventListener('change', function() {
    if (currentUser.isAdmin) {
        const isEnabled = this.checked;
        socket.emit('toggle_test_mode', {
            enabled: isEnabled
        });
        
        // Update display immediately for admin
        document.getElementById('test-mode-status').textContent = isEnabled ? 'ON' : 'OFF';
    }
});

// Listen for test mode status updates
socket.on('test_mode_status', (data) => {
    // Update checkbox state
    document.getElementById('test-mode-toggle').checked = data.enabled;
    document.getElementById('test-mode-status').textContent = data.enabled ? 'ON' : 'OFF';
    
    // Show notification for in-game players
    if (currentUser.inGame) {
        const notificationText = data.enabled 
            ? 'Test Mode enabled: Players will never die and game continues indefinitely.' 
            : 'Test Mode disabled: Normal game rules apply.';
        
        // Use our notification function instead
        showNotification(notificationText, data.enabled ? 'info' : 'success');
    }
});

// Initialize button on load
window.addEventListener('load', () => {
    updateTestModeButton();
});