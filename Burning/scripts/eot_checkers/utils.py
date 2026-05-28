import os
import subprocess



def run_eot_flow(job, path, test_name=''):
    """
    Args:
       path (str): Path to logs of test
       test_name (str): Test name
    Returns:
        str: Eot Flow credits results
        str: Eot Flow error results
        str: Eot logs
    """
    if not path and not test_name:
        error = "No test path/name was given"
        return 'N/A', error, 'N/A'  # TODO

    utils_path = "{}/Orama/orama_code/core/utils/eot_checkers/".format(os.path.expanduser('~'))
    script_name = 'eot_checkers_{}.py'.format(job.project.lower())
    if not test_name:
        job.log("Trying to get test name from given path '{}'".format(path))
        test_name = os.path.basename(path).replace("http://", "/net/")
    else:
        test_name = os.path.basename(test_name).replace('.py', '')

    args = ''
    if job.project.lower() == 'mmg':
        args = '--driver {}'.format('sv' if 'Denver' in job.tool.name else 'commercial')
    cmd = "python {}/{} {} --post".format(utils_path, script_name, args)
    cmd1 = "python {}/{} --compare {} --test {}".format(utils_path, script_name, args, test_name)

    try:
        job.log("Collecting Eot Flow")
        subprocess.check_output(cmd, shell=True, cwd=utils_path).decode()
        output = subprocess.check_output(cmd1, shell=True, cwd=utils_path).decode()
        output = output.splitlines()
        credits = output[2]
        try:
            err = output.index("========================= ERRORS =========================")
            error = output[err + 1]
        except:
            error = None

        logs = output[-1].replace('DONE. Results in ', '')

        # collect log files to server:
        log_path = os.path.join(path.replace('http://', '/net/'), 'eot_checkers_logs')
        os.system("mkdir {}".format(log_path))
        log_files = ['results_pre_credits_tests.csv', 'results_pre_errors_tests.csv',
                     'results_post_credits_tests.csv', 'results_post_errors_tests.csv', logs]
        for file in log_files:
            if os.path.exists(os.path.join(utils_path, file)):
                os.system("cp {}/{} {}".format(utils_path, file, log_path))
                os.system('rm -f {}/{}'.format(utils_path, file))

        path = path.replace("/net/", "http://")
        logs = os.path.join(path, logs)

        return credits, error, logs
    except Exception as e:
        job.log("Fail to collect eot result, Unexpected error: {}".format(e))
        return 'N/A', 'N/A', 'N/A'


def run_eot_pre_checkers(job):
    """
    Runs EOT pre checkers
    """
    try:
        utils_path = "{}/Orama/orama_code/core/utils/eot_checkers/".format(os.path.expanduser('~'))
        script_name = 'eot_checkers_{}.py'.format(job.project.lower())
        job.log("Running pre eot checkers")
        args = ''
        if job.project == 'mmg':
            args = '--driver {}'.format('sv' if 'Denver' in job.tool.name else 'commercial')
        subprocess.check_output("python {}/{} {} --pre".format(utils_path, script_name, args),
                                shell=True, cwd=utils_path)
    except subprocess.CalledProcessError:
        job.log("Failed to run pre eot checkers")
