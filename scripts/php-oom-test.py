#!/usr/bin/env python3
"""Exercise the PHP memory-limit app on the local root and upstream images."""

import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

APP = os.path.join(os.path.dirname(__file__), "..", "images", "php-app")
LAYERS = [
    ("cli", "Dockerfile.cli", "timurkri/root-php-8-5-11-cli:latest", "timurkri/upstream-php-8-5-11-cli:latest"),
    ("apache", "Dockerfile.apache", "timurkri/root-php-8-4-26-apache:latest", "timurkri/upstream-php-8-4-26-apache:latest"),
    ("fpm", "Dockerfile.fpm", "timurkri/root-php-8-5-11-fpm:latest", "timurkri/upstream-php-8-5-11-fpm:latest"),
]


def oom_tag(image):
    return image.replace(":latest", ":oomtest")


def build_layers():
    for sapi, dockerfile, root, upstream in LAYERS:
        for base in (root, upstream):
            tag = oom_tag(base)
            print(f"build {tag} from {base}")
            proc = subprocess.run(
                [
                    "docker", "build",
                    "-f", os.path.join(APP, dockerfile),
                    "--build-arg", f"BASE={base}",
                    "-t", tag,
                    APP,
                ],
                text=True,
            )
            if proc.returncode != 0:
                raise SystemExit(f"build failed for {tag}")


PAIRS = [
    (sapi, oom_tag(root), oom_tag(upstream))
    for sapi, _, root, upstream in LAYERS
]

failures = []


def note(image, case, detail):
    print(f"  {image} {case}: {detail}")


def fail(image, case, detail):
    failures.append(f"{image} {case}: {detail}")
    print(f"  FAIL {image} {case}: {detail}")


def docker(*args, check=True, text=True):
    return subprocess.run(["docker", *args], check=check, text=text, capture_output=True)


def cli_case(image, case, flag_dir):
    flag = os.path.join(flag_dir, "flag")
    if os.path.exists(flag):
        os.remove(flag)
    proc = subprocess.run(
        [
            "docker", "run", "--rm",
            "-e", "OOM_FLAG=/oom/flag",
            "-v", f"{flag_dir}:/oom",
            "--entrypoint", "php",
            image,
            "/app/index.php",
            case,
        ],
        text=True,
        capture_output=True,
    )
    shutdown = os.path.isfile(flag) and open(flag).read() == "1"
    return proc.returncode, proc.stdout, proc.stderr, shutdown


def parse_json(stdout):
    line = stdout.strip().splitlines()[-1] if stdout.strip() else ""
    return json.loads(line)


def fcgi_record(typ, req_id, body):
    pad = (8 - (len(body) % 8)) % 8
    header = struct.pack(">BBHHBB", 1, typ, req_id, len(body), pad, 0)
    return header + body + (b"\x00" * pad)


def enc_len(n):
    if n < 128:
        return struct.pack("B", n)
    return struct.pack(">I", n | 0x80000000)


def name_value(pairs):
    out = b""
    for key, value in pairs:
        kb, vb = key.encode(), value.encode()
        out += enc_len(len(kb)) + enc_len(len(vb)) + kb + vb
    return out


