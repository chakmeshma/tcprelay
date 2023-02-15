import socket
import threading

NET_MSG_SIZE = 1024

running = 1

relay_local_bind_address = '0.0.0.0'
relay_local_bind_port = 5633
relay_remote_address = '83.170.219.86'
relay_remote_port = 8081


def createNewListenSocket(hostname, port):
    s = None

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((hostname, port))
    s.listen()

    return s


def createNewConnectSocket(hostname, port):
    s = None

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostname, port))

    return s


def handleRelay(relayacceptedsocket, tunnelhost, tunnelport):
    tunnelsocket = None

    try:
        global running

        tunnelsocket = createNewConnectSocket(tunnelhost, tunnelport)
        print(f'New connection made to {tunnelsocket.getpeername()}')

        relayacceptedsocket.setblocking(False)
        tunnelsocket.setblocking(False)

        while running:
            try:
                relay_data = relayacceptedsocket.recv(NET_MSG_SIZE)
                if relay_data:
                    tunnelsocket.send(relay_data)
            except socket.error as e:
                if e.args[0] != socket.EAGAIN and e.args[0] != socket.EWOULDBLOCK:
                    raise e

            try:
                tunnel_data = tunnelsocket.recv(NET_MSG_SIZE)
                if tunnel_data:
                    relayacceptedsocket.send(tunnel_data)
            except socket.error as e:
                if e.args[0] != socket.EAGAIN and e.args[0] != socket.EWOULDBLOCK:
                    raise e
    except:
        pass
    finally:
        if tunnelsocket:
            tunnelsocket.close()
        if relayacceptedsocket:
            relayacceptedsocket.close()
        print('Closed a connection')


def createRelayServer(relayhost, relayport):
    global running

    relaysocket = createNewListenSocket(relayhost, relayport)

    try:
        while running:
            relayacceptedsocket, relayacceptedaddr = relaysocket.accept()

            print(f"Accepted new connection from {relayacceptedaddr}")

            relay_thread = threading.Thread(target=handleRelay,
                                            args=(relayacceptedsocket, relay_remote_address, relay_remote_port))
            relay_thread.start()
    except:
        pass
    finally:
        if relaysocket:
            relaysocket.close()


createRelayServer(relay_local_bind_address, relay_local_bind_port)
