from __future__ import absolute_import
import platform
import sys
import subprocess

def burn_ssd(image_file):
        if platform.system() != "Linux":
            raise NotImplementedError("burn_ssd is not supported on this OS.")
        
        from datetime import timedelta
        import time
        
        try:
            def run_imc_command(command):
                return subprocess.run(['ssh', 'IMC', command], capture_output=True, text=True).returncode

            # Remove any existing SSH key for the IMC host
            try:
                ssh_keygen_process = subprocess.Popen(["ssh-keygen", "-R", "100.0.0.100"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                ssh_keygen_process.wait()
                if ssh_keygen_process.returncode != 0:
                    print("Warning: Failed to remove existing SSH key for IMC host")
            except Exception as e:
                print(f"Warning: Error removing SSH key: {e}")
            
            print(f"Unmount all on IMC side")

            # Execute each command and get return status
            return_status1 = run_imc_command('/etc/init.d/syslogmode DEV')
            # return_status2 = run_imc_command('umount /mnt/imc/')
            # return_status3 = run_imc_command('umount /mnt/')
            # return_status4 = run_imc_command('umount /log')
            
            cmd = f"(pv -fB 512M -f {image_file} | ssh IMC 'dd of=/dev/nvme0n1 bs=512M') |& stdbuf -oL tr '\r' '\n'"
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
            output = process.stdout.readline().decode("utf-8").strip()
            eta_str = output.split("ETA ")[1]
            parts = eta_str.split(":")
            
            if len(parts) == 4:  # Format includes days
                days, hours, minutes, seconds = map(int, parts)
                eta_timedelta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
            elif len(parts) == 3:  # Format does not include days
                hours, minutes, seconds = map(int, parts)
                eta_timedelta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
            else:
                raise ValueError(f"Unexpected ETA format: {eta_str}")
            
            time_out = eta_timedelta.total_seconds()
            time_run = time_out * 4
            while "bytes" not in output:
                if time_run <= 0 :
                    raise Exception("Time Out of SSD burn")
                start = time.perf_counter()
                print(output)
                output = process.stdout.readline().decode("utf-8").strip()
                sys.stdout.flush()
                end = time.perf_counter()
                time_run = time_run - (end-start)
            print(output)
            return True, "SSD burn successfully"
        except Exception as e:
            return False, str(e)