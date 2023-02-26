import os
import socket
import sys
import threading
import hashlib
import pickle
from timeit import default_timer as timer
from Crypto.Cipher import AES

receive_buffer_size = 1024
running = False
logging_enabled = True
proxy_mode_header_timeout = 20
magic_cookie = 3242
cipherpool = list()


def _loadCipherPool():
    global cipherpool

    keypool = list()

    with open('keypool', 'rb') as keypoolfile:
        keypool = pickle.load(keypoolfile)

    for key in keypool:
        cipher = AES.new(key, AES.MODE_ECB)
        cipherpool.append(cipher)


def _graceful_socket_close(s: socket.socket):
    if s:
        try:
            s.shutdown(socket.SHUT_RDWR)
        except:
            pass
        finally:
            s.close()


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


def _hCalculateCheckSum(part):
    global magic_cookie

    bCalcMD5 = hashlib.md5(part).hexdigest().encode('ascii')
    md5Sum = int(0)
    for b in bCalcMD5:
        md5Sum += b
    S = md5Sum ^ magic_cookie
    return S


def _obfsrecv(s: socket.socket, buffers: dict):
    global receive_buffer_size
    global cipherpool

    if s not in buffers:
        buffers[s] = bytearray()

    newReceivedData = s.recv(receive_buffer_size)

    buffers[s] += newReceivedData

    returnOutput = bytearray()

    atLeastOneValidBlock = False

    while len(buffers[s]) >= 16:
        validBlock = False

        for cipher in cipherpool:
            block = cipher.decrypt(buffers[s][0:16])
            H = int(block[2])
            if H < 0 or H > 13:
                continue

            hCalculatedCheckSum = _hCalculateCheckSum(block[2:2 + H + 1])
            nCalculatedCheckSum = socket.htons(hCalculatedCheckSum)
            nReceivedChecksum = block[0:2]

            if nReceivedChecksum != nCalculatedCheckSum:
                continue

            returnOutput += block[3:3 + H]
            del buffers[s][0:16]
            validBlock = True
            atLeastOneValidBlock = True
            break

        if not validBlock:
            raise Exception('Invalid Obfuscation PDU')

    if atLeastOneValidBlock:
        return bytes(returnOutput)
    else:
        e = socket.error()
        e.errno = socket.EWOULDBLOCK
        raise e


def _handleRelay(relayacceptedsocket: socket.socket, proxy_mode: bool = True, target_name: str = None,
                 target_port: int = None, **obfssettings):
    global running
    global receive_buffer_size
    tunnelsocket = None

    obfs_socket_buffers = dict()

    try:
        relayacceptedsocket.setblocking(False)
        relayacceptedsocket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        if proxy_mode:
            global proxy_mode_header_timeout

            acc_inbound_meta_data = bytearray()

            proxy_header_time_start = timer()

            while running:
                if (timer() - proxy_header_time_start) > proxy_mode_header_timeout:
                    raise Exception('Proxy Mode get header time out')

                try:
                    acc_inbound_meta_data += relayacceptedsocket.recv(receive_buffer_size)

                    dblnewline_pos = acc_inbound_meta_data.find(b'\x0D\x0A\x0D\x0A')

                    if dblnewline_pos != -1:
                        break

                except socket.error as e:
                    if e.errno != socket.EWOULDBLOCK and e.errno != socket.EAGAIN:
                        raise e

            inbound_meta_data: bytes = bytes(acc_inbound_meta_data)
            inbound_meta_data_str: str = inbound_meta_data.decode('ascii')

            # CHECK HEADER START
            inbound_header_splitted_line = inbound_meta_data_str.split('\r\n')
            header_fline_splitted = inbound_header_splitted_line[0].split(' ')

            if (header_fline_splitted[0] != 'CONNECT') or (
                    header_fline_splitted[2] != 'HTTP/1.0' and header_fline_splitted[2] != 'HTTP/1.1'):
                raise Exception('Proxy Mode invalid or not supported header')
            # CHECK HEADER STOP

            remote_taddress_ss = header_fline_splitted[1].split(':')
            remote_taddress = (remote_taddress_ss[0], int(remote_taddress_ss[1]))
            meta_protocol_str = header_fline_splitted[2]

            tunnelsocket = _createNewConnectSocket(remote_taddress[0], remote_taddress[1])

            if logging_enabled:
                print(f'New connection made to {tunnelsocket.getpeername()}')

            outbound_meta_str: str = f'{meta_protocol_str} 200 OK\r\n\r\n'
            outbound_meta_data: bytes = outbound_meta_str.encode('ascii')

            relayacceptedsocket.sendall(outbound_meta_data)
        else:
            tunnelsocket = _createNewConnectSocket(target_name, target_port)
            if logging_enabled:
                print(f'New connection made to {tunnelsocket.getpeername()}')

        tunnelsocket.setblocking(False)
        tunnelsocket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        while running:
            try:
                relay_data = relayacceptedsocket.recv(receive_buffer_size)
            except socket.error as e:
                if e.errno != socket.EWOULDBLOCK and e.errno != socket.EAGAIN:
                    raise e
            else:
                tunnelsocket.sendall(relay_data)

            try:
                tunnel_data = tunnelsocket.recv(receive_buffer_size)
            except socket.error as e:
                if e.errno != socket.EWOULDBLOCK and e.errno != socket.EAGAIN:
                    raise e
            else:
                relayacceptedsocket.sendall(tunnel_data)

    except:
        pass
    finally:
        _graceful_socket_close(tunnelsocket)
        _graceful_socket_close(relayacceptedsocket)

        if logging_enabled:
            print('Closed connection socket pair')