def fcgi_request(port, params, body=b"", timeout=20, attempts=8):
    last = None
    sock = None
    for _ in range(40):
        try:
            sock = socket.create_connection(("127.0.0.1", port), timeout=2)
            break
        except OSError as exc:
            last = exc
            time.sleep(0.25)
    if sock is None:
        raise RuntimeError(f"fpm port {port} not accepting connections: {last}")
    sock.settimeout(timeout)
    rid = 1
    msg = fcgi_record(1, rid, struct.pack(">HB5x", 1, 0))
    msg += fcgi_record(4, rid, name_value(params))
    msg += fcgi_record(4, rid, b"")
    view = body
    while view:
        chunk = view[:65535]
        view = view[65535:]
        msg += fcgi_record(5, rid, chunk)
    msg += fcgi_record(5, rid, b"")
    try:
        sock.sendall(msg)
        stdout = b""
        stderr = b""
        while True:
            hdr = b""
            while len(hdr) < 8:
                chunk = sock.recv(8 - len(hdr))
                if not chunk:
                    raise ConnectionError("fpm closed before a record")
                hdr += chunk
            _, typ, _, clen, plen, _ = struct.unpack(">BBHHBB", hdr)
            payload = b""
            while len(payload) < clen:
                chunk = sock.recv(clen - len(payload))
                if not chunk:
                    break
                payload += chunk
            if plen:
                extra = b""
                while len(extra) < plen:
                    chunk = sock.recv(plen - len(extra))
                    if not chunk:
                        break
                    extra += chunk
            if typ == 6:
                stdout += payload
            elif typ == 7:
                stderr += payload
            elif typ == 3:
                break
    except (ConnectionError, socket.timeout, OSError):
        stdout, stderr = b"", b""
    finally:
        sock.close()
    if not stdout and attempts > 1:
        time.sleep(0.3)
        return fcgi_request(port, params, body, timeout, attempts - 1)
    return stdout, stderr


def http_get(port, path):
    url = f"http://127.0.0.1:{port}{path}"
    last = None
    for _ in range(40):
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()
        except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            last = exc
            time.sleep(0.25)
    raise RuntimeError(f"apache port {port} failed: {last}")


def http_exchange(port, raw):
    sock = socket.create_connection(("127.0.0.1", port), timeout=10)
    sock.settimeout(10)
    sock.sendall(raw)
    data = b""
    while True:
        try:
            chunk = sock.recv(65536)
        except socket.timeout:
            break
        if not chunk:
            break
        data += chunk
    sock.close()
    return data


def start_server(image, name, publish):
    docker("rm", "-f", name, check=False)
    docker("run", "-d", "--name", name, "-p", publish, image)
    host_port = int(publish.split(":")[0])
    return host_port


def stop_server(name):
    logs = docker("logs", name, check=False).stderr + docker("logs", name, check=False).stdout
    docker("rm", "-f", name, check=False)
    return logs


def expect_health(label, payload):
    if not payload.get("ok"):
        fail(label, "health", payload)
        return
    note(label, "health", f"php {payload.get('version')} sapi={payload.get('sapi')} hard={payload.get('memory_hard_limit_percent')!r}")


def run_cli(image):
    flag_dir = tempfile.mkdtemp(prefix="php-oom-")
    try:
        code, out, err, shutdown = cli_case(image, "health", flag_dir)
        if code != 0:
            fail(image, "health", f"exit {code} {err}")
            return None
        health = parse_json(out)
        expect_health(image, health)

        code, out, err, _ = cli_case(image, "normal", flag_dir)
        if code != 0:
            fail(image, "normal", f"exit {code} {err}")
            normal = None
        else:
            normal = parse_json(out)["result"]
            note(image, "normal", "ok")

        code, out, err, shutdown = cli_case(image, "oom-soft", flag_dir)
        if code == 139 or "segfault" in err.lower():
            fail(image, "oom-soft", f"crash exit {code}")
        elif code == 0:
            body = parse_json(out)
            note(image, "oom-soft", f"caught {body.get('type')} shutdown={shutdown} finally={body.get('finally')}")
        elif "Allowed memory size" in err:
            note(image, "oom-soft", f"fatal exit {code} shutdown={shutdown}")
        else:
            fail(image, "oom-soft", f"exit {code} stderr={err.strip()[-400:]}")

        for case in ("oom-ob", "oom-json"):
            code, out, err, _ = cli_case(image, case, flag_dir)
            if code == 139 or "segfault" in err.lower():
                fail(image, case, f"crash exit {code}")
            elif code == 0:
                note(image, case, out.strip()[:180])
            elif "Allowed memory size" in err or "output buffering" in err:
                note(image, case, f"exit {code} {err.strip().splitlines()[-1][-180:]}")
            else:
                fail(image, case, f"exit {code} stderr={err.strip()[-300:]}")

        code, out, err, shutdown = cli_case(image, "oom-hard", flag_dir)
        hard_text = err
        if code == 139 or "segfault" in err.lower():
            fail(image, "oom-hard", "segfault")
        elif "after-hard-oom" in err:
            fail(image, "oom-hard", "allocation returned")
        else:
            note(image, "oom-hard", f"exit {code} shutdown={shutdown} stderr={err.strip()[-240:]!r}")

        code, out, err, shutdown = cli_case(image, "pbkdf2-huge", flag_dir)
        if code == 139 or "segfault" in (err + out).lower():
            fail(image, "pbkdf2-huge", "segfault")
        elif "after-pbkdf2" in err:
            fail(image, "pbkdf2-huge", "huge hash_pbkdf2 returned")
        else:
            note(image, "pbkdf2-huge", f"exit {code} shutdown={shutdown} stderr={err.strip()[-240:]!r}")

        code, out, err, _ = cli_case(image, "health", flag_dir)
        if code != 0:
            fail(image, "health-after", f"exit {code}")
        return normal, hard_text
    finally:
        shutil.rmtree(flag_dir, ignore_errors=True)


