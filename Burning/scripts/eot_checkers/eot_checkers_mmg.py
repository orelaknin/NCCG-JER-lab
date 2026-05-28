import os
import sys
import csv
import re
import subprocess
import argparse
from datetime import datetime

IMC_user = "root"
IMC_ip = "100.0.0.100"

parser = argparse.ArgumentParser()
prepost_group = parser.add_mutually_exclusive_group(required=False)
prepost_group.add_argument('--pre', dest='pre', action='store_true', default=False,
                           help='Dump CSRs before any test (clean system)')
prepost_group.add_argument('--post', dest='post', action='store_true', default=False, help='Dump CSRs after test(s)')

parser.add_argument('--compare', action='store_true', default=False, help='Compare the pre/post results',
                    required=False)
parser.add_argument('--test', help='Test name to add to RESULTS.csv file', required=False)
parser.add_argument('--driver', dest='driver', help='sv/commercial - The driver type', required=True)

args = parser.parse_args()


def LOG(file, str):
    print(str, end='')
    file.writelines(str)


def check_imc_connection():
    res = os.system(f"ping -c 1 {IMC_ip} > /dev/null")
    if res != 0:
        sys.exit(f"IMC is not responsive!\nPlease check the connection before running this tool")


def run_script_and_get_results(stage, mode):
    cmd = f"scp -o StrictHostKeyChecking=no ./read_csrs.sh {IMC_user}@{IMC_ip}:/home/root > /dev/null"
    res = os.system(cmd)

    if res != 0:
        sys.exit(f"Read CSRs script not copied to IMC")

    cmd = f"ssh -o StrictHostKeyChecking=no {IMC_user}@{IMC_ip} \"sh /home/root/read_csrs.sh > results_{stage}_{mode}_tests.csv\""
    res = os.system(cmd)

    if res != 0:
        sys.exit(f"Read CSRs script not copied to IMC")

    cmd = f"scp -o StrictHostKeyChecking=no {IMC_user}@{IMC_ip}:/home/root/results_{stage}_{mode}_tests.csv ./ > /dev/null"
    res = os.system(cmd)

    if res != 0:
        sys.exit(f"Results file not copied from IMC")

    cmd = f"ssh -o StrictHostKeyChecking=no {IMC_user}@{IMC_ip} \"rm -rf /home/root/results_{stage}_{mode}_tests.csv /home/root/read_csrs.sh\""
    res = os.system(cmd)

    os.remove("./read_csrs.sh")


def prepare_lan_cpf_for_bar4_access():
    try:
        lan_cpf = subprocess.check_output('lspci -d:1453', shell=True, text=True)
    except Exception as e:
        print("LAN CPF is mandatory for access to BAR4 while IDPF is using LAN PF. Please check why it doesn't appear in lspci")
        exit()

    # Get lan cpf bus/device/function and the offset of the debug bar
    lan_cpf = lan_cpf.split(" ")[0]
    #print(lan_cpf)
    lan_cpf_bar4 = subprocess.check_output('sudo lspci -d:1453 -v', shell=True, text=True)
    #print(lan_cpf_bar4)
    memory_lines = re.findall(r"Memory at .+", lan_cpf_bar4)
    offset = None
    for word in memory_lines[-1].split(" "):
        try:
            offset_hex = hex(int(word, 16))
            offset = offset_hex
            break
        except ValueError as e:
            continue

    # Enable lan cpf bars
    cmd = f"sudo setpci -s:{lan_cpf} 0x4.w=0x6"
    #print(cmd)
    reg_value = subprocess.check_output(cmd, shell=True, text=True)

    return offset

