import socket
import threading
import sys
from datetime import datetime

# Configuracion de red — 0.0.0.0 es fundamental en Docker para escuchar en todas las interfaces del contenedor
HOST = '0.0.0.0'
PORT = 5555

clientes = []
nombres_clientes = {}  # {socket: nombre} — permite saber el nombre de cada socket conectado
nombres_libres = []    # nombres liberados por desconexiones, disponibles para reusar
clientes_lock = threading.Lock()  # clientes_lock es importante ya que como varios hilos pueden interactuar
                                  # con la lista clientes, el lock garantiza que solo uno la modifique a la vez
                                  # para que no exista condicion de carrera
contador_clientes = 0

def timestamp():
    return datetime.now().strftime("%H:%M:%S")

def broadcast(mensaje, cliente_emisor=None):
    # Recorre la lista y reenvía el mensaje a todos los sockets, excepto al que lo envió
    with clientes_lock:
        for cliente in clientes[:]:
            if cliente != cliente_emisor:
                try:
                    cliente.sendall(mensaje.encode('utf-8'))
                except Exception:
                    # Si el envío falla el cliente se desconecto — se limpia sin bloquear
                    clientes.remove(cliente)
                    cliente.close()

def manejar_cliente(cliente_socket, nombre_cliente):
    # En el hilo del cliente, se manda un mensaje de bienvenida con quienes estan conectados
    try:
        with clientes_lock:
            otros = [n for s, n in nombres_clientes.items() if s != cliente_socket]
        contexto = f"En el chat: {', '.join(otros)}." if otros else "Eres el primero en conectarte."
        bienvenida = f"[{timestamp()}][SERVIDOR]: Bienvenido [{nombre_cliente}]. {contexto}"
        cliente_socket.sendall(bienvenida.encode('utf-8'))

        # Entra a un bucle en el que recibe los mensajes
        while True:
            mensaje = cliente_socket.recv(1024).decode('utf-8')
            if not mensaje:
                break
            # Al recibir uno, primero se valida el tamaño (<500) antes de distribuirlo
            if len(mensaje) > 500:
                cliente_socket.sendall(f"[{timestamp()}][SERVIDOR]: Mensaje demasiado largo (max 500 caracteres).".encode('utf-8'))
                continue
            # Si pasa la validacion, se manda a broadcast que lo reenvia a los demas sockets de la lista
            mensaje_formateado = f"[{timestamp()}][{nombre_cliente}]: {mensaje}"
            print(mensaje_formateado, flush=True)
            broadcast(mensaje_formateado, cliente_emisor=cliente_socket)

    except ConnectionResetError:
        pass
    except Exception as e:
        print(f"[ERROR CON {nombre_cliente}]: {e}", flush=True)
    finally:
        # Cuando el recv() devuelve vacio finaliza el bucle y el finally lo quita de la lista liberando su nombre
        with clientes_lock:
            if cliente_socket in clientes:
                clientes.remove(cliente_socket)
            if cliente_socket in nombres_clientes:
                nombres_libres.append(nombres_clientes.pop(cliente_socket))
                nombres_libres.sort(key=lambda x: int(x.split()[-1]))  # mantener orden: 1, 2, 3...
        cliente_socket.close()
        aviso = f"[{timestamp()}][SERVIDOR]: {nombre_cliente} ha abandonado el chat."
        print(aviso, flush=True)
        broadcast(aviso)

def enviar_mensajes_servidor():
    # Hilo para que el operador del servidor pueda escribir mensajes desde la consola Docker
    while True:
        try:
            texto = sys.stdin.readline().strip()
            if texto:
                mensaje_formateado = f"[{timestamp()}][SERVIDOR]: {texto}"
                print(mensaje_formateado, flush=True)
                broadcast(mensaje_formateado, cliente_emisor=None)
        except EOFError:
            break
        except Exception as e:
            print(f"[ERROR DE ENTRADA EN SERVIDOR]: {e}", flush=True)
            break

def iniciar_servidor():
    global contador_clientes

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # permite reusar el puerto si el servidor se reinicia
    servidor.bind((HOST, PORT))
    servidor.listen()

    print(f"[{timestamp()}] === SERVIDOR INICIADO EN {HOST}:{PORT} ===", flush=True)
    print("Esperando conexiones... Puedes escribir mensajes aqui.", flush=True)

    hilo_escritura = threading.Thread(target=enviar_mensajes_servidor, daemon=True)
    hilo_escritura.start()

    # El servidor se queda en el hilo principal hasta que alguien se conecte
    while True:
        try:
            cliente_socket, direccion = servidor.accept()

            with clientes_lock:
                # Se asigna un nombre al cliente, uno que este libre, o se crea uno nuevo si no hay
                if nombres_libres:
                    nombre_cliente = nombres_libres.pop(0)
                else:
                    contador_clientes += 1
                    nombre_cliente = f"CLIENTE {contador_clientes}"
                clientes.append(cliente_socket)
                nombres_clientes[cliente_socket] = nombre_cliente

            print(f"[{timestamp()}][CONEXION] {direccion} -> [{nombre_cliente}]", flush=True)

            # Se avisa a los ya conectados que llego alguien nuevo
            aviso_union = f"[{timestamp()}][SERVIDOR]: {nombre_cliente} se unio al chat. ({len(clientes)} conectado(s))"
            broadcast(aviso_union, cliente_emisor=cliente_socket)

            # Se lanza un hilo para el uso de ese cliente, permitiendo a varios conectarse y escribir al mismo tiempo
            hilo_cliente = threading.Thread(
                target=manejar_cliente,
                args=(cliente_socket, nombre_cliente),
                daemon=True
            )
            hilo_cliente.start()

        except KeyboardInterrupt:
            # Cierre limpio — avisa a los clientes y cierra todos los sockets ordenadamente
            print("\n[SERVIDOR] Apagando servidor...", flush=True)
            broadcast(f"[{timestamp()}][SERVIDOR]: El servidor se esta apagando. Hasta pronto.")
            with clientes_lock:
                for c in clientes:
                    try: c.close()
                    except: pass
                clientes.clear()
            servidor.close()
            break

if __name__ == '__main__':
    iniciar_servidor()