def createServer(bind_address: str, bind_port: int, proxy_mode: bool = True, target_name: str = None,
                 target_port: int = None, **obfssettings):
    if not proxy_mode:
        if (not target_name) or (not target_port):
            raise Exception('Address and Port must be provided when relay mode (not proxy)')

    global running

    running = True

    localRelayListenSocket = _createNewListenSocket(bind_address, bind_port)

    try:
        while running:
            relayacceptedsocket, relayacceptedaddr = localRelayListenSocket.accept()

            if logging_enabled:
                print(f'Accepted new connection from {relayacceptedaddr}')

            relay_thread = threading.Thread(target=_handleRelay,
                                            args=(relayacceptedsocket, proxy_mode, target_name,
                                                  target_port, obfssettings))
            relay_thread.start()
    except:
        pass
    finally:
        _graceful_socket_close(localRelayListenSocket)

    running = False


def _print_usage():
    fname = os.path.basename(__file__)
    print(
        f'Usage:\n{fname} -p <local address>:<local port>\n{fname} -r <local address>:<local port> <remote '
        f'address>:<remote port>')


def _check_args():
    def _is_valid_port(port_str: str):
        return port_str.isdecimal() and (0 <= int(port_str) < 65536)

    if len(sys.argv) < 3:
        return False
    if sys.argv[1] != '-p' and sys.argv[1] != '-r':
        return False

    if sys.argv[1] == '-p':
        if sys.argv[2].find(':') <= 0 or sys.argv[2].find(':') == (len(sys.argv[2]) - 1):
            return False
        if not _is_valid_port(sys.argv[2].split(':')[1]):
            return False

    if sys.argv[1] == '-r':
        if len(sys.argv) < 4:
            return False
        if sys.argv[2].find(':') <= 0 or sys.argv[2].find(':') == (len(sys.argv[2]) - 1):
            return False
        if sys.argv[3].find(':') <= 0 or sys.argv[3].find(':') == (len(sys.argv[3]) - 1):
            return False

        if not _is_valid_port(sys.argv[2].split(':')[1]):
            return False
        if not _is_valid_port(sys.argv[3].split(':')[1]):
            return False

    return True


# Program starts here
if not _check_args():
    _print_usage()
    sys.exit(1)

_loadCipherPool()

mode = sys.argv[1]

laddrlist = sys.argv[2].split(':')
laddr = (laddrlist[0], int(laddrlist[1]))

if mode == '-p':
    createServer(laddr[0], laddr[1], True)
elif mode == '-r':
    raddrlist = sys.argv[3].split(':')
    raddr = (raddrlist[0], int(raddrlist[1]))
    createServer(laddr[0], laddr[1], False, raddr[0], raddr[1])
else:
    sys.exit(1)
