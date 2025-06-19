import * as THREE from 'three';

// Simple camera controls replacement for OrbitControls
class SimpleControls {
    constructor(camera, domElement) {
        this.camera = camera;
        this.domElement = domElement;
        this.target = new THREE.Vector3(0, 0, 0);
        this.enableDamping = true;
        this.dampingFactor = 0.05;
        this.screenSpacePanning = false;
        this.minDistance = 100;
        this.maxDistance = 5000;
        this.enableRotate = true;
        this.minPolarAngle = 0;
        this.maxPolarAngle = Math.PI;
        this.minAzimuthAngle = -Infinity;
        this.maxAzimuthAngle = Infinity;
        
        this.isMouseDown = false;
        this.lastMouseX = 0;
        this.lastMouseY = 0;
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        this.domElement.addEventListener('mousedown', (e) => {
            this.isMouseDown = true;
            this.lastMouseX = e.clientX;
            this.lastMouseY = e.clientY;
        });
        
        this.domElement.addEventListener('mouseup', () => {
            this.isMouseDown = false;
        });
        
        this.domElement.addEventListener('mousemove', (e) => {
            if (!this.isMouseDown) return;
            
            const deltaX = e.clientX - this.lastMouseX;
            const deltaY = e.clientY - this.lastMouseY;
            
            // Simple pan control
            const distance = this.camera.position.distanceTo(this.target);
            const factor = distance * 0.001;
            
            this.target.x -= deltaX * factor;
            this.target.y += deltaY * factor;
            this.camera.position.x -= deltaX * factor;
            this.camera.position.y += deltaY * factor;
            
            this.lastMouseX = e.clientX;
            this.lastMouseY = e.clientY;
        });
        
        this.domElement.addEventListener('wheel', (e) => {
            e.preventDefault();
            const factor = e.deltaY > 0 ? 1.1 : 0.9;
            this.camera.position.multiplyScalar(factor);
        });
    }
    
    update() {
        this.camera.lookAt(this.target);
    }
}

// Make it available globally like OrbitControls
THREE.OrbitControls = SimpleControls;