def prepare_reads_csrs_script(stage, mode, driver_type="sv"):
    with open(f"{mode}_regs_db_mmg.csv", mode="r") as regs_file:
        reader = csv.reader(regs_file)
        # sv_driver_path = subprocess.check_output('svdt -c  | grep \"loaded\"', shell=True, text=True)
        # sv_driver_path = sv_driver_path.split(':')[1].strip()
        # print(f"Using read_csr.py from: {sv_driver_path}")

        if driver_type == "commercial":
            debug_bar_offset = prepare_lan_cpf_for_bar4_access()

        with open(f"results_{stage}_{mode}_tests.csv", mode="w") as res_file:
            for row in reader:
                if len(row) == 0:
                    continue

                if driver_type == "sv":
                    cmd = f"read-csr -a {row[1]} -b 4"
                    reg_value = subprocess.check_output(cmd, shell=True, text=True).splitlines()[2].split("value: ")[1].strip()
                else:
                    bar4_reg_address = int(row[1], 16) + int(debug_bar_offset, 16)
                    cmd = f"sudo devmem2 {hex(bar4_reg_address)}"
                    #print(cmd)
                    reg_value = subprocess.check_output(cmd, shell=True, text=True)
                    reg_value = reg_value.split(":")[1].strip()
                
                print(reg_value)

                line = f"{row[1]},{row[0]},{reg_value}\n"
                res_file.write(line)


def compare_dumps(mode, res_filename):
    pre_tests_data = []
    post_tests_data = []
    failures = []

    pre_dump_file = open(f"results_pre_{mode}_tests.csv", mode="r")
    reader_pre = csv.reader(pre_dump_file)

    post_dump_file = open(f"results_post_{mode}_tests.csv", mode="r")
    reader_post = csv.reader(post_dump_file)

    for row in reader_pre:
        pre_tests_data.append(row)

    for row in reader_post:
        post_tests_data.append(row)

    pre_dump_file.close()
    post_dump_file.close()

    if len(pre_tests_data) != len(post_tests_data):
        print(f"Pre tests data = {len(pre_tests_data)}\nPost tests data = {len(post_tests_data)}")
        pre_dump_file.close()
        post_dump_file.close()
        sys.exit("The CSV files don't have the same number of rows, check them before comparing")

    for item_pre, item_post in zip(pre_tests_data, post_tests_data):
        if item_pre[1] != item_post[1]:
            sys.exit(
                f"Trying to compare {item_pre} to {item_post}\nThe CSV files don't have the same list of CSRs, check them before comparing")

        if item_pre[2] == '' or item_post[2] == '':
            sys.exit(f"Failed to read CSR \"{item_pre[1]}\", check its address in the database file")

        if mode == "credits":
            if item_pre[2] != item_post[2] and not bool(re.search("icm_eg_dispresp_glb_stat", item_pre[1])):
                failures.append(
                    f"Credit CSR: {item_pre[1]} ({item_pre[0]}) - Pre-tests value = {item_pre[2]} | Post-tests value = {item_post[2]}")
        else:
            if int(item_post[2][2:] != 0):
                if item_post[2] != item_pre[2] and not bool(re.search("icm_eg_dispresp_glb_stat", item_pre[1])):
                    failures.append(
                        f"Error CSR: {item_pre[1]} ({item_pre[0]}) - Pre-tests value = {item_pre[2]} | Post-tests value = {item_post[2]}")
    
    result_file = open(res_filename, mode="a")

    log_mode = f"========================= {mode.upper()} =========================\n"
    LOG(result_file, log_mode)

    if len(failures) != 0:
        res_log = "FAIL\n"
        LOG(result_file, res_log)

        for failure in failures:
            LOG(result_file, failure + "\n")

    else:
        res_log = "PASS"
        LOG(result_file, res_log)

    LOG(result_file, "\n\n")

    result_file.close()


if __name__ == '__main__':
    if args.pre is False and args.post is False and args.compare is False:
        sys.exit("Please provide a parameter (use -h)")

    if args.driver != "sv" and args.driver != "commercial":
        sys.exit("Please provice \"sv/commercial in --driver flag\"")

    if args.compare is False:
        # check_imc_connection()

        if args.pre is True:
            print("Running pre-tests CSRs dump")
            stage = "pre"
        elif args.post is True:
            print("Running post-tests CSRs dump")
            stage = "post"

        prepare_reads_csrs_script(stage, mode="credits", driver_type=args.driver)
        # run_script_and_get_results(stage, mode="credits")

        # prepare_reads_csrs_script(stage, mode="errors")
        # run_script_and_get_results(stage, mode="errors")

    else:
        print(f"Comparing the pre/post dumps...")
        timestamp = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        res_filename = f"RESULTS_{args.test}_{timestamp}.txt"
        compare_dumps(mode="credits", res_filename=res_filename)
        # compare_dumps(mode="errors", res_filename=res_filename)
        print(f"DONE. Results in {res_filename}")
