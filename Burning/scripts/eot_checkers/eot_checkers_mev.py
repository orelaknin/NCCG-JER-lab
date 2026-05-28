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


def prepare_reads_csrs_script(mode):
    with open(f"{mode}_regs_db.csv", mode="r") as regs_file:
        reader = csv.reader(regs_file)

        with open("read_csrs.sh", mode="w") as read_csrs_script:

            for row in reader:
                if len(row) == 0:
                    continue

                cmd = f"echo {row[1]},{row[0]},$(devmem {row[1]})\n"
                read_csrs_script.write(cmd)


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

    if args.compare is False:
        check_imc_connection()

        if args.pre is True:
            print("Running pre-tests CSRs dump")
            stage = "pre"
        elif args.post is True:
            print("Running post-tests CSRs dump")
            stage = "post"

        prepare_reads_csrs_script(mode="credits")
        run_script_and_get_results(stage, mode="credits")

        prepare_reads_csrs_script(mode="errors")
        run_script_and_get_results(stage, mode="errors")

    else:
        print(f"Comparing the pre/post dumps...")
        timestamp = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        res_filename = f"RESULTS_{args.test}_{timestamp}.txt"
        compare_dumps(mode="credits", res_filename=res_filename)
        compare_dumps(mode="errors", res_filename=res_filename)
        print(f"DONE. Results in {res_filename}")
