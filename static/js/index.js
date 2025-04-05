const socket = io();
let currentUser = {
    id: '',
    username: '',
    isAdmin: false,
    inGame: false,
    inAiGame: false // Track if user is in AI game mode
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
const gameCanvasContainer = document.getElementById('game-canvas-container');

// Game state
let gameState = null;
let aiGameState = null; // Store AI game state
let playersInfo = {};
let animationFrameId = null;
let showDebugBoxes = false; // Debug flag
let countdownActive = false;
let countdownValue = 0;
let isMobileFullscreenMode = false;

// Function to check if device is mobile
function isMobileDevice() {
    return (window.innerWidth <= 768) || 
           navigator.userAgent.match(/Android/i) || 
           navigator.userAgent.match(/iPhone|iPad|iPod/i);
}

// Function to toggle mobile fullscreen mode
function toggleMobileFullscreenMode(enable) {
    if (!isMobileDevice()) return;
    
    document.body.classList.toggle('mobile-fullscreen-game', enable);
    isMobileFullscreenMode = enable;
    
    // Update fullscreen button text
    const fullscreenBtn = document.getElementById('toggle-fullscreen');
    if (fullscreenBtn) {
        fullscreenBtn.textContent = enable ? 'Exit Fullscreen' : 'Go Fullscreen';
    }
    
    // Add exit button if entering fullscreen mode
    if (enable) {
        // Create exit fullscreen button if it doesn't exist
        let exitBtn = document.querySelector('.exit-fullscreen');
        if (!exitBtn) {
            exitBtn = document.createElement('button');
            exitBtn.className = 'exit-fullscreen';
            exitBtn.innerHTML = '✕';
            exitBtn.addEventListener('click', () => {
                toggleMobileFullscreenMode(false);
            });
            document.body.appendChild(exitBtn);
        }
    } else {
        // Remove exit button if exiting fullscreen mode
        const exitBtn = document.querySelector('.exit-fullscreen');
        if (exitBtn) {
            exitBtn.remove();
        }
    }
    
    // Force resize the canvas after toggling fullscreen
    setTimeout(resizeGameCanvas, 100);
}

// Canvas sizing with improved responsive handling
function resizeGameCanvas() {
    const container = document.getElementById('game-canvas-container');
    if (!container) return;
    
    const containerHeight = container.clientHeight;
    
    // Get the container's current computed dimensions
    const computedStyle = window.getComputedStyle(container);
    
    // Set canvas dimensions to match container
    gameCanvas.width = parseInt(computedStyle.width);
    gameCanvas.height = containerHeight;
    
    // Force the container to be visible
    container.style.display = 'block';
    
    // If we have a game state, render it
    if ((gameState && gameAssets.loaded) || (currentUser.inAiGame && aiGameState && gameAssets.loaded)) {
        if (currentUser.inAiGame) {
            renderAiGame();
        } else {
            renderGame();
        }
    } else {
        // Draw something on the canvas to make sure it's visible even without game state
        const ctx = gameCanvasContext;
        ctx.clearRect(0, 0, gameCanvas.width, gameCanvas.height);
        ctx.fillStyle = '#87CEEB'; // Sky blue
        ctx.fillRect(0, 0, gameCanvas.width, gameCanvas.height);
        
        // Draw some clouds to make it look nicer while loading
        drawClouds(ctx);
        
        ctx.fillStyle = 'white';
        ctx.font = 'bold 20px Arial';
        ctx.textAlign = 'center';
        ctx.shadowColor = 'rgba(0,0,0,0.3)';
        ctx.shadowBlur = 4;
        ctx.shadowOffsetX = 2;
        ctx.shadowOffsetY = 2;
        ctx.fillText('Game loading...', gameCanvas.width / 2, gameCanvas.height / 2);
        ctx.shadowColor = 'transparent';
    }
    
    console.log(`Canvas resized: ${gameCanvas.width}x${gameCanvas.height}`);
}

// Draw decorative clouds on the canvas
function drawClouds(ctx) {
    const clouds = [
        { x: gameCanvas.width * 0.1, y: gameCanvas.height * 0.2, size: 40 },
        { x: gameCanvas.width * 0.5, y: gameCanvas.height * 0.15, size: 50 },
        { x: gameCanvas.width * 0.8, y: gameCanvas.height * 0.25, size: 35 },
    ];
    
    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
    
    clouds.forEach(cloud => {
        // Draw a cloud shape
        ctx.beginPath();
        ctx.arc(cloud.x, cloud.y, cloud.size, 0, Math.PI * 2);
        ctx.arc(cloud.x + cloud.size * 0.6, cloud.y - cloud.size * 0.1, cloud.size * 0.7, 0, Math.PI * 2);
        ctx.arc(cloud.x + cloud.size * 1.1, cloud.y + cloud.size * 0.1, cloud.size * 0.8, 0, Math.PI * 2);
        ctx.fill();
    });
}

// Call resize on window resize
window.addEventListener('resize', resizeGameCanvas);
window.addEventListener('load', resizeGameCanvas);

// Add event listener for fullscreen toggle button
document.addEventListener('DOMContentLoaded', () => {
    const fullscreenBtn = document.getElementById('toggle-fullscreen');
    if (fullscreenBtn) {
        fullscreenBtn.addEventListener('click', () => {
            toggleMobileFullscreenMode(!isMobileFullscreenMode);
        });
    }
});

// Join game button
document.getElementById('join-btn').addEventListener('click', () => {
    const username = document.getElementById('username').value.trim();
    if (!username) {
        alert('Please enter a username');
        return;
    }

    const queryString = window.location.search;
    const urlParams = new URLSearchParams(queryString);
    const admin = urlParams.get('admin');
    
    currentUser.username = username;
    currentUser.isAdmin = admin === '1';
    
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
    
    // Toggle mobile fullscreen mode
    toggleMobileFullscreenMode(true);
    
    // Start game loop
    startGameLoop();
});

socket.on('ai_game_started', () => {
    // Load game assets if not already loaded
    if (!gameAssets.loaded) {
        loadGameAssets();
    }
    
    // Toggle mobile fullscreen mode
    toggleMobileFullscreenMode(true);
});

socket.on('game_state', (enhancedState) => {
    if (currentUser.inGame) {
        gameState = enhancedState.game_data;
        playersInfo = enhancedState.players_info;
        updateGameDisplay(enhancedState);
    }
});

socket.on('ai_game_state', (state) => {
    if (currentUser.inAiGame) {
        aiGameState = state;
        updateAiGameDisplay();
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
            <p>with a score of ${Math.floor(data.winner.score)}</p>
        `;
    } else {
        winnerAnnouncement.innerHTML = `
            <p>All players died!</p>
            <p>No winner this round.</p>
        `;
    }
    
    gameOverModal.classList.remove('hidden');
});

socket.on('ai_game_over', (data) => {
    // Stop game loop
    stopGameLoop();
    
    // Display game over modal with winner information
    if (data.winner) {
        winnerAnnouncement.innerHTML = `
            <p>Winner is:</p>
            <div class="winner-name">${data.winner.username}</div>
            <p>with a score of ${Math.floor(data.winner.score)}</p>
        `;
    } else {
        winnerAnnouncement.innerHTML = `
            <p>Both players died!</p>
            <p>No winner this round.</p>
        `;
    }
    
    // Add "Play Again" button
    const resetBtn = document.createElement('button');
    resetBtn.className = 'reset-button';
    resetBtn.textContent = 'Play Again';
    resetBtn.addEventListener('click', () => {
        socket.emit('reset_ai_game');
        gameOverModal.classList.add('hidden');
    });
    
    // Add "Back to Menu" button
    const menuBtn = document.createElement('button');
    menuBtn.className = 'reset-button';
    menuBtn.textContent = 'Back to Menu';
    menuBtn.addEventListener('click', () => {
        socket.emit('reset_ai_game');
        gameOverModal.classList.add('hidden');
        gameSection.style.display = 'none';
        loginSection.style.display = 'block';
        currentUser.inAiGame = false;
        toggleMobileFullscreenMode(false);
    });
    
    // Clear existing controls and add new buttons
    const controls = document.createElement('div');
    controls.appendChild(resetBtn);
    controls.appendChild(menuBtn);
    
    // Replace existing controls
    const existingControls = gameOverModal.querySelector('#admin-reset-controls');
    if (existingControls) {
        existingControls.innerHTML = '';
        existingControls.appendChild(controls);
        existingControls.style.display = 'block';
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
    
    // Exit mobile fullscreen mode
    toggleMobileFullscreenMode(false);
});

// Game controls for both multiplayer and single-player mode
document.addEventListener('keydown', (event) => {
    if (event.code === 'Space') {
        event.preventDefault(); // Prevent scrolling on space
        
        // Handle key controls for multiplayer mode
        if (currentUser.inGame) {
            socket.emit('update_position', {
                playerId: currentUser.id,
                action: 1  // Flap
            });
        }
        
        // Handle key controls for AI game mode
        if (currentUser.inAiGame) {
            socket.emit('update_ai_position', {
                action: 1  // Flap
            });
        }
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

// Handle mobile touch control for AI game
gameCanvas.addEventListener('touchstart', (event) => {
    if (currentUser.inAiGame) {
        socket.emit('update_ai_position', {
            action: 1  // Flap
        });
        event.preventDefault();
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

// Render AI game
function renderAiGame() {
    if (!aiGameState || !gameAssets.loaded) return;
    
    const ctx = gameCanvasContext;
    const canvas = gameCanvas;
    
    // Get metadata from game state
    const metadata = aiGameState._metadata;
    const gameData = metadata.game_data;
    
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
        
        // Now draw all upper pipes
        gameData.pipes.forEach(pipe => {
            const pipeX = pipe.x * scaleX;
            const upperY = (512 - 100 - pipe.lower_y - 100) * scaleY;
            console.log(pipe.lower_y)
            const pipeWidth = (gameData.pipe_width || 52) * scaleX;
            
            // Upper pipe - now use the same green color as lower pipes
            ctx.fillStyle = '#74BF2E'; // Match the lower pipe color
            ctx.fillRect(pipeX, 0, pipeWidth, upperY);
            
            // Border
            ctx.strokeStyle = '#528C1E';
            ctx.lineWidth = 4;
            ctx.strokeRect(pipeX, 0, pipeWidth, upperY);
        });
    }
    
    // Draw ground
    if (gameData.ground_y) {
        const groundY = gameData.ground_y * scaleY;
        ctx.drawImage(gameAssets.ground, 0, groundY, canvas.width, canvas.height - groundY);
    }
    
    // Draw player bird
    if (aiGameState.player.alive) {
        const playerPos = aiGameState.player.position;
        
        // Scale the positions
        const playerX = playerPos.x * scaleX;
        const playerY = playerPos.y * scaleY;
        const playerWidth = 34 * scaleX;
        const playerHeight = 24 * scaleY;
        
        // Apply rotation to the bird
        ctx.save();
        ctx.translate(playerX + playerWidth/2, playerY + playerHeight/2);
        ctx.rotate(playerPos.rotation * Math.PI / 180);
        ctx.translate(-(playerX + playerWidth/2), -(playerY + playerHeight/2));
        
        // Draw player bird - red color
        ctx.drawImage(
            gameAssets.bird.red,
            playerX, 
            playerY, 
            playerWidth, 
            playerHeight
        );
        
        ctx.restore();
        
        // Display player name above bird
        ctx.fillStyle = '#ff8c00'; // Orange color for player
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 2;
        ctx.font = `${12 * scaleX}px Arial`;
        ctx.textAlign = 'center';
        ctx.strokeText('You', playerX + playerWidth/2, playerY - 10 * scaleY);
        ctx.fillText('You', playerX + playerWidth/2, playerY - 10 * scaleY);
    }
    
    // Draw AI bird
    if (aiGameState.ai.alive) {
        const aiPos = aiGameState.ai.position;
        
        // Scale the positions
        const aiX = aiPos.x * scaleX;
        const aiY = aiPos.y * scaleY;
        const aiWidth = 34 * scaleX;
        const aiHeight = 24 * scaleY;
        
        // Apply rotation to the bird
        ctx.save();
        ctx.translate(aiX + aiWidth/2, aiY + aiHeight/2);
        ctx.rotate(aiPos.rotation * Math.PI / 180);
        ctx.translate(-(aiX + aiWidth/2), -(aiY + aiHeight/2));
        
        // Draw AI bird - yellow color
        ctx.drawImage(
            gameAssets.bird.yellow,
            aiX, 
            aiY, 
            aiWidth, 
            aiHeight
        );
        
        ctx.restore();
        
        // Display AI name above bird
        ctx.fillStyle = '#ffcc00'; // Yellow color for AI
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 2;
        ctx.font = `${12 * scaleX}px Arial`;
        ctx.textAlign = 'center';
        ctx.strokeText('AI', aiX + aiWidth/2, aiY - 10 * scaleY);
        ctx.fillText('AI', aiX + aiWidth/2, aiY - 10 * scaleY);
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

function updateAiGameDisplay() {
    if (!aiGameState) return;
    
    // Update player score
    const playerScore = Math.floor(aiGameState.player.score);
    gameOverlayScore.textContent = 'Score: ' + playerScore;
    
    // Update scoreboard
    playersScores.innerHTML = '';
    
    // Create player entry
    const playerRow = document.createElement('div');
    playerRow.className = `player-row ${aiGameState.player.alive ? 'alive' : 'dead'}`;
    playerRow.innerHTML = `
        <span class="player-name current-player">You</span>
        <span class="player-score">Score: ${playerScore}</span>
    `;
    playersScores.appendChild(playerRow);
    
    // Create AI entry
    const aiRow = document.createElement('div');
    aiRow.className = `player-row ${aiGameState.ai.alive ? 'alive' : 'dead'}`;
    aiRow.innerHTML = `
        <span class="player-name">AI</span>
        <span class="player-score">Score: ${Math.floor(aiGameState.ai.score)}</span>
    `;
    playersScores.appendChild(aiRow);
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