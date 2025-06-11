class TileViewer {
    constructor() {
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.tiles = [];
        this.tileGroup = null;
        this.is3D = false;
        this.gridWidth = 0;
        this.gridHeight = 0;        this.tileSize = 256; // Default tile size
        this.loadedTiles = 0;
        this.totalTiles = 0;
        this.minimapEnabled = false;
        this.minimapCanvas = null;
        this.minimapCtx = null;
        
        this.init();
        this.setupEventListeners();
    }
    
    init() {
        // Create scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x222222);
        
        // Create camera
        const aspect = window.innerWidth / window.innerHeight;
        this.camera = new THREE.PerspectiveCamera(75, aspect, 0.1, 10000);
        this.camera.position.set(0, 0, 1000);
        
        // Create renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        
        document.getElementById('container').appendChild(this.renderer.domElement);
          // Create controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = false;
        this.controls.minDistance = 100;
        this.controls.maxDistance = 5000;
        
        // Set 2D mode by default
        this.set2DMode();
        
        // Create tile group
        this.tileGroup = new THREE.Group();
        this.scene.add(this.tileGroup);
        
        // Add lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
        this.scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
        directionalLight.position.set(0, 0, 1000);
        this.scene.add(directionalLight);
        
        // Start render loop
        this.animate();
    }
    
    setupEventListeners() {
        // File input and load button
        const fileInput = document.getElementById('fileInput');
        const loadButton = document.getElementById('loadButton');
          fileInput.addEventListener('change', (e) => {
            console.log('Files selected:', e.target.files.length);
            loadButton.disabled = false;
        });
          loadButton.addEventListener('click', () => {
            console.log('Load button clicked, files:', fileInput.files.length);
            this.loadTiles(fileInput.files);
        });
        
        // Minimap toggle
        const toggleMinimap = document.getElementById('toggleMinimap');        toggleMinimap.addEventListener('click', () => {
            this.toggleMinimap();
        });
        
        // Fullscreen toggle
        const fullscreenButton = document.getElementById('fullscreenButton');
        fullscreenButton.addEventListener('click', () => {
            this.toggleFullscreen();
        });
          // Keyboard controls
        window.addEventListener('keydown', (e) => {
            switch(e.key.toLowerCase()) {
                case 'r':
                    this.resetView();
                    break;
                case 't':
                    this.toggle3D();
                    break;
                case 'f':
                    this.fitToScreen();
                    break;
                case '+':
                case '=':
                    this.zoomIn();
                    break;
                case '-':
                    this.zoomOut();
                    break;
                case 'arrowup':
                    this.pan(0, 50);
                    break;
                case 'arrowdown':
                    this.pan(0, -50);
                    break;
                case 'arrowleft':
                    this.pan(50, 0);
                    break;                case 'arrowright':
                    this.pan(-50, 0);
                    break;
                case 's':
                    this.saveViewSettings();
                    break;                case 'l':
                    this.loadViewSettings();
                    break;
                case 'f11':
                case 'f':
                    if (e.key === 'f11' || (e.key === 'f' && e.ctrlKey)) {
                        e.preventDefault();
                        this.toggleFullscreen();
                    }
                    break;
            }
        });
          // Window resize
        window.addEventListener('resize', () => {
            this.camera.aspect = window.innerWidth / window.innerHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(window.innerWidth, window.innerHeight);
        });
        
        // Drag and drop support
        this.setupDragAndDrop();
    }
    
    async loadTiles(files) {
        if (!files || files.length === 0) return;
        
        this.clearTiles();
        this.showProgress(true);
        this.updateStatus('Analyzing files...');
        
        // Parse tile files
        const tileFiles = this.parseTileFiles(files);
        
        if (tileFiles.length === 0) {
            this.updateStatus('No valid tile files found');
            this.showProgress(false);
            return;
        }
        
        this.totalTiles = tileFiles.length;
        this.loadedTiles = 0;
        
        // Determine grid size
        const { gridWidth, gridHeight } = this.calculateGridSize(tileFiles);
        this.gridWidth = gridWidth;
        this.gridHeight = gridHeight;
        
        // Update UI
        document.getElementById('tileCount').textContent = this.totalTiles;
        document.getElementById('gridSize').textContent = `${gridWidth}x${gridHeight}`;
        
        // Detect format
        const format = this.detectFormat(tileFiles[0].name);
        document.getElementById('format').textContent = format;
        
        this.updateStatus(`Loading ${this.totalTiles} tiles...`);
        
        // Load tiles progressively
        await this.loadTilesProgressively(tileFiles);
        
        // Center view on loaded tiles
        this.centerView();
        
        this.showProgress(false);
        this.updateStatus('Loading complete');
    }
    
    parseTileFiles(files) {
        const tileFiles = [];
        const tilePattern = /.*-tile-(\d+)-(\d+)\.(png|ktx|ktx2)$/i;
        
        for (const file of files) {
            const match = file.name.match(tilePattern);
            if (match) {
                tileFiles.push({
                    file: file,
                    name: file.name,
                    x: parseInt(match[1]),
                    y: parseInt(match[2]),
                    format: match[3].toLowerCase()
                });
            }
        }
        
        // Sort by position
        tileFiles.sort((a, b) => {
            if (a.x !== b.x) return a.x - b.x;
            return a.y - b.y;
        });
        
        return tileFiles;
    }
    
    calculateGridSize(tileFiles) {
        let maxX = 0, maxY = 0;
        
        for (const tile of tileFiles) {
            maxX = Math.max(maxX, tile.x);
            maxY = Math.max(maxY, tile.y);
        }
        
        return {
            gridWidth: maxX + 1,
            gridHeight: maxY + 1
        };
    }
    
    detectFormat(filename) {
        if (filename.toLowerCase().endsWith('.ktx2')) return 'KTX2';
        if (filename.toLowerCase().endsWith('.ktx')) return 'KTX';
        if (filename.toLowerCase().endsWith('.png')) return 'PNG';
        return 'Unknown';
    }
    
    async loadTilesProgressively(tileFiles) {
        const batchSize = 4; // Load tiles in batches
        
        for (let i = 0; i < tileFiles.length; i += batchSize) {
            const batch = tileFiles.slice(i, Math.min(i + batchSize, tileFiles.length));
            const promises = batch.map(tileData => this.loadSingleTile(tileData));
            
            await Promise.all(promises);
            
            this.updateProgress((i + batchSize) / tileFiles.length * 100);
        }
    }
    
    async loadSingleTile(tileData) {
        return new Promise((resolve, reject) => {
            const { file, x, y, format } = tileData;
            
            if (format === 'png') {
                this.loadPNGTile(file, x, y, resolve, reject);
            } else if (format === 'ktx' || format === 'ktx2') {
                this.loadKTXTile(file, x, y, resolve, reject);
            } else {
                reject(new Error(`Unsupported format: ${format}`));
            }
        });
    }
    
    loadPNGTile(file, x, y, resolve, reject) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const loader = new THREE.TextureLoader();
            loader.load(e.target.result, (texture) => {
                this.createTileMesh(texture, x, y);
                this.loadedTiles++;
                resolve();
            }, undefined, reject);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    }
      loadKTXTile(file, x, y, resolve, reject) {
        // Try to load actual KTX file
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const ktxLoader = new KTXLoader();
                const buffer = e.target.result;
                const texture = ktxLoader.parse(buffer);
                this.createTileMesh(texture, x, y);
                this.loadedTiles++;
                resolve();
            } catch (error) {
                console.warn(`Failed to load KTX tile ${x},${y}:`, error);
                // Fall back to placeholder
                this.createKTXPlaceholder(x, y);
                this.loadedTiles++;
                resolve();
            }
        };
        reader.onerror = () => {
            // Fall back to placeholder
            this.createKTXPlaceholder(x, y);
            this.loadedTiles++;
            resolve();
        };
        reader.readAsArrayBuffer(file);
    }
    
    createKTXPlaceholder(x, y) {
        const canvas = document.createElement('canvas');
        canvas.width = this.tileSize;
        canvas.height = this.tileSize;
        const ctx = canvas.getContext('2d');
        
        // Create a placeholder pattern
        ctx.fillStyle = '#333';
        ctx.fillRect(0, 0, this.tileSize, this.tileSize);
        ctx.fillStyle = '#666';
        ctx.font = '20px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('KTX', this.tileSize/2, this.tileSize/2 - 10);
        ctx.fillText(`${x},${y}`, this.tileSize/2, this.tileSize/2 + 15);
        
        const texture = new THREE.CanvasTexture(canvas);
        this.createTileMesh(texture, x, y);
    }
    
    createTileMesh(texture, x, y) {
        // Create geometry
        const geometry = new THREE.PlaneGeometry(this.tileSize, this.tileSize);
        
        // Create material
        const material = new THREE.MeshBasicMaterial({ 
            map: texture,
            transparent: true
        });
        
        // Create mesh
        const mesh = new THREE.Mesh(geometry, material);
        
        // Position the tile
        mesh.position.x = x * this.tileSize - (this.gridWidth - 1) * this.tileSize / 2;
        mesh.position.y = -y * this.tileSize + (this.gridHeight - 1) * this.tileSize / 2;
        mesh.position.z = 0;
        
        // Add to group
        this.tileGroup.add(mesh);
        this.tiles.push(mesh);
    }
    
    clearTiles() {
        while (this.tileGroup.children.length > 0) {
            const child = this.tileGroup.children[0];
            this.tileGroup.remove(child);
            
            // Dispose of geometry and material
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (child.material.map) child.material.map.dispose();
                child.material.dispose();
            }
        }
        this.tiles = [];
        this.loadedTiles = 0;
        this.totalTiles = 0;
    }
    
    centerView() {
        if (this.tiles.length === 0) return;
        
        // Calculate bounding box
        const box = new THREE.Box3().setFromObject(this.tileGroup);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        
        // Position camera to see all tiles
        const maxDim = Math.max(size.x, size.y);
        const distance = maxDim / (2 * Math.tan(this.camera.fov * Math.PI / 360));
        
        this.camera.position.set(center.x, center.y, distance * 1.2);
        this.controls.target.copy(center);
        this.controls.update();
    }
      resetView() {
        this.centerView();
    }
    
    fitToScreen() {
        this.centerView();
    }
    
    zoomIn() {
        this.camera.position.multiplyScalar(0.8);
        this.controls.update();
        this.updateInfoDisplay();
    }
    
    zoomOut() {
        this.camera.position.multiplyScalar(1.25);
        this.controls.update();
        this.updateInfoDisplay();
    }
    
    pan(deltaX, deltaY) {
        const distance = this.camera.position.distanceTo(this.controls.target);
        const factor = distance * 0.001;
        
        this.controls.target.x += deltaX * factor;
        this.controls.target.y += deltaY * factor;
        this.camera.position.x += deltaX * factor;
        this.camera.position.y += deltaY * factor;
        
        this.controls.update();
        this.updateInfoDisplay();
    }
    
    updateInfoDisplay() {
        // Update zoom level
        const distance = this.camera.position.distanceTo(this.controls.target);
        const zoomLevel = Math.round((1000 / distance) * 100);
        document.getElementById('zoomLevel').textContent = `${zoomLevel}%`;
        
        // Update position
        const pos = this.controls.target;
        document.getElementById('position').textContent = `${Math.round(pos.x)}, ${Math.round(pos.y)}`;
    }
    
    toggle3D() {
        this.is3D = !this.is3D;
        
        if (this.is3D) {
            this.set3DMode();
        } else {
            this.set2DMode();
        }
    }
    
    set2DMode() {
        this.is3D = false;
        this.controls.enableRotate = false;
        this.controls.minPolarAngle = 0;
        this.controls.maxPolarAngle = 0;
        this.controls.minAzimuthAngle = 0;
        this.controls.maxAzimuthAngle = 0;
        
        // Reset rotation
        this.camera.position.z = Math.abs(this.camera.position.z);
        this.camera.lookAt(this.controls.target);
        this.controls.update();
    }
    
    set3DMode() {
        this.is3D = true;
        this.controls.enableRotate = true;
        this.controls.minPolarAngle = 0;
        this.controls.maxPolarAngle = Math.PI;
        this.controls.minAzimuthAngle = -Infinity;
        this.controls.maxAzimuthAngle = Infinity;
    }
    
    showProgress(show) {
        const progress = document.getElementById('progress');
        progress.style.display = show ? 'block' : 'none';
        if (!show) {
            this.updateProgress(0);
        }
    }
    
    updateProgress(percent) {
        const progressBar = document.getElementById('progressBar');
        progressBar.style.width = `${Math.min(100, Math.max(0, percent))}%`;
    }
      updateStatus(message) {
        document.getElementById('status').textContent = message;
    }
    
    setupDragAndDrop() {
        const dropZone = document.getElementById('dropZone');
        const container = document.getElementById('container');
        
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            container.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
        
        // Highlight drop zone when dragging over
        ['dragenter', 'dragover'].forEach(eventName => {
            container.addEventListener(eventName, () => {
                dropZone.classList.add('active');
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            container.addEventListener(eventName, () => {
                dropZone.classList.remove('active');
            });
        });
        
        // Handle dropped files
        container.addEventListener('drop', (e) => {
            const files = [...e.dataTransfer.files];
            if (files.length > 0) {
                this.loadTiles(files);
            }
        });
    }
      animate() {
        requestAnimationFrame(() => this.animate());
        
        this.controls.update();
        
        // Update info display periodically
        if (this.frameCount % 30 === 0) { // Every 30 frames
            this.updateInfoDisplay();
        }
        this.frameCount = (this.frameCount || 0) + 1;
          this.renderer.render(this.scene, this.camera);
        
        // Update minimap if enabled
        if (this.minimapEnabled && this.frameCount % 60 === 0) { // Every 60 frames
            this.updateMinimap();
        }
    }
    
    toggleMinimap() {
        this.minimapEnabled = !this.minimapEnabled;
        const minimap = document.getElementById('minimap');
        
        if (this.minimapEnabled) {
            minimap.style.display = 'block';
            this.initMinimap();
        } else {
            minimap.style.display = 'none';
        }
    }
    
    initMinimap() {
        if (!this.minimapCanvas) {
            this.minimapCanvas = document.getElementById('minimapCanvas');
            this.minimapCtx = this.minimapCanvas.getContext('2d');
            
            // Set canvas size
            this.minimapCanvas.width = 200;
            this.minimapCanvas.height = 150;
        }
        
        this.updateMinimap();
    }
    
    updateMinimap() {
        if (!this.minimapEnabled || !this.minimapCtx || this.tiles.length === 0) return;
        
        const ctx = this.minimapCtx;
        const canvas = this.minimapCanvas;
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Calculate scaling
        const box = new THREE.Box3().setFromObject(this.tileGroup);
        const size = box.getSize(new THREE.Vector3());
        const scale = Math.min(canvas.width / size.x, canvas.height / size.y) * 0.8;
        
        // Draw tiles as rectangles
        ctx.fillStyle = '#666';
        for (const tile of this.tiles) {
            const x = (tile.position.x - box.min.x) * scale + (canvas.width - size.x * scale) / 2;
            const y = (tile.position.y - box.min.y) * scale + (canvas.height - size.y * scale) / 2;
            const w = this.tileSize * scale;
            const h = this.tileSize * scale;
            
            ctx.fillRect(x, canvas.height - y - h, w, h);
        }
        
        // Draw viewport indicator
        const center = this.controls.target;
        const distance = this.camera.position.distanceTo(center);
        const viewSize = distance * 0.5; // Approximate view size
        
        const viewX = (center.x - box.min.x) * scale + (canvas.width - size.x * scale) / 2;
        const viewY = (center.y - box.min.y) * scale + (canvas.height - size.y * scale) / 2;
        const viewW = viewSize * scale;
        const viewH = viewSize * scale;
          ctx.strokeStyle = '#4CAF50';
        ctx.lineWidth = 2;
        ctx.strokeRect(viewX - viewW/2, canvas.height - viewY - viewH/2, viewW, viewH);
    }
    
    saveViewSettings() {
        const settings = {
            cameraPosition: {
                x: this.camera.position.x,
                y: this.camera.position.y,
                z: this.camera.position.z
            },
            controlsTarget: {
                x: this.controls.target.x,
                y: this.controls.target.y,
                z: this.controls.target.z
            },
            is3D: this.is3D,
            minimapEnabled: this.minimapEnabled
        };
        
        localStorage.setItem('tileViewerSettings', JSON.stringify(settings));
        this.updateStatus('View settings saved');
        setTimeout(() => this.updateStatus('Ready'), 2000);
    }
    
    loadViewSettings() {
        try {
            const settingsJson = localStorage.getItem('tileViewerSettings');
            if (!settingsJson) {
                this.updateStatus('No saved settings found');
                setTimeout(() => this.updateStatus('Ready'), 2000);
                return;
            }
            
            const settings = JSON.parse(settingsJson);
            
            // Restore camera position
            this.camera.position.set(
                settings.cameraPosition.x,
                settings.cameraPosition.y,
                settings.cameraPosition.z
            );
            
            // Restore controls target
            this.controls.target.set(
                settings.controlsTarget.x,
                settings.controlsTarget.y,
                settings.controlsTarget.z
            );
            
            // Restore 3D mode
            if (settings.is3D !== this.is3D) {
                this.toggle3D();
            }
            
            // Restore minimap
            if (settings.minimapEnabled !== this.minimapEnabled) {
                this.toggleMinimap();
            }
            
            this.controls.update();
            this.updateInfoDisplay();
            this.updateStatus('View settings loaded');
            setTimeout(() => this.updateStatus('Ready'), 2000);
            
        } catch (error) {
            console.warn('Failed to load settings:', error);
            this.updateStatus('Failed to load settings');            setTimeout(() => this.updateStatus('Ready'), 2000);
        }
    }
    
    toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(err => {
                console.warn('Failed to enter fullscreen:', err);
            });
        } else {
            document.exitFullscreen().catch(err => {
                console.warn('Failed to exit fullscreen:', err);
            });
        }
    }
}

// Initialize the viewer when the page loads
window.addEventListener('DOMContentLoaded', () => {
    new TileViewer();
});