def run_http_posts(image, port):
    status, raw = http_get(port, "/index.php?case=post")
    note(image, "post-empty", raw.decode()[:200])

    body = "&".join(f"k{i}=v" for i in range(80)).encode()
    raw = http_exchange(
        port,
        b"POST /index.php?case=post HTTP/1.1\r\nHost: localhost\r\n"
        b"Content-Type: application/x-www-form-urlencoded\r\n"
        + f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode()
        + body,
    )
    note(image, "post-many-vars", raw.split(b"\r\n\r\n", 1)[-1][:240].decode(errors="replace"))

    nested = "a[b][c][d][e][f][g]=1&a[b]=2".encode()
    raw = http_exchange(
        port,
        b"POST /index.php?case=post HTTP/1.1\r\nHost: localhost\r\n"
        b"Content-Type: application/x-www-form-urlencoded\r\n"
        + f"Content-Length: {len(nested)}\r\nConnection: close\r\n\r\n".encode()
        + nested,
    )
    note(image, "post-nested", raw.split(b"\r\n\r\n", 1)[-1][:240].decode(errors="replace"))

    short = b"a=1"
    raw = http_exchange(
        port,
        b"POST /index.php?case=post HTTP/1.1\r\nHost: localhost\r\n"
        b"Content-Type: application/x-www-form-urlencoded\r\n"
        b"Content-Length: 100\r\nConnection: close\r\n\r\n" + short,
    )
    note(image, "post-bad-length", raw.split(b"\r\n\r\n", 1)[-1][:240].decode(errors="replace"))

    chunked = (
        b"POST /index.php?case=post HTTP/1.1\r\nHost: localhost\r\n"
        b"Content-Type: application/x-www-form-urlencoded\r\n"
        b"Transfer-Encoding: chunked\r\nConnection: close\r\n\r\n"
        b"4\r\na=123\r\n0\r\n\r\n"
    )
    raw = http_exchange(port, chunked)
    note(image, "post-chunked", raw.split(b"\r\n\r\n", 1)[-1][:240].decode(errors="replace"))

    big = b"a=" + (b"x" * (5 * 1024 * 1024))
    raw = http_exchange(
        port,
        b"POST /index.php?case=post HTTP/1.1\r\nHost: localhost\r\n"
        b"Content-Type: application/x-www-form-urlencoded\r\n"
        + f"Content-Length: {len(big)}\r\nConnection: close\r\n\r\n".encode()
        + big,
    )
    note(image, "post-over-max", raw.split(b"\r\n\r\n", 1)[-1][:240].decode(errors="replace"))

    boundary = "----timur"
    multipart = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="a[b][c]"\r\n\r\n'
        "nested\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="a[b][c]"\r\n\r\n'
        "duplicate\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="hi.txt"\r\n'
        "Content-Type: text/plain\r\n"
        "Content-Type: application/octet-stream\r\n\r\n"
        "hello\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="PHP_SESSION_UPLOAD_PROGRESS"\r\n\r\n'
        "not-a-session\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    raw = http_exchange(
        port,
        (
            "POST /index.php?case=post HTTP/1.1\r\nHost: localhost\r\n"
            f"Content-Type: multipart/form-data; boundary={boundary}\r\n"
            f"Content-Length: {len(multipart)}\r\n"
            "Cookie: PHPSESSID=%%%invalid%%%\r\nConnection: close\r\n\r\n"
        ).encode()
        + multipart,
    )
    note(image, "multipart", raw.split(b"\r\n\r\n", 1)[-1][:300].decode(errors="replace"))

    small = b"a=1&b=2"
    raw = http_exchange(
        port,
        b"POST /index.php?case=parse-body HTTP/1.1\r\nHost: localhost\r\n"
        b"Content-Type: application/x-www-form-urlencoded\r\n"
        + f"Content-Length: {len(small)}\r\nConnection: close\r\n\r\n".encode()
        + small,
    )
    note(image, "parse-body", raw.split(b"\r\n\r\n", 1)[-1][:240].decode(errors="replace"))


