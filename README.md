# Chat en Tiempo Real — Python · Sockets TCP · Hilos · Docker <img src="https://cdn.pixabay.com/animation/2023/06/13/15/13/15-13-25-972_512.gif" width="40" style="vertical-align: middle;" alt="chat">

Aplicacion de chat distribuido que permite comunicacion en tiempo real entre un servidor dockerizado y multiples clientes conectados desde terminales locales. No hay turnos, cualquiera puede escribir y recibir en cualquier momento.

## Cómo funciona

* **Servidor (`server.py`):** Corre dentro de un contenedor Docker escuchando en `0.0.0.0:5555` y permanece en el hilo principal esperando conexiones. Al conectarse un cliente, se le asigna un nombre disponible de la lista de nombres libres (o se crea uno nuevo como `CLIENTE 1`, `CLIENTE 2`, etc.) y se lanza un hilo dedicado para atenderlo, permitiendo que varios usuarios escriban al mismo tiempo.
  * **Recepción y Broadcast:** En el hilo del cliente se envía un mensaje de bienvenida y se entra en un bucle de recepción. Cada mensaje recibido se valida en tamaño (máximo 500 caracteres) antes de reenviarse mediante `broadcast()` a los demás sockets conectados.
  * **Control de concurrencia (`clientes_lock`):** Como múltiples hilos interactúan con la lista de clientes al mismo tiempo, se utiliza un `threading.Lock()` para garantizar que solo un hilo la modifique a la vez y evitar condiciones de carrera (*race conditions*).
  * **Desconexión:** Cuando un cliente se desconecta, `recv()` devuelve vacío, finalizando el bucle. El bloque `finally` se encarga de cerrar el socket, quitarlo de la lista activa y liberar su nombre para que pueda ser reutilizado.

* **Cliente (`cliente.py`):** Al conectarse a `127.0.0.1:5555`, lanza un hilo de recepción en paralelo al hilo principal. Mientras el hilo principal se bloquea esperando que el usuario escriba con `input()`, el hilo de recepción escucha los mensajes del servidor en todo momento.
  * **Sincronización de nombre:** El hilo de recepción detecta el nombre asignado en el mensaje de bienvenida y dispara un evento (`threading.Event`) que el hilo principal espera antes de habilitar la escritura, asegurando que siempre quede registro de quién envía cada mensaje.

Los mensajes llevan timestamp con hora local de Ecuador (`America/Guayaquil`) y el servidor notifica globalmente cuando alguien entra o sale del chat.

## Tecnologías

| Componente | Detalle |
|---|---|
| Protocolo | TCP (`socket.SOCK_STREAM`) en puerto `5555` |
| Concurrencia | `threading` (`Lock` en servidor para exclusión mutua, `Event` en cliente para sincronización) |
| Contenedor | Docker + Docker Compose |
| Zona horaria | `America/Guayaquil` (UTC-5) |

## Requisitos

- Docker y Docker Compose instalados
- Python 3.x instalado en la máquina local

## Ejecución

### Terminal 1 — Levantar el servidor

```bash
docker compose up --build -d
docker attach servidor_chat_tcp
```

Una vez adjunto al contenedor, todo lo que escribas se enviara a los clientes como `[SERVIDOR]`.

### Terminal 2 — Cliente 1

```bash
python cliente.py
```

### Terminal 3 — Cliente 2

```bash
python cliente.py
```

## Comandos disponibles

| Comando | Efecto |
|---|---|
| `/salir` | Desconecta al cliente limpiamente |
| `Ctrl+C` | Cierra el cliente y/o apaga el servidor |
| `Ctrl+P` + `Ctrl+Q` | Se desconecta del contenedor sin apagar el servidor |

## Apagar todo

```bash
En la terminal de servidor: Ctrl+C
En cada terminal de cliente: Ctrl+C o escribir /salir
```
