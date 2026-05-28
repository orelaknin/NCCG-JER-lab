import argparse
import importlib
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple
from uuid import uuid4


def load_hosts(hosts_file: Path) -> List[str]:
	hosts: List[str] = []
	with hosts_file.open("r", encoding="utf-8") as file:
		for line in file:
			host = line.strip()
			if not host or host.startswith("#"):
				continue
			hosts.append(host)
	return hosts


def run_script_on_host(
	host: str,
	user: str,
	script_content: str,
	script_name: str,
	port: int,
	timeout: int,
	identity_file: str | None,
	strict_host_key_checking: bool,
) -> Tuple[str, int, str, str]:
	ssh_target = f"{user}@{host}"

	ssh_command = ["ssh", "-p", str(port)]
	if identity_file:
		ssh_command.extend(["-i", identity_file])
	if not strict_host_key_checking:
		ssh_command.extend(
			[
				"-o",
				"StrictHostKeyChecking=no",
				"-o",
				"UserKnownHostsFile=/dev/null",
			]
		)

	remote_command = (
		f"bash -lc 'set -e; "
		f"cat >/tmp/{script_name} <<\"__SCRIPT_EOF__\"\n"
		f"{script_content}\n"
		f"__SCRIPT_EOF__\n"
		f"chmod +x /tmp/{script_name}; "
		f"/tmp/{script_name}; "
		f"rc=$?; rm -f /tmp/{script_name}; exit $rc'"
	)

	full_command = ssh_command + [ssh_target, remote_command]

	completed = subprocess.run(
		full_command,
		capture_output=True,
		text=True,
		timeout=timeout,
		check=False,
	)

	return host, completed.returncode, completed.stdout, completed.stderr


def run_command_on_host(
	host: str,
	user: str,
	command: str,
	port: int,
	timeout: int,
	identity_file: str | None,
	strict_host_key_checking: bool,
) -> Tuple[str, int, str, str]:
	ssh_target = f"{user}@{host}"

	ssh_command = ["ssh", "-p", str(port)]
	if identity_file:
		ssh_command.extend(["-i", identity_file])
	if not strict_host_key_checking:
		ssh_command.extend(
			[
				"-o",
				"StrictHostKeyChecking=no",
				"-o",
				"UserKnownHostsFile=/dev/null",
			]
		)

	remote_command = f"bash -lc {shlex.quote(command)}"
	full_command = ssh_command + [ssh_target, remote_command]

	completed = subprocess.run(
		full_command,
		capture_output=True,
		text=True,
		timeout=timeout,
		check=False,
	)

	return host, completed.returncode, completed.stdout, completed.stderr


def run_script_on_host_password(
	host: str,
	user: str,
	password: str,
	script_content: str,
	script_name: str,
	port: int,
	timeout: int,
	strict_host_key_checking: bool,
) -> Tuple[str, int, str, str]:
	try:
		paramiko = importlib.import_module("paramiko")
	except ImportError as error:
		return host, 998, "", f"paramiko is required for --password mode: {error}"

	client = paramiko.SSHClient()
	if strict_host_key_checking:
		client.load_system_host_keys()
		client.set_missing_host_key_policy(paramiko.RejectPolicy())
	else:
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

	remote_script = f"/tmp/{uuid4().hex}_{script_name}"

	try:
		client.connect(
			hostname=host,
			port=port,
			username=user,
			password=password,
			timeout=timeout,
			look_for_keys=False,
			allow_agent=False,
		)

		sftp = client.open_sftp()
		with sftp.open(remote_script, "w") as file:
			file.write(script_content)
		sftp.close()

		command = (
			f"bash -lc 'chmod +x {remote_script}; "
			f"{remote_script}; "
			f"rc=$?; rm -f {remote_script}; exit $rc'"
		)

		stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
		stdin.close()
		return_code = stdout.channel.recv_exit_status()
		stdout_text = stdout.read().decode("utf-8", errors="replace")
		stderr_text = stderr.read().decode("utf-8", errors="replace")
		return host, return_code, stdout_text, stderr_text
	except Exception as error:
		return host, 997, "", str(error)
	finally:
		client.close()


