// KTX Loader for Three.js
// Based on the official Three.js KTXLoader but simplified for our use case

class KTXLoader {
    constructor() {
        this.loader = new THREE.FileLoader();
        this.loader.setResponseType('arraybuffer');
    }
    
    load(url, onLoad, onProgress, onError) {
        this.loader.load(url, (buffer) => {
            try {
                const texture = this.parse(buffer);
                if (onLoad) onLoad(texture);
            } catch (error) {
                if (onError) onError(error);
            }
        }, onProgress, onError);
    }
    
    parse(buffer) {
        // KTX file format parsing
        const data = new Uint8Array(buffer);
        
        // Check KTX identifier
        const identifier = [0xAB, 0x4B, 0x54, 0x58, 0x20, 0x31, 0x31, 0xBB, 0x0D, 0x0A, 0x1A, 0x0A];
        for (let i = 0; i < identifier.length; i++) {
            if (data[i] !== identifier[i]) {
                throw new Error('Invalid KTX file');
            }
        }
        
        // Read header
        const littleEndian = new Uint32Array(buffer, 12, 1)[0] === 0x04030201;
        const view = new DataView(buffer);
        
        const glType = view.getUint32(16, littleEndian);
        const glTypeSize = view.getUint32(20, littleEndian);
        const glFormat = view.getUint32(24, littleEndian);
        const glInternalFormat = view.getUint32(28, littleEndian);
        const glBaseInternalFormat = view.getUint32(32, littleEndian);
        const pixelWidth = view.getUint32(36, littleEndian);
        const pixelHeight = view.getUint32(40, littleEndian);
        const pixelDepth = view.getUint32(44, littleEndian);
        const numberOfArrayElements = view.getUint32(48, littleEndian);
        const numberOfFaces = view.getUint32(52, littleEndian);
        const numberOfMipmapLevels = view.getUint32(56, littleEndian);
        const bytesOfKeyValueData = view.getUint32(60, littleEndian);
        
        // Skip key/value data
        let offset = 64 + bytesOfKeyValueData;
        
        // For compressed textures, create a CompressedTexture
        if (glType === 0) { // Compressed
            const texture = new THREE.CompressedTexture();
            texture.image = { width: pixelWidth, height: pixelHeight };
            texture.mipmaps = [];
            
            // Read mipmap levels
            for (let level = 0; level < numberOfMipmapLevels; level++) {
                const imageSize = view.getUint32(offset, littleEndian);
                offset += 4;
                
                const levelData = new Uint8Array(buffer, offset, imageSize);
                texture.mipmaps.push({
                    data: levelData,
                    width: Math.max(1, pixelWidth >> level),
                    height: Math.max(1, pixelHeight >> level)
                });
                
                offset += imageSize;
                // Pad to 4-byte boundary
                offset = (offset + 3) & ~3;
            }
            
            // Set format based on glInternalFormat
            texture.format = this.getThreeFormat(glInternalFormat);
            texture.type = THREE.UnsignedByteType;
            texture.generateMipmaps = false;
            texture.needsUpdate = true;
            
            return texture;
        } else {
            // Uncompressed texture - convert to regular DataTexture
            const imageSize = view.getUint32(offset, littleEndian);
            offset += 4;
            
            const levelData = new Uint8Array(buffer, offset, imageSize);
            
            const texture = new THREE.DataTexture(
                levelData,
                pixelWidth,
                pixelHeight,
                this.getThreeFormat(glFormat),
                this.getThreeType(glType)
            );
            
            texture.needsUpdate = true;
            return texture;
        }
    }
    
    getThreeFormat(glFormat) {
        // Map OpenGL formats to Three.js formats
        switch (glFormat) {
            case 0x1907: return THREE.RGBFormat; // GL_RGB
            case 0x1908: return THREE.RGBAFormat; // GL_RGBA
            case 0x1909: return THREE.LuminanceFormat; // GL_LUMINANCE
            case 0x190A: return THREE.LuminanceAlphaFormat; // GL_LUMINANCE_ALPHA
            
            // Compressed formats
            case 0x83F0: return THREE.RGBA_S3TC_DXT1_Format; // GL_COMPRESSED_RGB_S3TC_DXT1_EXT
            case 0x83F1: return THREE.RGBA_S3TC_DXT1_Format; // GL_COMPRESSED_RGBA_S3TC_DXT1_EXT
            case 0x83F2: return THREE.RGBA_S3TC_DXT3_Format; // GL_COMPRESSED_RGBA_S3TC_DXT3_EXT
            case 0x83F3: return THREE.RGBA_S3TC_DXT5_Format; // GL_COMPRESSED_RGBA_S3TC_DXT5_EXT
            
            default:
                console.warn('Unknown KTX format:', glFormat);
                return THREE.RGBAFormat;
        }
    }
    
    getThreeType(glType) {
        // Map OpenGL types to Three.js types
        switch (glType) {
            case 0x1401: return THREE.UnsignedByteType; // GL_UNSIGNED_BYTE
            case 0x1403: return THREE.UnsignedShortType; // GL_UNSIGNED_SHORT
            case 0x1405: return THREE.UnsignedIntType; // GL_UNSIGNED_INT
            case 0x1406: return THREE.FloatType; // GL_FLOAT
            default:
                console.warn('Unknown KTX type:', glType);
                return THREE.UnsignedByteType;
        }
    }
}

// Export for use in main.js
window.KTXLoader = KTXLoader;
