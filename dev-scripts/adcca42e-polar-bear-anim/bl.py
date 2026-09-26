import socket, json, sys
code = open(sys.argv[1], encoding="utf-8").read()
s = socket.create_connection(("127.0.0.1", 9876), timeout=600)
s.sendall(json.dumps({"type": "execute_code", "params": {"code": code}}).encode())
buf = b""
while True:
    chunk = s.recv(65536)
    if not chunk: break
    buf += chunk
    try: r = json.loads(buf.decode()); break
    except ValueError: continue
print(r.get("status"), r.get("message", ""))
res = r.get("result")
print(res.get("result", res) if isinstance(res, dict) else res)
