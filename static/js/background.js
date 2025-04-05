class BackgroundAnimation {
    constructor() {
        this.canvas = document.getElementById('background-canvas');
        this.ctx = this.canvas.getContext('2d');
        
        // Animation properties
        this.speed = 2;
        this.groundOffset = 0;
        this.pipeGap = 150;
        this.pipeSpacing = 300;
        this.pipes = [];
        this.lastPipeX = 0;
        
        // Load assets
        this.loadAssets().then(() => {
            this.resizeCanvas();
            window.addEventListener('resize', () => this.resizeCanvas());
            this.init();
            this.animate();
        });
    }

    async loadAssets() {
        // Load background
        this.bgImage = new Image();
        this.bgImage.src = '/static/sprites/background-day.png';
        await new Promise(resolve => this.bgImage.onload = resolve);

        // Load ground
        this.groundImage = new Image();
        this.groundImage.src = '/static/sprites/base.png';
        await new Promise(resolve => this.groundImage.onload = resolve);

        // Load pipe
        this.pipeImage = new Image();
        this.pipeImage.src = '/static/sprites/pipe-green.png';
        await new Promise(resolve => this.pipeImage.onload = resolve);

        // Create flipped pipe image
        this.flippedPipeImage = new Image();
        this.flippedPipeImage.src = '/static/sprites/pipe-green.png';
        await new Promise(resolve => this.flippedPipeImage.onload = resolve);
    }

    resizeCanvas() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        this.groundY = this.canvas.height - 100;
    }

    init() {
        // Initialize pipes
        this.pipes = [];
        this.lastPipeX = this.canvas.width;
        const numInitialPipes = Math.ceil(this.canvas.width / this.pipeSpacing) + 2;
        
        for (let i = 0; i < numInitialPipes; i++) {
            this.addPipe(this.lastPipeX);
            this.lastPipeX += this.pipeSpacing;
        }
    }

    addPipe(x) {
        const minHeight = 100;
        const maxHeight = this.groundY - this.pipeGap - 100;
        const height = Math.random() * (maxHeight - minHeight) + minHeight;
        
        this.pipes.push({
            x: x,
            height: height,
            counted: false
        });
    }

    animate() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw background (tiled)
        const bgWidth = this.canvas.width;
        const bgHeight = this.canvas.height;
        this.ctx.drawImage(this.bgImage, 0, 0, bgWidth, bgHeight);

        // Update and draw pipes
        for (let i = this.pipes.length - 1; i >= 0; i--) {
            const pipe = this.pipes[i];
            pipe.x -= this.speed;

            // Draw top pipe
            this.ctx.save();
            this.ctx.translate(pipe.x + this.pipeImage.width, pipe.height);
            this.ctx.scale(1, -1);
            this.ctx.drawImage(this.pipeImage, 0, 0);
            this.ctx.restore();

            // Draw bottom pipe
            this.ctx.drawImage(this.pipeImage, pipe.x, pipe.height + this.pipeGap);

            // Remove pipes that are off screen
            if (pipe.x + this.pipeImage.width < 0) {
                this.pipes.splice(i, 1);
                // Add a new pipe at the rightmost position
                this.addPipe(this.lastPipeX);
                this.lastPipeX += this.pipeSpacing;
            }
        }

        // Draw scrolling ground
        this.groundOffset = (this.groundOffset - this.speed) % this.groundImage.width;
        for (let i = 0; i <= this.canvas.width / this.groundImage.width + 1; i++) {
            this.ctx.drawImage(
                this.groundImage,
                this.groundOffset + i * this.groundImage.width,
                this.groundY
            );
        }

        // Continue animation
        requestAnimationFrame(() => this.animate());
    }
}

// Start the background animation when the page loads
window.addEventListener('load', () => {
    new BackgroundAnimation();
}); 