import socket
import threading
import sys
import os
from datetime import datetime

# Dirección del servidor — se usa localhost (127.0.0.1) porque Docker publica el puerto en la máquina anfitriona
HOST = '127.0.0.1'
PORT = 5555

nombre_propio = [None]           # Estado compartido entre hilos mediante una lista mutable
nombre_listo = threading.Event() # Evento de sincronización que se dispara cuando el servidor asigna el nombre

def timestamp():
    return datetime.now().strftime("%H:%M:%S")

def recibir_mensajes(cliente_socket):
    # Al conectarse, se lanza este hilo en paralelo al hilo principal.
    # Mientras el hilo principal se bloquea esperando que el usuario escriba con input(),
    # este hilo de recepción escucha constantemente los mensajes del servidor;
    # gracias a esto no existen turnos y se pueden recibir mensajes de cualquiera en cualquier momento.
    while True:
        try:
            mensaje = cliente_socket.recv(1024).decode('utf-8')
            if not mensaje:
                print("\n[DESCONECTADO] El servidor cerro la conexion.")
                os._exit(0)
            
            # Para el nombre: el hilo detecta el identificador asignado en el mensaje de bienvenida,
            # lo guarda y dispara el evento (nombre_listo) que el hilo principal estaba esperando
            # antes de poder escribir, asegurando que quede registro de quién envió cada mensaje.
            if nombre_propio[0] is None and "Bienvenido [" in mensaje:
                nombre_propio[0] = mensaje.split("Bienvenido [")[1].split("]")[0]
                nombre_listo.set()
                
            print(f"\r{mensaje}\n", end="", flush=True)
        except Exception:
            print("\n[ERROR] Se perdio la conexion con el servidor.")
            os._exit(0)

def iniciar_cliente():
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        cliente.connect((HOST, PORT))
        print(f"Conectado al servidor en {HOST}:{PORT}")
        print("Escribe tus mensajes y presiona Enter para enviar.\n")
    except ConnectionRefusedError:
        print(f"[ERROR] No se pudo conectar a {HOST}:{PORT}. Verifica que el contenedor Docker este encendido.")
        return

    # Primero, al conectarse, se lanza el hilo de recepción en paralelo al hilo principal
    hilo_recepcion = threading.Thread(target=recibir_mensajes, args=(cliente,), daemon=True)
    hilo_recepcion.start()

    # El hilo principal permanece en espera hasta que el hilo de recepción dispare el evento con el nombre asignado
    nombre_listo.wait()

    try:
        # Una vez confirmado el nombre, el hilo principal se bloquea esperando el input() del usuario
        while True:
            mensaje = input()
            if mensaje.strip():
                # Al escribir /salir se rompe el bucle y se cierra la conexión limpiamente sin forzar Ctrl+C
                if mensaje.strip().lower() == '/salir':
                    print("Desconectando del chat...")
                    break
                # \033[F sube a la línea del input original y \033[K la borra para mostrar el mensaje formateado sin duplicarlo
                print(f"\033[F\033[K[{timestamp()}][{nombre_propio[0]}]: {mensaje}", flush=True)
                cliente.sendall(mensaje.encode('utf-8'))
    except KeyboardInterrupt:
        print("\nCerrando cliente...")
    finally:
        cliente.close()

if __name__ == '__main__':
    iniciar_cliente()