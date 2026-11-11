import socket
import threading
import sys
from datetime import datetime

# Configuración de red — 0.0.0.0 es necesario en Docker para escuchar en todas las interfaces del contenedor
HOST = '0.0.0.0'
PORT = 5555

clientes = []
nombres_clientes = {}  # {socket: nombre} — asocia cada socket activo con su identificador asignado
nombres_libres = []    # Almacena nombres liberados tras desconexiones para que puedan ser reutilizados
# clientes_lock es fundamental: como varios hilos interactúan con la lista de clientes al mismo tiempo,
# el lock garantiza que solo un hilo la modifique a la vez, evitando condiciones de carrera (race conditions).
clientes_lock = threading.Lock()  
contador_clientes = 0

def timestamp():
    return datetime.now().strftime("%H:%M:%S")

def broadcast(mensaje, cliente_emisor=None):
    # Recorre la lista de clientes y reenvía el mensaje a todos los sockets conectados, excepto al emisor
    with clientes_lock:
        for cliente in clientes[:]:
            if cliente != cliente_emisor:
                try:
                    cliente.sendall(mensaje.encode('utf-8'))
                except Exception:
                    # Si el envío falla, se asume que el cliente se desconectó y se remueve sin bloquear el servidor
                    clientes.remove(cliente)
                    cliente.close()

def manejar_cliente(cliente_socket, nombre_cliente):
    # En el hilo del cliente, se envía primero un mensaje de bienvenida indicando quiénes están conectados
    try:
        with clientes_lock:
            otros = [n for s, n in nombres_clientes.items() if s != cliente_socket]
        contexto = f"En el chat: {', '.join(otros)}." if otros else "Eres el primero en conectarte."
        bienvenida = f"[{timestamp()}][SERVIDOR]: Bienvenido [{nombre_cliente}]. {contexto}"
        cliente_socket.sendall(bienvenida.encode('utf-8'))

        # Entra en un bucle continuo para recibir los mensajes de este cliente en particular
        while True:
            mensaje = cliente_socket.recv(1024).decode('utf-8')
            # Cuando el cliente se desconecta, recv() devuelve vacío y se rompe el bucle
            if not mensaje:
                break
            
            # Al recibir un mensaje, primero se valida su longitud (máximo 500 caracteres) antes de procesarlo
            if len(mensaje) > 500:
                cliente_socket.sendall(f"[{timestamp()}][SERVIDOR]: Mensaje demasiado largo (max 500 caracteres).".encode('utf-8'))
                continue
            
            # Si pasa la validación, se formatea y se envía a broadcast() para reenviarlo a los demás sockets de la lista
            mensaje_formateado = f"[{timestamp()}][{nombre_cliente}]: {mensaje}"
            print(mensaje_formateado, flush=True)
            broadcast(mensaje_formateado, cliente_emisor=cliente_socket)

    except ConnectionResetError:
        pass
    except Exception as e:
        print(f"[ERROR CON {nombre_cliente}]: {e}", flush=True)
    finally:
        # Al finalizar el bucle por desconexión, el bloque finally elimina al cliente de la lista y libera su nombre
        with clientes_lock:
            if cliente_socket in clientes:
                clientes.remove(cliente_socket)
            if cliente_socket in nombres_clientes:
                nombres_libres.append(nombres_clientes.pop(cliente_socket))
                nombres_libres.sort(key=lambda x: int(x.split()[-1]))  # Mantiene el orden numérico: 1, 2, 3...
        cliente_socket.close()
        aviso = f"[{timestamp()}][SERVIDOR]: {nombre_cliente} ha abandonado el chat."
        print(aviso, flush=True)
        broadcast(aviso)

def enviar_mensajes_servidor():
    # Hilo secundario para que el administrador del servidor pueda enviar mensajes globales desde la consola
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
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Permite reutilizar el puerto inmediatamente tras reiniciar el servidor
    servidor.bind((HOST, PORT))
    servidor.listen()

    print(f"[{timestamp()}] === SERVIDOR INICIADO EN {HOST}:{PORT} ===", flush=True)
    print("Esperando conexiones... Puedes escribir mensajes aqui.", flush=True)

    hilo_escritura = threading.Thread(target=enviar_mensajes_servidor, daemon=True)
    hilo_escritura.start()

    # El servidor permanece en el hilo principal esperando a que nuevos clientes se conecten
    while True:
        try:
            cliente_socket, direccion = servidor.accept()

            with clientes_lock:
                # Se asigna un nombre de la lista de nombres libres; si no hay disponibles, se genera uno nuevo
                if nombres_libres:
                    nombre_cliente = nombres_libres.pop(0)
                else:
                    contador_clientes += 1
                    nombre_cliente = f"CLIENTE {contador_clientes}"
                clientes.append(cliente_socket)
                nombres_clientes[cliente_socket] = nombre_cliente

            print(f"[{timestamp()}][CONEXION] {direccion} -> [{nombre_cliente}]", flush=True)

            # Se notifica a los demás clientes conectados sobre el nuevo ingreso
            aviso_union = f"[{timestamp()}][SERVIDOR]: {nombre_cliente} se unio al chat. ({len(clientes)} conectado(s))"
            broadcast(aviso_union, cliente_emisor=cliente_socket)

            # Se lanza un hilo independiente para atender a este cliente, permitiendo que varios se conecten y escriban al mismo tiempo
            hilo_cliente = threading.Thread(
                target=manejar_cliente,
                args=(cliente_socket, nombre_cliente),
                daemon=True
            )
            hilo_cliente.start()

        except KeyboardInterrupt:
            # Cierre limpio — notifica a los clientes y cierra todos los sockets activos de forma ordenada
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