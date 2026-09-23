import { BarcodeDetector, setZXingModuleOverrides } from 'barcode-detector/ponyfill';

// zxing-wasm fetches its .wasm from a jsDelivr CDN by default. Serve our own copy
// out of `static/` instead, so the scanner works offline and on a LAN-only host.
// Keep `static/zxing_reader.wasm` in sync when bumping the barcode-detector dep.
setZXingModuleOverrides({
	locateFile: (path: string, prefix: string) =>
		path.endsWith('.wasm') ? '/zxing_reader.wasm' : prefix + path
});

export type QrDetector = InstanceType<typeof BarcodeDetector>;

export function createDetector(): QrDetector {
	return new BarcodeDetector({ formats: ['qr_code'] });
}
