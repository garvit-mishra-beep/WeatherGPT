"""WeatherGPT Developer Backend QR Code Generator.

Generates a QR code containing the developer's local backend URL
for instant physical Android device connectivity during debug testing.

Usage:
    python scripts/generate_backend_qr.py [--url http://<IP>:8000/] [--port 8000]

Note:
    Contains ZERO hardcoded personal IP addresses or credentials.
    The URL payload is strictly a network endpoint (e.g. http://192.168.1.50:8000/).
"""

import argparse
import os
import socket
import sys


def get_local_lan_ip() -> str:
    """Discovers the primary local LAN IPv4 address dynamically."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually connect, just resolves outbound route interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def print_ascii_qr(data: str):
    """Renders QR code in ASCII terminal safely across all operating systems."""
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        print("\n" + "=" * 50)
        print("SCAN QR CODE WITH ANDROID DEVICE:")
        print("=" * 50)
        
        # Safe text-based ASCII matrix rendering that never crashes on cp1252 Windows consoles
        matrix = qr.get_matrix()
        for row in matrix:
            line = "".join("██" if cell else "  " for cell in row)
            try:
                print(line)
            except UnicodeEncodeError:
                # Fallback to pure ASCII '#' / ' ' if Windows terminal doesn't support unicode block
                ascii_line = "".join("##" if cell else "  " for cell in row)
                print(ascii_line)
        print("=" * 50)
    except ImportError:
        print("\n" + "=" * 50)
        print(f"BACKEND URL PAYLOAD: {data}")
        print("=" * 50)
        print("(Tip: Install 'qrcode' via 'pip install qrcode' for in-terminal ASCII QR rendering)")


def main():
    parser = argparse.ArgumentParser(description="Generate QR code for local WeatherGPT Android debugging.")
    parser.add_argument("--url", type=str, default=None, help="Explicit backend URL (e.g. http://192.168.1.50:8000/)")
    parser.add_argument("--port", type=int, default=8000, help="Backend port (default: 8000)")
    parser.add_argument("--output", type=str, default=None, help="Optional image output file path (e.g. qr.png)")
    args = parser.parse_args()

    if args.url:
        target_url = args.url.strip()
    else:
        lan_ip = get_local_lan_ip()
        target_url = f"http://{lan_ip}:{args.port}/"

    if not target_url.endswith("/"):
        target_url += "/"

    print(f"\n[WeatherGPT Developer Tool]")
    print(f"Configured Backend Endpoint: {target_url}")

    print_ascii_qr(target_url)

    if args.output:
        try:
            import qrcode
            img = qrcode.make(target_url)
            img.save(args.output)
            print(f"[OK] QR Code saved to: {args.output}")
        except ImportError:
            print("[WARN] Pillow / qrcode not installed; could not save image.")


if __name__ == "__main__":
    main()