def run_apache(image, port):
    name = "timur-php-oom-" + image.split("/")[-1].split(":")[0]
    start_server(image, name, f"{port}:80")
    normal = None
    try:
        _, raw = http_get(port, "/index.php?case=health")
        expect_health(image, json.loads(raw))
        _, raw = http_get(port, "/index.php?case=normal")
        body = json.loads(raw)
        if not body.get("ok"):
            fail(image, "normal", body)
        else:
            normal = body["result"]
            note(image, "normal", "ok")
        run_http_posts(image, port)
        status, raw = http_get(port, "/index.php?case=oom-soft")
        if status >= 500 and b"ok" not in raw:
            note(image, "oom-soft", f"HTTP {status}")
        elif status != 200:
            fail(image, "oom-soft", f"HTTP {status} {raw[:180]!r}")
        else:
            note(image, "oom-soft", raw[:180].decode(errors="replace"))
        try:
            http_get(port, "/index.php?case=oom-hard")
            note(image, "oom-hard", "response returned")
        except Exception as exc:
            note(image, "oom-hard", f"request ended: {exc}")
        _, raw = http_get(port, "/index.php?case=health")
        health = json.loads(raw)
        if not health.get("ok"):
            fail(image, "health-after-hard", health)
        else:
            note(image, "health-after-hard", "ok")
        logs = stop_server(name)
        if "segfault" in logs.lower() or "segmentation fault" in logs.lower():
            fail(image, "logs", "segfault in apache logs")
        if "Hard memory limit" in logs:
            note(image, "logs", "hard memory limit message present")
        else:
            note(image, "logs", "no hard memory limit message")
        return normal
    except Exception:
        stop_server(name)
        raise


def fpm_get(port, case):
    stdout, stderr = fcgi_request(
        port,
        [
            ("REQUEST_METHOD", "GET"),
            ("SCRIPT_FILENAME", "/var/www/html/index.php"),
            ("SCRIPT_NAME", "/index.php"),
            ("QUERY_STRING", f"case={case}"),
            ("SERVER_PROTOCOL", "HTTP/1.1"),
            ("GATEWAY_INTERFACE", "CGI/1.1"),
            ("CONTENT_LENGTH", "0"),
        ],
    )
    return stdout, stderr


