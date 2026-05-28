import os
import json
import argparse
from requests.auth import HTTPBasicAuth

try:
    import requests
except:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--proxy=https://proxy-chain.intel.com:911", "requests"])


USER = 'svtools'
PASSWORD = 'SVSW@123'
BKC_DIR = '/net/ladhdatamevpo.iil.intel.com/data/BKC_releases/'


def download_data_from_artifactory(ci_version):
    """
     Get data from version_report.json file in the ci
     Args:
         ci_version (str): full path of ci version
     """
    component_file = os.path.join(ci_version, 'version_report.json')
    print('Reading the file: {}'.format(component_file))
    response = requests.get(component_file, auth=HTTPBasicAuth(USER, PASSWORD))
    if response.status_code == 200:
        data = response.json()
        return data
    if response.status_code == 404:
        print(f'\033[91mURL {component_file} not found\033[0m')
        exit(10)
    else:
        print(f'Error occur while download file, Return code: {response.status_code}')
        exit(1)


def parse_components_file(project, step,  data, kernel):
    """
        This function parse the data and return the necessary data according the project
        Args:
            project (str): project for the ci details
            step (str):  project step
            data (dict): all the data from artifactory for the ci
            kernel (str) : kernel version
        """
    dict = {}
    kernel = kernel.replace('.', '_')
    for component in data['components']:
        for key, value in component.items():
            if 'IMC' in key:
                if project == 'mev' and 'IPU' in key and kernel in key or project == 'mmg':
                    dict['imc'] = value['build_full_number']
                    print('IMC: ', value['build_full_number'])
            elif 'ACC' in key:
                if project == 'mev' and project.upper() in key and step in key or project == 'mmg':
                    dict['acc'] = value['build_full_number']
                    print('ACC: ', value['build_full_number'])
            elif 'F37' in key and project == 'mev' and project.upper() in key and step in key or project == 'mmg':
                dict['fedora'] = value['build_full_number']
                print('Fedora: ', value['build_full_number'])
    return dict


def write_for_bkc(project, ci_details, ci_name):

    """
    This function write the ci info into the bkc sv folder
    Args:
        project (str): project for the ci details
        ci_details (dict) :  dict with the ci_details
        ci_name (str) : ci version name e.g. ci-release-10562
    """
    json_file = os.path.join(BKC_DIR, project.upper(), 'ci_details.json')
    data = {}
    with open(json_file, 'r') as file:
        try:
            data = json.load(file)
        except Exception as e:
            print('Error occur when open the file {} on json format : {}'.format(json_file, e))
            exit(10)

    print(data['ci_details'])
    if ci_name not in data['ci_details']:
        data['ci_details'][ci_name] = ci_details
        print('Added new ci_details:', ci_details)
    else:
        print('Ci details {} already exist in the data'.format(ci_name))

    with open(json_file, 'w') as file:
        json.dump(data, file, indent=4)


if __name__ == '__main__':

    """
     The script search the ci details from version_report.json file in the artifactory of each ci.
     Then take the the necessary information and store on bkc SV execution folder
    """

    parser = argparse.ArgumentParser("ci_details")

    # Required arguments
    parser.add_argument("-p", "--project", help="Project", required=True)
    parser.add_argument("-s", "--step", help="Project step", default='C0')
    parser.add_argument("-k", "--kernel", help="Kernel version", default='6.1')
    parser.add_argument("-ci", "--ci_version", help="Full ci path from artifactory", required=True)

    args = parser.parse_args()
    ci_ver = args.ci_version.rstrip('/')
    ci_name = os.path.basename(ci_ver)
    print('CI NAME:',  ci_name)
    data = download_data_from_artifactory(ci_ver)
    dict_parse_date = parse_components_file(args.project, args.step, data, args.kernel)
    write_for_bkc(args.project, dict_parse_date, ci_name)
