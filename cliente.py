import socket
import threading
import sys
import os
from datetime import datetime

# Direccion del servidor — localhost porque Docker publica el puerto en la maquina local
HOST = '127.0.0.1'
PORT = 5555

nombre_propio = [None]           # compartido entre hilos usando lista mutable
nombre_listo = threading.Event() # evento que se dispara cuando ya se conoce el nombre asignado

def timestamp():
    return datetime.now().strftime("%H:%M:%S")

def recibir_mensajes(cliente_socket):
    # Al conectarse se lanza este hilo en paralelo al hilo principal
    # el hilo principal se bloquea esperando que el usuario escriba con input()
    # mientras este hilo escucha los mensajes del servidor
    # por lo que no hay turnos y puede recibir mensaje de cualquiera en cualquier momento
    while True:
        try:
            mensaje = cliente_socket.recv(1024).decode('utf-8')
            if not mensaje:
                print("\n[DESCONECTADO] El servidor cerro la conexion.")
                os._exit(0)
            # El hilo detecta el nombre asignado en el primer mensaje y dispara el evento
            # el hilo principal estaba esperando ese evento antes de dejar escribir
            # para asegurar que quede registro de quien escribio
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

    hilo_recepcion = threading.Thread(target=recibir_mensajes, args=(cliente,), daemon=True)
    hilo_recepcion.start()

    # Espera hasta que el hilo de recepcion dispare el evento con el nombre
    nombre_listo.wait()

    try:
        while True:
            mensaje = input()
            if mensaje.strip():
                # Al escribir /salir se cierra la conexion limpiamente sin forzar Ctrl+C
                if mensaje.strip().lower() == '/salir':
                    print("Desconectando del chat...")
                    break
                # \033[F sube al renglon del input crudo y \033[K lo borra para evitar que salga duplicado
                print(f"\033[F\033[K[{timestamp()}][{nombre_propio[0]}]: {mensaje}", flush=True)
                cliente.sendall(mensaje.encode('utf-8'))
    except KeyboardInterrupt:
        print("\nCerrando cliente...")
    finally:
        cliente.close()

if __name__ == '__main__':
    iniciar_cliente()
