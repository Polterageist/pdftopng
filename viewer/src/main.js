import * as THREE from 'three';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';

class TileViewer {
    constructor() {
        this.scene = null;
        this.camera = null;
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.tiles = [];
        this.tileGroup = null;
        this.gridWidth = 0;
        this.gridHeight = 0;
        this.tileSize = 256; // Default tile size
        this.loadedTiles = 0;
        this.totalTiles = 0;
        this.minimapEnabled = false;
        this.minimapCanvas = null;
        this.minimapCtx = null;
        this.isPanning = false;
        this.lastPointer = { x: 0, y: 0 };
        this.zoom = 1;
        this.minZoom = 0.1;
        this.maxZoom = 40;
        this.pan = { x: 0, y: 0 };
        this.showTileBorders = false;
        this.showTileCoords = false;
        this.tileBorders = [];
        this.tileLabels = [];

        // Create renderer DOM element early
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        document.getElementById('container').appendChild(this.renderer.domElement);

        this.init();
        this.setupEventListeners();
    }
    getRenderer() {
        // Возвращает renderer, если уже создан
        return this.renderer;
    }

    init() {
        // Create scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x222222);

        // Create orthographic camera for 2D
        const aspect = window.innerWidth / window.innerHeight;
        const viewSize = 1000;
        this.camera = new THREE.OrthographicCamera(
            -viewSize * aspect / 2, viewSize * aspect / 2,
            viewSize / 2, -viewSize / 2, -1000, 1000
        );
        this.camera.position.set(0, 0, 10);
        this.camera.lookAt(0, 0, 0);
        // camera.up.set(0, -1, 0); // Не трогаем up, стандартная ориентация
        // Убираем поворот и обратную сторону

        this.ktx2Loader = new KTX2Loader()
            .setTranscoderPath('/basis/') // Vite: put basis_transcoder.wasm/js in public/basis/
            .detectSupport(this.renderer);

        // Create tile group
        this.tileGroup = new THREE.Group();
        this.scene.add(this.tileGroup);

        // Start render loop
        this.animate();
    }