def run_command_on_host_password(
	host: str,
	user: str,
	password: str,
	command: str,
	port: int,
	timeout: int,
	strict_host_key_checking: bool,
) -> Tuple[str, int, str, str]:
	try:
		paramiko = importlib.import_module("paramiko")
	except ImportError as error:
		return host, 998, "", f"paramiko is required for --password mode: {error}"

	client = paramiko.SSHClient()
	if strict_host_key_checking:
		client.load_system_host_keys()
		client.set_missing_host_key_policy(paramiko.RejectPolicy())
	else:
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

	try:
		client.connect(
			hostname=host,
			port=port,
			username=user,
			password=password,
			timeout=timeout,
			look_for_keys=False,
			allow_agent=False,
		)

		remote_command = f"bash -lc {shlex.quote(command)}"
		stdin, stdout, stderr = client.exec_command(remote_command, timeout=timeout)
		stdin.close()
		return_code = stdout.channel.recv_exit_status()
		stdout_text = stdout.read().decode("utf-8", errors="replace")
		stderr_text = stderr.read().decode("utf-8", errors="replace")
		return host, return_code, stdout_text, stderr_text
	except Exception as error:
		return host, 997, "", str(error)
	finally:
		client.close()


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Run a script file or command on multiple hosts over SSH using a hosts txt file."
	)
	parser.add_argument("hosts_file", help="Path to txt file containing one host per line")
	parser.add_argument(
		"script_file",
		nargs="?",
		default=None,
		help="Path to script file to execute on each host",
	)
	parser.add_argument(
		"--command",
		default=None,
		help="Command string to execute on each host (use this instead of script_file)",
	)
	parser.add_argument("--user", required=True, help="SSH username")
	parser.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
	parser.add_argument(
		"--timeout",
		type=int,
		default=300,
		help="Timeout per host in seconds (default: 300)",
	)
	parser.add_argument("--identity-file", help="Path to SSH private key", default=None)
	parser.add_argument("--password", help="SSH password (uses paramiko)", default=None)
	parser.add_argument(
		"--workers",
		type=int,
		default=5,
		help="How many hosts to run in parallel (default: 5)",
	)
	parser.add_argument(
		"--strict-host-key-checking",
		action="store_true",
		help="Enable strict host key checking (disabled by default)",
	)

	args = parser.parse_args()

	if bool(args.script_file) == bool(args.command):
		raise ValueError("Provide exactly one target: script_file OR --command")

	hosts_path = Path(args.hosts_file)

	if not hosts_path.exists():
		raise FileNotFoundError(f"Hosts file not found: {hosts_path}")

	use_command = args.command is not None
	if use_command:
		execution_target = args.command
		script_content = ""
		script_name = ""
	else:
		script_path = Path(args.script_file)
		if not script_path.exists():
			raise FileNotFoundError(f"Script file not found: {script_path}")
		execution_target = str(script_path)
		script_content = script_path.read_text(encoding="utf-8")
		script_name = script_path.name

	hosts = load_hosts(hosts_path)
	if not hosts:
		raise ValueError("No hosts found in hosts file")

	print(f"Loaded {len(hosts)} hosts from {hosts_path}")
	if use_command:
		print(f"Command: {execution_target}")
	else:
		print(f"Script: {execution_target}")
	print(f"Running with {args.workers} worker(s)...")
	if args.password:
		print("Authentication mode: password (paramiko)")
	else:
		print("Authentication mode: ssh client (key/agent/password prompt)")

	results: List[Tuple[str, int, str, str]] = []

	with ThreadPoolExecutor(max_workers=args.workers) as executor:
		if args.password:
			if use_command:
				futures = {
					executor.submit(
						run_command_on_host_password,
						host,
						args.user,
						args.password,
						args.command,
						args.port,
						args.timeout,
						args.strict_host_key_checking,
					): host
					for host in hosts
				}
			else:
				futures = {
					executor.submit(
						run_script_on_host_password,
						host,
						args.user,
						args.password,
						script_content,
						script_name,
						args.port,
						args.timeout,
						args.strict_host_key_checking,
					): host
					for host in hosts
				}
		else:
			if use_command:
				futures = {
					executor.submit(
						run_command_on_host,
						host,
						args.user,
						args.command,
						args.port,
						args.timeout,
						args.identity_file,
						args.strict_host_key_checking,
					): host
					for host in hosts
				}
			else:
				futures = {
					executor.submit(
						run_script_on_host,
						host,
						args.user,
						script_content,
						script_name,
						args.port,
						args.timeout,
						args.identity_file,
						args.strict_host_key_checking,
					): host
					for host in hosts
				}

		for future in as_completed(futures):
			host = futures[future]
			try:
				result = future.result()
			except Exception as error:
				result = (host, 999, "", f"Execution failed: {error}")

			results.append(result)
			host_name, rc, _, stderr = result
			if rc == 0:
				print(f"[OK] {host_name}")
			else:
				print(f"[FAIL] {host_name} (rc={rc})")
				if stderr.strip():
					print(stderr.strip())

	success = [entry for entry in results if entry[1] == 0]
	failed = [entry for entry in results if entry[1] != 0]

	print("\n===== Summary =====")
	print(f"Total: {len(results)}")
	print(f"Success: {len(success)}")
	print(f"Failed: {len(failed)}")

	if failed:
		print("\nFailed hosts:")
		for host, rc, _, _ in failed:
			print(f"- {host} (rc={rc})")
		raise SystemExit(1)


if __name__ == "__main__":
	main()
