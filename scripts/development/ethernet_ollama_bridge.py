import os
import socket
import threading
import sys

LOCAL_HOST = os.getenv("OLLAMA_LOCAL_HOST", "0.0.0.0")
LOCAL_PORT = int(os.getenv("OLLAMA_LOCAL_PORT", "11434"))

REMOTE_HOST = sys.argv[1] if len(sys.argv) > 1 else os.getenv("OLLAMA_REMOTE_HOST", "169.254.88.2")
REMOTE_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else int(os.getenv("OLLAMA_REMOTE_PORT", "11434"))

CONNECT_TIMEOUT = float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "5.0"))

def forward(src, dst, direction):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except Exception:
            pass

def handle_client(client_socket, client_addr):
    remote_socket = None
    try:
        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        remote_socket.settimeout(CONNECT_TIMEOUT)
        remote_socket.connect((REMOTE_HOST, REMOTE_PORT))
        remote_socket.settimeout(None)
    except Exception as e:
        print(f"[Bridge] Failed to connect to remote {REMOTE_HOST}:{REMOTE_PORT}: {e}", flush=True)
        try:
            client_socket.close()
        except Exception:
            pass
        if remote_socket:
            try:
                remote_socket.close()
            except Exception:
                pass
        return

    print(f"[Bridge] Forwarding connection from {client_addr} to {REMOTE_HOST}:{REMOTE_PORT}", flush=True)

    t1 = threading.Thread(target=forward, args=(client_socket, remote_socket, "c2r"), daemon=True)
    t2 = threading.Thread(target=forward, args=(remote_socket, client_socket, "r2c"), daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    try:
        client_socket.close()
    except Exception:
        pass
    try:
        remote_socket.close()
    except Exception:
        pass

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((LOCAL_HOST, LOCAL_PORT))
    except Exception as e:
        print(f"[Bridge] Cannot bind to {LOCAL_HOST}:{LOCAL_PORT}: {e}", flush=True)
        sys.exit(1)

    server.listen(100)
    print(f"[Bridge] Listening on {LOCAL_HOST}:{LOCAL_PORT} -> Forwarding to {REMOTE_HOST}:{REMOTE_PORT}", flush=True)

    while True:
        try:
            client_socket, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True)
            t.start()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[Bridge] Accept error: {e}", flush=True)

if __name__ == "__main__":
    main()