    setupEventListeners() {
        // File input and load button
        const fileInput = document.getElementById('fileInput');
        const loadButton = document.getElementById('loadButton');
        fileInput.addEventListener('change', (e) => {
            loadButton.disabled = false;
        });
        loadButton.addEventListener('click', () => {
            this.loadTiles(fileInput.files);
        });

        // Minimap toggle
        const toggleMinimap = document.getElementById('toggleMinimap');
        toggleMinimap.addEventListener('click', () => {
            this.toggleMinimap();
        });

        // Fullscreen toggle
        const fullscreenButton = document.getElementById('fullscreenButton');
        fullscreenButton.addEventListener('click', () => {
            this.toggleFullscreen();
        });

        // Tile borders toggle
        const toggleBorders = document.getElementById('toggleBorders');
        if (toggleBorders) {
            toggleBorders.addEventListener('click', () => {
                this.toggleTileBorders();
            });
        }

        // Tile coordinates toggle
        const toggleCoords = document.getElementById('toggleCoords');
        if (toggleCoords) {
            toggleCoords.addEventListener('click', () => {
                this.toggleTileCoords();
            });
        }

        // 2D mouse/touch controls
        const canvas = this.renderer.domElement;
        canvas.addEventListener('mousedown', (e) => {
            this.isPanning = true;
            this.lastPointer = { x: e.clientX, y: e.clientY };
        });
        window.addEventListener('mousemove', (e) => {
            if (this.isPanning) {
                const dx = e.clientX - this.lastPointer.x;
                const dy = e.clientY - this.lastPointer.y;
                this.pan.x += dx / this.zoom;
                this.pan.y -= dy / this.zoom;
                this.lastPointer = { x: e.clientX, y: e.clientY };
                this.updateCamera();
            }
        });
        window.addEventListener('mouseup', () => {
            this.isPanning = false;
        });
        canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const oldZoom = this.zoom;
            if (e.deltaY < 0) {
                this.zoom = Math.min(this.maxZoom, this.zoom * 1.2);
            } else {
                this.zoom = Math.max(this.minZoom, this.zoom / 1.2);
            }
            // Zoom to mouse position
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left - rect.width / 2;
            const my = rect.height / 2 - (e.clientY - rect.top);
            this.pan.x += mx * (1 / oldZoom - 1 / this.zoom);
            this.pan.y += my * (1 / oldZoom - 1 / this.zoom);
            this.updateCamera();
        }, { passive: false });

        // Keyboard controls (only zoom and pan)
        window.addEventListener('keydown', (e) => {
            switch (e.key.toLowerCase()) {
                case '+':
                case '=':
                    this.zoom = Math.min(this.maxZoom, this.zoom * 1.2);
                    this.updateCamera();
                    break;
                case '-':
                    this.zoom = Math.max(this.minZoom, this.zoom / 1.2);
                    this.updateCamera();
                    break;
                case 'arrowup':
                    this.pan.y += 50 / this.zoom;
                    this.updateCamera();
                    break;
                case 'arrowdown':
                    this.pan.y -= 50 / this.zoom;
                    this.updateCamera();
                    break;
                case 'arrowleft':
                    this.pan.x -= 50 / this.zoom;
                    this.updateCamera();
                    break;
                case 'arrowright':
                    this.pan.x += 50 / this.zoom;
                    this.updateCamera();
                    break;
                case 's':
                    this.saveViewSettings();
                    break;
                case 'l':
                    this.loadViewSettings();
                    break;
                case 'f11':
                    e.preventDefault();
                    this.toggleFullscreen();
                    break;
                case 'b':
                    this.toggleTileBorders();
                    break;
                case 'c':
                    this.toggleTileCoords();
                    break;
            }
        });

        // Window resize
        window.addEventListener('resize', () => {
            const aspect = window.innerWidth / window.innerHeight;
            const viewSize = 1000;
            this.camera.left = -viewSize * aspect / 2;
            this.camera.right = viewSize * aspect / 2;
            this.camera.top = viewSize / 2;
            this.camera.bottom = -viewSize / 2;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(window.innerWidth, window.innerHeight);
        });
    }

    updateCamera() {
        this.camera.zoom = this.zoom;
        this.camera.position.x = this.pan.x;
        this.camera.position.y = this.pan.y;
        this.camera.updateProjectionMatrix();
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
        const tilePattern = /.*_(\d+)_(\d+).*\.(png|ktx|ktx2)$/i;

        for (const file of files) {
            const match = file.name.match(tilePattern);
            if (match) {
                tileFiles.push({
                    file: file,
                    name: file.name,
                    x: parseInt(match[1]) - 1, // Convert from 1-based to 0-based indexing
                    y: parseInt(match[2]) - 1, // Convert from 1-based to 0-based indexing
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

    // Calculate tile position in world coordinates
    calculateTilePosition(x, y) {
        // Инверсия по y для корректной сшивки: y = gridHeight - 1 - y
        const invY = this.gridHeight - 1 - y;
        
        return {
            x: x * this.tileSize - (this.gridWidth * this.tileSize) / 2 + this.tileSize / 2,
            y: invY * this.tileSize - (this.gridHeight * this.tileSize) / 2 + this.tileSize / 2,
            z: 0
        };
    }

    // Обновляет значение прогресс-бара (0-100)
    updateProgress(percent) {
        const progressBar = document.getElementById('progressBar');
        if (!progressBar) return;
        progressBar.value = percent;
        progressBar.style.display = 'block';
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

            console.log(`Loading single tile ${x},${y} with format ${format}`);

            try {
                if (format === 'png') {
                    this.loadPNGTile(file, x, y, resolve, reject);
                } else if (format === 'ktx' || format === 'ktx2') {
                    this.loadKTXTile(file, x, y, resolve, reject);
                } else {
                    console.error(`Unsupported format for tile ${x},${y}: ${format}`);
                    reject(new Error(`Unsupported format: ${format}`));
                }
            } catch (error) {
                console.error(`Error in loadSingleTile for ${x},${y}:`, error);
                reject(error);
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
        console.log(`Starting to load KTX tile ${x},${y}:`, {
            fileName: file.name,
            fileSize: file.size,
            fileType: file.type
        });

        const reader = new FileReader();
        reader.onload = (e) => {
            const buffer = e.target.result;
            console.log(`FileReader loaded buffer for tile ${x},${y}, size:`, buffer.byteLength);
            if (!this.ktx2Loader) {
                console.warn('KTX2Loader is not initialized');
                this.createKTXPlaceholder(x, y, 'NO LOADER');
                this.loadedTiles++;
                resolve();
                return;
            }
            // Используем асинхронный вариант parse с onLoad/onError
            this.ktx2Loader.parse(
                buffer,
                (texture) => {
                    console.log(`Successfully loaded KTX2 texture for tile ${x},${y}`, texture);
                    // For KTX2 with pre-baked mipmaps, don't generate new ones
                    texture.minFilter = THREE.LinearMipmapLinearFilter;
                    texture.magFilter = THREE.LinearFilter;
                    texture.generateMipmaps = false; // Use pre-baked mipmaps from KTX2
                    texture.needsUpdate = true;
                    texture.anisotropy = this.renderer.capabilities.getMaxAnisotropy()
                    this.createTileMesh(texture, x, y);
                    this.loadedTiles++;
                    resolve();
                },
                (err) => {
                    console.error(`KTX2Loader.parse error for tile ${x},${y}:`, err);
                    const header = new Uint8Array(buffer, 0, Math.min(32, buffer.byteLength));
                    console.warn(`Buffer header for tile ${x},${y}:`, header);
                    this.createKTXPlaceholder(x, y, 'PARSE ERR');
                    this.loadedTiles++;
                    resolve();
                }
            );
        };
        reader.onerror = (errorEvent) => {
            console.error(`FileReader error for KTX tile ${x},${y}:`, errorEvent);
            console.error('FileReader error details:', {
                fileName: file.name,
                fileSize: file.size,
                fileType: file.type,
                error: reader.error
            });
            this.createKTXPlaceholder(x, y, 'READ ERR');
            this.loadedTiles++;
            resolve();
        };
        reader.readAsArrayBuffer(file);
    } 
    
    createKTXPlaceholder(x, y, errorMsg = 'KTX') {
        console.log(`Creating KTX placeholder for tile ${x},${y} with error: ${errorMsg}`);

        const canvas = document.createElement('canvas');
        canvas.width = this.tileSize;
        canvas.height = this.tileSize;
        const ctx = canvas.getContext('2d');

        // Create a placeholder pattern
        ctx.fillStyle = '#333';
        ctx.fillRect(0, 0, this.tileSize, this.tileSize);
        ctx.fillStyle = '#ff6666'; // Red color for error indication
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('ERROR', this.tileSize / 2, this.tileSize / 2 - 20);
        ctx.fillStyle = '#666';
        ctx.font = '12px Arial';
        ctx.fillText(errorMsg, this.tileSize / 2, this.tileSize / 2);
        ctx.fillText(`${x+1},${y+1}`, this.tileSize / 2, this.tileSize / 2 + 20); // Display 1-based coordinates

        const texture = new THREE.CanvasTexture(canvas);
        texture.minFilter = THREE.LinearFilter;
        texture.magFilter = THREE.LinearFilter;
        texture.generateMipmaps = false;
        this.createTileMesh(texture, x, y);
    }

    createTileMesh(texture, x, y) {
        // Apply proper filtering for PNG textures only
        if (texture.minFilter === THREE.NearestFilter) {
            texture.minFilter = THREE.LinearFilter;
            texture.magFilter = THREE.LinearFilter;
            texture.generateMipmaps = true; // Only for PNG textures
        }
        texture.needsUpdate = true;

        // Create geometry
        const geometry = new THREE.PlaneGeometry(this.tileSize, this.tileSize);
        // Инвертируем UV только по Y для BufferGeometry
        // const uv = geometry.attributes.uv;
        // for (let i = 0; i < uv.count; i++) {
        //     uv.setY(i, 1 - uv.getY(i));
        // }
        // uv.needsUpdate = true;

        // Create material
        const material = new THREE.MeshBasicMaterial({
            map: texture,
            transparent: true
        });

        // Корректируем позиционирование: (0,0) — top-left, x вправо, y вниз
        const mesh = new THREE.Mesh(geometry, material);
        
        // Use the shared position calculation function
        const position = this.calculateTilePosition(x, y);
        mesh.position.x = position.x;
        mesh.position.y = position.y;
        mesh.position.z = position.z;

        // Add to group
        this.tileGroup.add(mesh);
        this.tiles.push(mesh);

        // Create tile border if enabled
        if (this.showTileBorders) {
            this.createTileBorder(x, y);
        }

        // Create tile coordinate label if enabled
        if (this.showTileCoords) {
            this.createTileLabel(x, y);
        }
    }

    createTileBorder(x, y) {
        // Create border geometry (wireframe box)
        const borderGeometry = new THREE.EdgesGeometry(
            new THREE.PlaneGeometry(this.tileSize, this.tileSize)
        );
        
        const borderMaterial = new THREE.LineBasicMaterial({ 
            color: 0x00ff00, 
            linewidth: 2,
            transparent: true,
            opacity: 0.8
        });
        
        const borderMesh = new THREE.LineSegments(borderGeometry, borderMaterial);
        
        // Use the shared position calculation function
        const position = this.calculateTilePosition(x, y);
        borderMesh.position.x = position.x;
        borderMesh.position.y = position.y;
        borderMesh.position.z = 0.1; // Slightly above tile
        
        this.tileGroup.add(borderMesh);
        this.tileBorders.push(borderMesh);
    }

    createTileLabel(x, y) {
        // Create canvas for text
        const canvas = document.createElement('canvas');
        canvas.width = 128;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        
        // Draw text
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        ctx.fillStyle = 'white';
        ctx.font = 'bold 14px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(`${x+1},${y+1}`, canvas.width / 2, canvas.height / 2 + 5); // Display 1-based coordinates
        
        // Create texture and material
        const texture = new THREE.CanvasTexture(canvas);
        texture.minFilter = THREE.LinearFilter;
        texture.magFilter = THREE.LinearFilter;
        
        const labelMaterial = new THREE.MeshBasicMaterial({
            map: texture,
            transparent: true,
            alphaTest: 0.1
        });
        
        const labelGeometry = new THREE.PlaneGeometry(64, 32);
        const labelMesh = new THREE.Mesh(labelGeometry, labelMaterial);
        
        // Use the shared position calculation function
        const position = this.calculateTilePosition(x, y);
        labelMesh.position.x = position.x;
        labelMesh.position.y = position.y;
        labelMesh.position.z = 0.2; // Above border
        
        this.tileGroup.add(labelMesh);
        this.tileLabels.push(labelMesh);
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

        // Clear borders and labels
        this.clearTileBorders();
        this.clearTileLabels();
    }

    clearTileBorders() {
        while (this.tileBorders.length > 0) {
            const border = this.tileBorders.pop();
            this.tileGroup.remove(border);
            if (border.geometry) border.geometry.dispose();
            if (border.material) border.material.dispose();
        }
    }

    clearTileLabels() {
        while (this.tileLabels.length > 0) {
            const label = this.tileLabels.pop();
            this.tileGroup.remove(label);
            if (label.geometry) label.geometry.dispose();
            if (label.material) {
                if (label.material.map) label.material.map.dispose();
                label.material.dispose();
            }
        }
    }

    toggleTileBorders() {
        this.showTileBorders = !this.showTileBorders;
        
        const button = document.getElementById('toggleBorders');
        if (button) {
            button.classList.toggle('active', this.showTileBorders);
        }
        
        if (this.showTileBorders) {
            // Create borders for all existing tiles
            this.recreateTileBorders();
            this.updateStatus('Tile borders enabled (B to toggle)');
        } else {
            // Clear all borders
            this.clearTileBorders();
            this.updateStatus('Tile borders disabled (B to toggle)');
        }
        
        setTimeout(() => this.updateStatus('Ready'), 2000);
    }

    toggleTileCoords() {
        this.showTileCoords = !this.showTileCoords;
        
        const button = document.getElementById('toggleCoords');
        if (button) {
            button.classList.toggle('active', this.showTileCoords);
        }
        
        if (this.showTileCoords) {
            // Create labels for all existing tiles
            this.recreateTileLabels();
            this.updateStatus('Tile coordinates enabled (C to toggle)');
        } else {
            // Clear all labels
            this.clearTileLabels();
            this.updateStatus('Tile coordinates disabled (C to toggle)');
        }
        
        setTimeout(() => this.updateStatus('Ready'), 2000);
    }

    recreateTileBorders() {
        this.clearTileBorders();
        
        for (let x = 0; x < this.gridWidth; x++) {
            for (let y = 0; y < this.gridHeight; y++) {
                this.createTileBorder(x, y);
            }
        }
    }

    recreateTileLabels() {
        this.clearTileLabels();
        
        for (let x = 0; x < this.gridWidth; x++) {
            for (let y = 0; y < this.gridHeight; y++) {
                this.createTileLabel(x, y);
            }
        }
    }

    centerView() {
        if (this.tiles.length === 0) return;

        // Calculate bounding box
        const box = new THREE.Box3().setFromObject(this.tileGroup);
        const center = box.getCenter(new THREE.Vector3());

        this.pan.x = center.x;
        this.pan.y = center.y;
        this.zoom = 1;
        this.updateCamera();
    }

    resetView() {
        this.centerView();
    }

    zoomIn() {
        this.zoom = Math.min(this.maxZoom, this.zoom * 1.2);
        this.updateCamera();
        this.updateInfoDisplay();
    }

    zoomOut() {
        this.zoom = Math.max(this.minZoom, this.zoom / 1.2);
        this.updateCamera();
        this.updateInfoDisplay();
    }

    updateInfoDisplay() {
        const zoomLevel = Math.round(this.zoom * 100);
        document.getElementById('zoomLevel').textContent = `${zoomLevel}%`;
        document.getElementById('position').textContent = `${Math.round(this.pan.x)}, ${Math.round(this.pan.y)}`;
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
        const center = this.pan;
        const distance = this.zoom * 500; // Approximate view size

        const viewX = (center.x - box.min.x) * scale + (canvas.width - size.x * scale) / 2;
        const viewY = (center.y - box.min.y) * scale + (canvas.height - size.y * scale) / 2;
        const viewW = distance * scale;
        const viewH = distance * scale;
        ctx.strokeStyle = '#4CAF50';
        ctx.lineWidth = 2;
        ctx.strokeRect(viewX - viewW / 2, canvas.height - viewY - viewH / 2, viewW, viewH);
    }

    saveViewSettings() {
        const settings = {
            pan: { ...this.pan },
            zoom: this.zoom,
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
            if (settings.pan) {
                this.pan.x = settings.pan.x;
                this.pan.y = settings.pan.y;
            }
            if (settings.zoom) {
                this.zoom = settings.zoom;
            }
            if (typeof settings.minimapEnabled === 'boolean' && settings.minimapEnabled !== this.minimapEnabled) {
                this.toggleMinimap();
            }
            this.updateCamera();
            this.updateInfoDisplay();
            this.updateStatus('View settings loaded');
            setTimeout(() => this.updateStatus('Ready'), 2000);
        } catch (error) {
            console.warn('Failed to load settings:', error);
            this.updateStatus('Failed to load settings');
            setTimeout(() => this.updateStatus('Ready'), 2000);
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

    showProgress(visible) {
        // Показывает или скрывает прогресс-бар загрузки
        const progressBar = document.getElementById('progressBar');
        if (!progressBar) return;
        progressBar.style.display = visible ? 'block' : 'none';
        if (!visible) {
            this.updateProgress(0);
        }
    }

    updateStatus(text) {
        // Показывает текст статуса в элементе statusBar
        const statusBar = document.getElementById('statusBar');
        if (statusBar) {
            statusBar.textContent = text;
        }
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        this.renderer.render(this.scene, this.camera);

        // Update info display periodically
        if (this.frameCount % 30 === 0) { // Every 30 frames
            this.updateInfoDisplay();
        }
        this.frameCount = (this.frameCount || 0) + 1;

        // Update minimap if enabled
        if (this.minimapEnabled && this.frameCount % 60 === 0) { // Every 60 frames
            this.updateMinimap();
        }
    }
}

// Initialize the viewer when the page loads
window.addEventListener('DOMContentLoaded', () => {
    new TileViewer();
});