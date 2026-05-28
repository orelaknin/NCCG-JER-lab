import os
import shutil
import subprocess
 
BASE_DIR = "/home/laduser"
TARGET_DIR = os.path.join(BASE_DIR, "Latest_Denver")
INSTALL_SCRIPT = "/net/inx028core.intel.com/data/things/scripts/install_denver.sh"
 
# Default team groups (list of strings)
DEFAULT_TEAMS_LIST = [
    "EthInlineCrypto_team",
    "EthLanFlows_team",
    "EthPacketProcessing_team",
    "EthQoS_team",
    "EthResets_team",
    "EthVirtualization_team",
    "EthPcie_team",
    "Rdma_team",
    "FcConcurrency_team",
    "EthSmartNicFlows_team",
    "Security_team",
]
DEFAULT_TEAMS = " ".join(DEFAULT_TEAMS_LIST)
 
# Default tag value
DEFAULT_TAG = "MASTER"
 
# credentials (can be overridden with env vars DENVER_USERNAME / DENVER_PASSWORD)
USERNAME = os.environ.get("DENVER_USERNAME", "svtools")
PASSWORD = os.environ.get("DENVER_PASSWORD", "SVSW@123")
 
 
def clean_and_prepare():
    """Delete the old folder and create a new one"""
    if os.path.exists(TARGET_DIR):
        print(f"Deleting {TARGET_DIR}...")
        shutil.rmtree(TARGET_DIR)
 
    print(f"Creating {TARGET_DIR}...")
    os.makedirs(TARGET_DIR, exist_ok=True)
 
 
def run_install(teams, tag=None):
    """Run install_denver with given parameters and auto-handle password prompts.

    The original simple stdin piping does not work if the underlying script invokes
    ssh/scp which reads directly from the controlling TTY (/dev/tty). Here we try:
      1. pexpect (best)  pattern-match and respond.
      2. pty.spawn fallback  intercept output and inject password.
      3. Last resort: plain subprocess (user may be prompted manually).
    """
    cmd = [INSTALL_SCRIPT, "-t", teams]
    if tag:  # only add -T if user provided tag
        cmd += ["-T", tag]

    print("Running command:", " ".join(cmd))

    # Always echo which user we're authenticating as (without password)
    print(f"Using username: {USERNAME} (password auto-supply enabled)")

    # 1. Try pexpect
    try:
        import pexpect
        # Use a shell form so install script & its internal ssh prompts appear
        child = pexpect.spawn(' '.join(cmd), cwd=TARGET_DIR, encoding='utf-8', timeout=None)
        # Optional: log output live
        child.logfile = None  # set to sys.stdout for verbose
        while True:
            idx = child.expect([
                r'Are you sure you want to continue connecting',
                r'[Pp]assword:',
                pexpect.EOF,
                pexpect.TIMEOUT,
            ])
            if idx == 0:
                print("Responding 'yes' to host key confirmation")
                child.sendline('yes')
            elif idx == 1:
                print("Supplying password...")
                child.sendline(PASSWORD)
            elif idx == 2:  # EOF
                break
            elif idx == 3:  # TIMEOUT
                # Continue waiting; could add a timeout counter if needed
                print("(Waiting... timeout, will continue monitoring)")
                continue
        child.close()
        if child.exitstatus is not None:
            print(f"install_denver exited with status {child.exitstatus}")
        else:
            print("install_denver finished (no explicit exit status)")
        return
    except ImportError:
        print("pexpect not installed  falling back to pty method.")
    except Exception as e:
        print(f"pexpect failed ({e})  attempting pty fallback.")

    # 2. Fallback: pty.spawn to emulate a tty so ssh accepts injected password
    try:
        import pty, sys, os as _os
        print("orel")

        def _read(fd):
            try:
                data = _os.read(fd, 1024)
                text = data.decode(errors='ignore')
                if 'Are you sure you want to continue connecting' in text:
                    print("Responding 'yes' to host key confirmation")
                    _os.write(fd, b'yes\n')
                if 'assword:' in text:  # matches Password: / password:
                    print("Supplying password...")
                    _os.write(fd, (PASSWORD + '\n').encode())
                # Mirror output to stdout
                sys.stdout.write(text)
                sys.stdout.flush()
            except OSError:
                pass
            return data

        pty.spawn(cmd, _read)
        return
    except Exception as e:
        print(f"pty fallback failed ({e})  running plain subprocess (may prompt).")

    # 3. Last resort  user will have to type password.
    subprocess.run(cmd, cwd=TARGET_DIR)
 
 
def fix_symlinks():
    """Re-create symbolic links from the new folder"""
    links = ["services", "sv_driver", "Denver"]
    for link in links:
        path = os.path.join(BASE_DIR, link)
        target = os.path.join(TARGET_DIR, link)
        if os.path.islink(path) or os.path.exists(path):
            print(f"Removing {path}...")
            if os.path.islink(path):
                os.unlink(path)
            else:
                shutil.rmtree(path)
        print(f"Linking {path} ? {target}")
        os.symlink(target, path)
 
 
def main():
    print("Choose an option:")
    print("1. Compile all teams")
    print("2. Compile for specific team")
    choice = input(">> ")
 
    if choice == "1":
        teams = DEFAULT_TEAMS
    elif choice == "2":
        print("\nPlease select a team to compile:")
        for i, team_name in enumerate(DEFAULT_TEAMS_LIST, 1):
            print(f"{i}. {team_name}")
        
        while True:
            try:
                team_choice = int(input(f"Enter team number (1-{len(DEFAULT_TEAMS_LIST)}): "))
                if 1 <= team_choice <= len(DEFAULT_TEAMS_LIST):
                    teams = DEFAULT_TEAMS_LIST[team_choice - 1]
                    break
                else:
                    print("Invalid number. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")
    else:
        print("Invalid choice")
        return
 
    use_tag = input("Do you want to use a TAG? (yes/no): ").strip().lower()
    tag = None
    if use_tag in ("yes", "y"):
        tag = input(f"Enter TAG value (default: {DEFAULT_TAG}): ").strip()
        if not tag:  # if user pressed Enter
            tag = DEFAULT_TAG
 
    clean_and_prepare()
    run_install(teams, tag)
    fix_symlinks()
 
 
if __name__ == "__main__":
    main()
