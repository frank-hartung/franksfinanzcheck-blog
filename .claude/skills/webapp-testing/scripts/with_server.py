#!/usr/bin/env python3
"""
Start one or more servers, wait for them to be ready, run a command, then clean up.

Usage:
    # Single server
    python scripts/with_server.py --server "npm run dev" --port 5173 -- python automation.py
    python scripts/with_server.py --server "npm start" --port 3000 -- python test.py

    # Multiple servers with separate working directories
    python scripts/with_server.py \
      --server "python server.py" --server-cwd backend --port 3000 \
      --server "npm run dev" --server-cwd frontend --port 5173 \
      -- python test.py

``--server`` is parsed as a command's argument vector (like a terminal line),
but is never passed to a shell. Use ``--server-cwd`` instead of ``cd ... &&``.
"""

import argparse
import shlex
import socket
import subprocess
import sys
import time

def is_server_ready(port, timeout=30):
    """Wait for server to be ready by polling the port."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(('localhost', port), timeout=1):
                return True
        except (socket.error, ConnectionRefusedError):
            time.sleep(0.5)
    return False


UNSUPPORTED_SHELL_OPERATORS = frozenset({"&&", "||", ";", "|", "<", ">", "<<", ">>"})


def parse_server_command(value):
    """Turn one ``--server`` value into an argv vector without a shell.

    Quotes only group arguments; operators such as ``&&`` have no special
    meaning. A working directory is supplied separately through
    ``--server-cwd``. This keeps the helper useful for normal commands while
    ensuring a CLI value is never evaluated as shell source code.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("server command must not be empty")
    try:
        argv = shlex.split(value, posix=True)
    except ValueError as exc:
        raise ValueError(f"invalid server command: {exc}") from exc
    if not argv:
        raise ValueError("server command must contain an executable")
    if any(argument in UNSUPPORTED_SHELL_OPERATORS for argument in argv):
        raise ValueError(
            "shell operators are not supported; use --server-cwd instead of `cd ... && ...`"
        )
    return argv


def main():
    parser = argparse.ArgumentParser(description='Run command with one or more servers')
    parser.add_argument('--server', action='append', dest='servers', required=True,
                        help='Server command, parsed to argv without a shell (repeatable)')
    parser.add_argument('--server-cwd', action='append', dest='server_cwds',
                        help='Working directory for the matching --server (repeatable)')
    parser.add_argument('--port', action='append', dest='ports', type=int, required=True, help='Port for each server (must match --server count)')
    parser.add_argument('--timeout', type=int, default=30, help='Timeout in seconds per server (default: 30)')
    parser.add_argument('command', nargs=argparse.REMAINDER, help='Command to run after server(s) ready')

    args = parser.parse_args()

    # Remove the '--' separator if present
    if args.command and args.command[0] == '--':
        args.command = args.command[1:]

    if not args.command:
        print("Error: No command specified to run")
        sys.exit(1)

    # Parse server configurations
    if len(args.servers) != len(args.ports):
        parser.error("Number of --server and --port arguments must match")
    if args.server_cwds and len(args.servers) != len(args.server_cwds):
        parser.error("Number of --server and --server-cwd arguments must match")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    servers = []
    for index, (command, port) in enumerate(zip(args.servers, args.ports)):
        try:
            argv = parse_server_command(command)
        except ValueError as exc:
            parser.error(str(exc))
        cwd = args.server_cwds[index] if args.server_cwds else None
        servers.append({'argv': argv, 'port': port, 'cwd': cwd})

    server_processes = []

    try:
        # Start all servers
        for i, server in enumerate(servers):
            printable = shlex.join(server['argv'])
            print(f"Starting server {i+1}/{len(servers)}: {printable}")

            process = subprocess.Popen(
                server['argv'],
                cwd=server['cwd'],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            server_processes.append(process)

            # Wait for this server to be ready
            print(f"Waiting for server on port {server['port']}...")
            if not is_server_ready(server['port'], timeout=args.timeout):
                raise RuntimeError(f"Server failed to start on port {server['port']} within {args.timeout}s")

            print(f"Server ready on port {server['port']}")

        print(f"\nAll {len(servers)} server(s) ready")

        # Run the command
        print(f"Running: {' '.join(args.command)}\n")
        result = subprocess.run(args.command, shell=False)
        sys.exit(result.returncode)

    finally:
        # Clean up all servers
        print(f"\nStopping {len(server_processes)} server(s)...")
        for i, process in enumerate(server_processes):
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            print(f"Server {i+1} stopped")
        print("All servers stopped")


if __name__ == '__main__':
    main()