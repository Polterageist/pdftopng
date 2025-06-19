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
        // Check KTX1 or KTX2 identifier
        const ktx1 = [0xAB, 0x4B, 0x54, 0x58, 0x20, 0x31, 0x31, 0xBB, 0x0D, 0x0A, 0x1A, 0x0A];
        const ktx2 = [0xAB, 0x4B, 0x54, 0x58, 0x20, 0x32, 0x30, 0xBB, 0x0D, 0x0A, 0x1A, 0x0A];
        let isKTX2 = true;
        for (let i = 0; i < ktx2.length; i++) {
            if (data[i] !== ktx2[i]) {
                isKTX2 = false;
                break;
            }
        }
        let isKTX1 = true;
        for (let i = 0; i < ktx1.length; i++) {
            if (data[i] !== ktx1[i]) {
                isKTX1 = false;
                break;
            }
        }
        if (!isKTX1 && !isKTX2) {
            throw new Error('Invalid KTX file');
        }
        if (isKTX2) {
            // KTX2 header parsing (see spec)
            const view = new DataView(buffer);
            const pixelWidth = view.getUint32(36, true);
            const pixelHeight = view.getUint32(40, true);
            const numberOfMipmapLevels = view.getUint32(52, true);
            // Supercompression, DFD, etc. are ignored for simple ETC1S/ETC2
            // Level index table starts at offset 68
            let levelIndexOffset = 68;
            let mipmaps = [];
            let width = pixelWidth;
            let height = pixelHeight;
            for (let level = 0; level < numberOfMipmapLevels; level++) {
                const levelOffset = Number(view.getBigUint64(levelIndexOffset + 8 * level, true));
                const levelLength = Number(view.getBigUint64(levelIndexOffset + 8 * level + 8 * numberOfMipmapLevels, true));
                const levelData = new Uint8Array(buffer, levelOffset, levelLength);
                mipmaps.push({
                    data: levelData,
                    width: Math.max(1, width >> level),
                    height: Math.max(1, height >> level)
                });
            }
            // glInternalFormat is not present in KTX2, use vkFormat
            const vkFormat = view.getUint32(28, true);
            const texture = new THREE.CompressedTexture(mipmaps, pixelWidth, pixelHeight, this.getThreeFormat(vkFormat));
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
            case 0x9274: return THREE.RGB_ETC2_Format; // GL_COMPRESSED_RGB8_ETC2 (ETC2/ETC1S)
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
