# Chat en Tiempo Real — Python · Sockets TCP · Hilos · Docker

Aplicacion de chat distribuido que permite comunicacion en tiempo real entre un servidor dockerizado y multiples clientes conectados desde terminales locales. No hay turnos, cualquiera puede escribir y recibir en cualquier momento.

## Como funciona

El servidor corre dentro de un contenedor Docker y se queda esperando conexiones. Cada vez que un cliente se conecta, el servidor le asigna un nombre automaticamente (CLIENTE 1, CLIENTE 2, etc.) y lanza un hilo dedicado para ese cliente, lo que permite que varios esten conectados y escribiendo al mismo tiempo sin que uno bloquee al otro.

Cada cliente tambien usa dos hilos: uno que se queda esperando que el usuario escriba, y otro que escucha los mensajes que llegan del servidor. Asi se puede recibir un mensaje de cualquier participante en cualquier momento mientras se esta escribiendo.

Los mensajes llevan timestamp con hora local de Ecuador, se validan antes de distribuirse (maximo 500 caracteres), y el servidor notifica cuando alguien entra o sale del chat.

## Tecnologias

| Componente | Detalle |
|---|---|
| Protocolo | TCP (`socket.SOCK_STREAM`) |
| Concurrencia | `threading` — un hilo por cliente + hilo de escritura del servidor |
| Contenedor | Docker + Docker Compose |
| Zona horaria | `America/Guayaquil` (UTC-5) |

## Requisitos

- Docker y Docker Compose instalados
- Python 3.x instalado en la maquina local

## Ejecucion

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