def run_fpm(image, port):
    name = "timur-php-oom-" + image.split("/")[-1].split(":")[0]
    start_server(image, name, f"{port}:9000")
    normal = None
    try:
        stdout, _ = fpm_get(port, "health")
        expect_health(image, json.loads(stdout.split(b"\r\n\r\n", 1)[-1]))
        stdout, _ = fpm_get(port, "normal")
        body = json.loads(stdout.split(b"\r\n\r\n", 1)[-1])
        if not body.get("ok"):
            fail(image, "normal", body)
        else:
            normal = body["result"]
            note(image, "normal", "ok")

        post = b"a=1&b=2"
        stdout, stderr = fcgi_request(
            port,
            [
                ("REQUEST_METHOD", "POST"),
                ("SCRIPT_FILENAME", "/var/www/html/index.php"),
                ("SCRIPT_NAME", "/index.php"),
                ("QUERY_STRING", "case=post"),
                ("CONTENT_TYPE", "application/x-www-form-urlencoded"),
                ("CONTENT_LENGTH", str(len(post))),
                ("SERVER_PROTOCOL", "HTTP/1.1"),
                ("GATEWAY_INTERFACE", "CGI/1.1"),
            ],
            post,
        )
        note(image, "post", stdout.split(b"\r\n\r\n", 1)[-1][:200].decode(errors="replace"))

        huge = b"a=" + (b"y" * (40 * 1024 * 1024))
        try:
            stdout, stderr = fcgi_request(
                port,
                [
                    ("REQUEST_METHOD", "POST"),
                    ("SCRIPT_FILENAME", "/var/www/html/index.php"),
                    ("SCRIPT_NAME", "/index.php"),
                    ("QUERY_STRING", "case=post"),
                    ("CONTENT_TYPE", "application/x-www-form-urlencoded"),
                    ("CONTENT_LENGTH", str(len(huge))),
                    ("SERVER_PROTOCOL", "HTTP/1.1"),
                    ("GATEWAY_INTERFACE", "CGI/1.1"),
                ],
                huge,
                timeout=30,
            )
            note(image, "post-oom", stdout.split(b"\r\n\r\n", 1)[-1][:200].decode(errors="replace") or stderr[:200].decode(errors="replace"))
        except Exception as exc:
            note(image, "post-oom", f"request ended: {exc}")

        stdout, _ = fpm_get(port, "health")
        health = json.loads(stdout.split(b"\r\n\r\n", 1)[-1])
        if not health.get("ok"):
            fail(image, "health-after-post-oom", health)
        else:
            note(image, "health-after-post-oom", "same worker or respawn accepted the next request")

        try:
            stdout, _ = fpm_get(port, "oom-hard")
            note(image, "oom-hard", stdout.split(b"\r\n\r\n", 1)[-1][:160].decode(errors="replace") or "empty")
        except Exception as exc:
            note(image, "oom-hard", f"request ended: {exc}")
        stdout, _ = fpm_get(port, "health")
        health = json.loads(stdout.split(b"\r\n\r\n", 1)[-1])
        if not health.get("ok"):
            fail(image, "health-after-hard", health)
        else:
            note(image, "health-after-hard", "ok")
        logs = stop_server(name)
        if "segfault" in logs.lower():
            fail(image, "logs", "segfault in fpm logs")
        if "Hard memory limit" in logs:
            note(image, "logs", "hard memory limit message present")
        else:
            note(image, "logs", "no hard memory limit message")
        return normal
    except Exception:
        stop_server(name)
        raise


def main():
    build_layers()
    normals = {}
    for sapi, root, upstream in PAIRS:
        print(f"\n== {sapi} ==")
        if sapi == "cli":
            root_normal, _ = run_cli(root) or (None, None)
            up_normal, _ = run_cli(upstream) or (None, None)
        elif sapi == "apache":
            root_normal = run_apache(root, 18080)
            up_normal = run_apache(upstream, 18081)
        else:
            root_normal = run_fpm(root, 19000)
            up_normal = run_fpm(upstream, 19001)
        if root_normal is not None and up_normal is not None and root_normal != up_normal:
            fail(sapi, "normal-compare", "root and upstream normal results differ")
            print(json.dumps({"root": root_normal, "upstream": up_normal}, indent=2)[:2000])
        elif root_normal is not None:
            note(sapi, "normal-compare", "root and upstream match")
        normals[sapi] = (root_normal, up_normal)

    print("\n== summary ==")
    if failures:
        for item in failures:
            print("FAIL", item)
        raise SystemExit(1)
    print("all required checks passed")


if __name__ == "__main__":
    main()
