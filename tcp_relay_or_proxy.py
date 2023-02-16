import socket
import threading

NET_MSG_SIZE = 1024
running = False
log_enabled = True


def _createNewListenSocket(hostname: str, port: int) -> socket.socket:
    s = None

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((hostname, port))
    s.listen()

    return s


def _createNewConnectSocket(hostname: str, port: int) -> socket.socket:
    s = None

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostname, port))

    return s


def _handleRelay(relayacceptedsocket: socket.socket, proxy_mode: bool = True, target_name: str = None,
                 target_port: int = None):
    global running
    global NET_MSG_SIZE

    tunnelsocket = None

    try:
        if proxy_mode:
            inbound_meta_data: bytes = relayacceptedsocket.recv(4096)
            inbound_meta_data_str: str = inbound_meta_data.decode('ascii')
            fspace_pos = inbound_meta_data_str.index(' ')
            sspace_pos = inbound_meta_data_str.index(' ', fspace_pos + 1)
            remote_taddress_str = inbound_meta_data_str[fspace_pos + 1:sspace_pos]
            remote_taddress_ss = remote_taddress_str.split(':')
            remote_taddress = (remote_taddress_ss[0], int(remote_taddress_ss[1]))
            fnl_pos = inbound_meta_data_str.index('\r')
            lrs_pos = inbound_meta_data_str[:fnl_pos].rindex(' ')
            meta_protocol_str = inbound_meta_data_str[lrs_pos + 1:fnl_pos]

            tunnelsocket = _createNewConnectSocket(remote_taddress[0], remote_taddress[1])

            if log_enabled:
                print(f'New connection made to {tunnelsocket.getpeername()}')

            outbound_meta_str: str = f'{meta_protocol_str} 200 OK\r\n\r\n'
            outbound_meta_data: bytes = outbound_meta_str.encode('ascii')

            relayacceptedsocket.sendall(outbound_meta_data)
        else:
            tunnelsocket = _createNewConnectSocket(target_name, target_port)
            if log_enabled:
                print(f'New connection made to {tunnelsocket.getpeername()}')

        relayacceptedsocket.setblocking(False)
        tunnelsocket.setblocking(False)

        while running:
            try:
                relay_data = relayacceptedsocket.recv(NET_MSG_SIZE)
                if relay_data:
                    tunnelsocket.sendall(relay_data)
            except socket.error as e:
                if e.errno != socket.EWOULDBLOCK and e.errno != socket.EAGAIN:
                    raise e

            try:
                tunnel_data = tunnelsocket.recv(NET_MSG_SIZE)
                if tunnel_data:
                    relayacceptedsocket.sendall(tunnel_data)
            except socket.error as e:
                if e.errno != socket.EWOULDBLOCK and e.errno != socket.EAGAIN:
                    raise e
    except:
        pass
    finally:
        if tunnelsocket:
            tunnelsocket.close()
        if relayacceptedsocket:
            relayacceptedsocket.close()

        if log_enabled:
            print('Closed connection')


def create(bind_address: str, bind_port: int, proxy_mode: bool = True, target_name: str = None,
           target_port: int = None):
    if not proxy_mode:
        if (not target_name) or (not target_port):
            raise Exception('Address and Port must be provided when relay mode (not proxy)')

    global running

    running = True

    localRelayListenSocket = _createNewListenSocket(bind_address, bind_port)

    try:
        while running:
            relayacceptedsocket, relayacceptedaddr = localRelayListenSocket.accept()

            if log_enabled:
                print(f'Accepted new connection from {relayacceptedaddr}')

            relay_thread = threading.Thread(target=_handleRelay,
                                            args=(relayacceptedsocket, proxy_mode, target_name,
                                                  target_port))
            relay_thread.start()
    except:
        pass
    finally:
        if localRelayListenSocket:
            localRelayListenSocket.close()

    running = False
