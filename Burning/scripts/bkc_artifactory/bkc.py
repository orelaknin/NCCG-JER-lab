# region imports
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
from os import environ
from os import name as os_name
from os.path import dirname, abspath
from cryptography.fernet import Fernet

# Absolute path of the script
ABS_SCRIPT_PATH = dirname(abspath(__file__))
sys.path.append(dirname(ABS_SCRIPT_PATH))
sys.path.append(dirname(dirname(ABS_SCRIPT_PATH)))

BKC_LOCAL_DIR = '/net/ladhdatamevpo.iil.intel.com/data/BKC_releases/'
# endregion

DEFAULT_RETRIES = 10
DEFAULT_WAIT_TIME = "3s"
DEFAULT_THREADS = 50

TOOLS_PATH_DIR = dirname(abspath(__file__))
JF_TOOL_PATH = os.path.join(TOOLS_PATH_DIR, 'jf' + ('.exe' if os_name == 'nt' else ''))


ARTIFACTORY_KEYS = {
    'ipu-sv-bkc-il-local':
    {
        'key': 'eyJ2ZXJzaW9uIjoyLCJ1cmwiOiJodHRwczovL3ViaXQtYXJ0aWZhY3RvcnktaWwuaW50ZWwuY29tLyIsImFydGlmYWN0b3J5VXJsIjoiaHR0cHM6Ly91Yml0LWFydGlmYWN0b3J5LWlsLmludGVsLmNvbS9hcnRpZmFjdG9yeS8iLCJkaXN0cmlidXRpb25VcmwiOiJodHRwczovL3ViaXQtYXJ0aWZhY3RvcnktaWwuaW50ZWwuY29tL2Rpc3RyaWJ1dGlvbi8iLCJ4cmF5VXJsIjoiaHR0cHM6Ly91Yml0LWFydGlmYWN0b3J5LWlsLmludGVsLmNvbS94cmF5LyIsIm1pc3Npb25Db250cm9sVXJsIjoiaHR0cHM6Ly91Yml0LWFydGlmYWN0b3J5LWlsLmludGVsLmNvbS9tYy8iLCJwaXBlbGluZXNVcmwiOiJodHRwczovL3ViaXQtYXJ0aWZhY3RvcnktaWwuaW50ZWwuY29tL3BpcGVsaW5lcy8iLCJ1c2VyIjoic3lzX3N2X2V4ZWN1dGlvbiIsInBhc3N3b3JkIjoiQVAzTTRBcUJ6ZlpLeWtmVW1xZEJUQzJVdUY1UnNEZHQ3Q2hiTUgiLCJhY2Nlc3NUb2tlbiI6ImV5SjJaWElpT2lJeUlpd2lkSGx3SWpvaVNsZFVJaXdpWVd4bklqb2lVbE15TlRZaUxDSnJhV1FpT2lKNGMzRnVlRGhrVjJaNWJEaFFTRXR2VkUxMlNTMURURWRLVEdGNmMzTlRVbXRIZFhCUlpuRXhVVnBGSW4wLmV5SnpkV0lpT2lKcVppMWhjblJwWm1GamRHOXllVUJpTlRsaFptTTJNQzAyWldaaExUUTBNVEl0T1dSa09DMDFObVptTVdZeU1UZ3pNMkl2ZFhObGNuTXZjM2x6WDNOMlgyVjRaV04xZEdsdmJpSXNJbk5qY0NJNkltMWxiV0psY2kxdlppMW5jbTkxY0hNNktpSXNJbUYxWkNJNkltcG1MV0Z5ZEdsbVlXTjBiM0o1UUdJMU9XRm1Zell3TFRabFptRXRORFF4TWkwNVpHUTRMVFUyWm1ZeFpqSXhPRE16WWlJc0ltbHpjeUk2SW1wbUxXRnlkR2xtWVdOMGIzSjVRR0kxT1dGbVl6WXdMVFpsWm1FdE5EUXhNaTA1WkdRNExUVTJabVl4WmpJeE9ETXpZaTkxYzJWeWN5OXplWE5mYzNaZlpYaGxZM1YwYVc5dUlpd2laWGh3SWpveE56TXpNakU1TnpVMkxDSnBZWFFpT2pFM016TXlNVFl4TlRZc0ltcDBhU0k2SWpSaFlUWTNPV0kxTFdFMk1qQXROR1ExWWkxaE1qRTBMVE0wTnprME5URXdZek0xTkNKOS5pMUtjemV1Si14MGV6aGxhUDNicjJxb0NFWUEwWEU2akJGeF91Y0hvcWlSbklpcldwUkhkeGg0V01oZmFLN3pSM0pQcXJVV19VZkxKOWNOc0o3a29jR0ZLMUp4Zk55akR2X0RxbEVLRXRrdjd2UHJlc2JhUkh5bjNyNXQ0Z21mbUJ2N3ZDc05MVFRIckdid0ppZDVQQkkyTEJxcmhYa0V0OGV1bDBncExoQnhXTm5QN2ZJZWxuN0pvc2d0Mi1SaF81WUt4aG5XNnJzVldpX2lqaTVlV1lDS0dJUG9yVThTcWFram5jcGJZcUVTUEN6OWVhclNfcEVsclptMEhYWDhaa2VvVm1mMnlYRUxfQTJRZ1o3LVB1TEUwRWpic3NfUGJROFR6cEJNQl83RlZtTUhPbWFQdkNwYURsVG1SekpRZ0o5UXVraXV4T2FJSFVBYVJ2eUtUR2ciLCJyZWZyZXNoVG9rZW4iOiI4Yzg5ZmI5Zi1jZmJjLTQwYzEtOGZiNy1iYzhhZGEwMzQyZTAiLCJzZXJ2ZXJJZCI6ImlwdS1zdi1ia2MtaWwtbG9jYWwifQ==',
        'url': 'https://ubit-artifactory-il.intel.com/artifactory',
        'proxy': 'ubit-artifactory-il.intel.com'
    },
    'mountevans_sw_bsp-or-local':
        {
            'key': 'eyJ2ZXJzaW9uIjoyLCJ1cmwiOiJodHRwczovL3ViaXQtYXJ0aWZhY3Rvcnktb3IuaW50ZWwuY29tLyIsImFydGlmYWN0b3J5VXJsIjoiaHR0cHM6Ly91Yml0LWFydGlmYWN0b3J5LW9yLmludGVsLmNvbS9hcnRpZmFjdG9yeS8iLCJkaXN0cmlidXRpb25VcmwiOiJodHRwczovL3ViaXQtYXJ0aWZhY3Rvcnktb3IuaW50ZWwuY29tL2Rpc3RyaWJ1dGlvbi8iLCJ4cmF5VXJsIjoiaHR0cHM6Ly91Yml0LWFydGlmYWN0b3J5LW9yLmludGVsLmNvbS94cmF5LyIsIm1pc3Npb25Db250cm9sVXJsIjoiaHR0cHM6Ly91Yml0LWFydGlmYWN0b3J5LW9yLmludGVsLmNvbS9tYy8iLCJwaXBlbGluZXNVcmwiOiJodHRwczovL3ViaXQtYXJ0aWZhY3Rvcnktb3IuaW50ZWwuY29tL3BpcGVsaW5lcy8iLCJ1c2VyIjoic3lzX3N2X2V4ZWN1dGlvbiIsInBhc3N3b3JkIjoiQVA4VU1ORmY3Sm9EY2pIOW1ubTNwMzM5alJYVEhzRUVkZlM1dVciLCJhY2Nlc3NUb2tlbiI6ImV5SjJaWElpT2lJeUlpd2lkSGx3SWpvaVNsZFVJaXdpWVd4bklqb2lVbE15TlRZaUxDSnJhV1FpT2lKelVIRkNZME01Y0hJelgxcDZTSGt0ZDFwTFkxRXpOMWRMTUhWcmVYcEpjM041WlhvdFJGOXdZazB3SW4wLmV5SnpkV0lpT2lKcVppMWhjblJwWm1GamRHOXllVUExTkRjNFpUY3daaTFtTXpkbUxUUmhaVFl0WW1Zd1ppMDVaV0ZsTXpnek1qVXdZelF2ZFhObGNuTXZjM2x6WDNOMlgyVjRaV04xZEdsdmJpSXNJbk5qY0NJNkltMWxiV0psY2kxdlppMW5jbTkxY0hNNktpSXNJbUYxWkNJNkltcG1MV0Z5ZEdsbVlXTjBiM0o1UURVME56aGxOekJtTFdZek4yWXROR0ZsTmkxaVpqQm1MVGxsWVdVek9ETXlOVEJqTkNJc0ltbHpjeUk2SW1wbUxXRnlkR2xtWVdOMGIzSjVRRFUwTnpobE56Qm1MV1l6TjJZdE5HRmxOaTFpWmpCbUxUbGxZV1V6T0RNeU5UQmpOQzkxYzJWeWN5OXplWE5mYzNaZlpYaGxZM1YwYVc5dUlpd2laWGh3SWpveE56TXpNamszTVRZNUxDSnBZWFFpT2pFM016TXlPVE0xTmprc0ltcDBhU0k2SW1JM05qRXpaRGxtTFRKallUa3ROR1kxWXkxaU56QTRMVGcxTlRVeFkyRTFNREV6WVNKOS5hYndfSEE3eFJDdTVqU1o5VFFNMk82VDItbW83OWJJVzd6TXJQdDdfZy1QaEprd0hyODN6RXNoQ0h4TG5MRUNuX2ZoSVp0RDJpdWc3UDVuS21FNVo1RkFybGUxc2o3ZV8zcThpcUE0LXdUQS1QZHlQcUkwcHY2UzRWSzh6OHB5S1piTEdHbk42WkxHWVBJYVdlZkJBOVd6c2FZMDYxVlFVckMyakFENktpejljOEs1TnRxLUlaVzhVblNHb2ZQdkh0dGstbG1NMnRldDc3bk5XMDFSdVFySVVVRUtJb0JwNFE1QjdzenFPbW5ndlFqUS1vY3B5dk5MZF95TXE5LW1xLTRFTHNYcDkyNlRSMlZoNVFFODRnT1FQZEgzOGpRM25ZazRNcjBFVGVURlVVR0JfMlJRUDNPcnIxYmR0S0I2aFFZRFcyZjZZRE5jOGNWaDBvUzQwWHciLCJyZWZyZXNoVG9rZW4iOiIzODAxYjNmMC1lYmZiLTRmNjQtOTY5OC02M2VkN2Q3MGRmYTkiLCJzZXJ2ZXJJZCI6Im1vdW50ZXZhbnNfc3dfYnNwLW9yLWxvY2FsIn0=',
            'url': 'https://ubit-artifactory-or.intel.com/artifactory',
            'proxy': 'ubit-artifactory-or.intel.com'
        }

}
fernet_key = ENCTYPTION_KEY = ''

class ArtifactoryController:
    """
    A class used to control the interactions with Artifactory

    ...

    Attributes
    ----------
    jf_repo : str
        the repository in JFrog Artifactory
    workspace : str
        the workspace directory
    is_flat : bool
        a flag to indicate if the repository is flat or not
    retention_days : int
        the number of days to retain the artifacts

    Methods
    -------
    decrypt_fernet_key(fernet_key)
        Decrypts the Fernet key
    send_jfrog_cli_command(command)
        Sends a command to the JFrog CLI
    check_results(result, mode)
        Checks the results of the command
    upload_artifacts(folder_items_to_upload, artifactory_dest_folder_path)
        Uploads artifacts to the Artifactory
    download_artifacts(artifactory_src_folder_path, workspace, is_flat)
        Downloads artifacts from the Artifactory
    get_latest_ci_build_completed_folder(artifactory_path)
        Gets the latest CI build completed folder from the Artifactory
    """
    def __init__(self, fernet_key, jf_repo, workspace="", is_flat=True, retention_days=2000):
        """
        Constructs all the necessary attributes for the ArtifactoryController object.

        Parameters
        ----------
            fernet_key : str
                the Fernet key
            jf_repo : str
                the repository in JFrog Artifactory
            workspace : str, optional
                the workspace directory (default is "")
            is_flat : bool, optional
                a flag to indicate if the repository is flat or not (default is True)
            retention_days : int, optional
                the number of days to retain the artifacts (default is None)
        """
        self.jf_repo = jf_repo
        self.workspace = workspace
        self.is_flat = is_flat
        self.retention_days = retention_days
        #jf_key = self._decrypt_fernet_key(fernet_key)
        jf_key = ARTIFACTORY_KEYS[self.jf_repo]['key']


        # Import JFROG configuration
        command = 'echo y | {} c rm && {} c im {}'.format(JF_TOOL_PATH, JF_TOOL_PATH, jf_key)
        cli_result = subprocess.call(command, shell=True)
        if cli_result == 1:
            exit(1)

        # Verify the token and connection are working
        self.test_connection(jf_repo)

    def test_connection(self, jf_repo):
        # Copy the current environment variables
        env = environ.copy()
        env['no_proxy'] = ARTIFACTORY_KEYS[self.jf_repo]['proxy']

        ping_result = subprocess.check_output('{} rt ping --server-id {}'.format(JF_TOOL_PATH, jf_repo),
                                              shell=True, env=env).decode("utf-8")
        assert "OK" in ping_result, 'JFROG init failed with: "Token failed verification"!!!'

    def _decrypt_fernet_key(self, fernet_key):
        cipher_suite = Fernet(fernet_key)
        return cipher_suite.decrypt(ARTIFACTORY_KEYS[self.jf_repo]['key']).decode()

    def send_jfrog_cli_command(self, command):
        """
        Decrypts the Fernet key

        Parameters
        ----------
            fernet_key : str
                the Fernet key

        Returns
        -------
            str
                the decrypted Fernet key
        """
        # Copy the current environment variables
        env = environ.copy()

        # Add or modify environment variables
        # if 'LOCAL_ENV' in environ and environ['LOCAL_ENV'] == '1':
        #     # Not setting proxy for local environment
        #     pass
        # else:
        env['no_proxy'] = ARTIFACTORY_KEYS[self.jf_repo]['proxy']

        print('Sending command: ' + command)
        cli_result = subprocess.check_output(command, shell=True, env=env)

        return json.loads(cli_result.decode('utf-8'))

    def check_results(self, result, mode):
        """
        Sends a command to the JFrog CLI

        Parameters
        ----------
            command : str
                the command to be sent

        Returns
        -------
            dict
                the result of the command
        """
        if 'status' in result and result['status'] == 'success':
            if mode == 'download' and 'success' in result['totals'] and result['totals']['success'] == 0:
                raise Exception("Downloads failed,  not files found")
            if 'success' in result['totals'] and result['totals']['success'] >= 0:
                print("{} artifacts {}ed successfully".format(result['totals']['success'], mode))
            else:
                print("artifacts {}ed failed".format(mode))
                raise Exception("artifacts {}ed failed".format(mode))
        else:
            raise Exception(f'result does not contain "status" or "status" is not "success"')

    def upload_artifacts(self, folder_items_to_upload, artifactory_dest_folder_path):
        """
        Checks the results of the command

        Parameters
        ----------
            result : dict
                the result of the command
            mode : str
                the mode of the command (download or upload)
        """

        ant_mode = False
        cd_cmd = ''

        folder_items_to_upload_clean = folder_items_to_upload.rstrip('/')

        if self.is_flat:

            if os.path.isdir(folder_items_to_upload):

                folder_name = os.path.basename(folder_items_to_upload_clean)
                artifactory_dest_folder_path = os.path.join(artifactory_dest_folder_path, folder_name)

        path, dir_name = os.path.split(folder_items_to_upload_clean)
        cd_cmd = f'cd {path};'
        folder_items_to_upload = dir_name

        if not folder_items_to_upload.endswith("/*"):
            folder_items_to_upload += "/*"

        if not artifactory_dest_folder_path.endswith("/"):
            artifactory_dest_folder_path += "/"

        command = (
            "{} {} rt u \"{}\" \"{}\" --server-id {} --flat={} --retries={}"
            " --retry-wait-time={} --ant={} --recursive --threads={}"
            " --exclusions=\".git/**\" --target-props \"retention.days={}\""
        ).format(
            cd_cmd, JF_TOOL_PATH, folder_items_to_upload, artifactory_dest_folder_path, self.jf_repo, self.is_flat,
            DEFAULT_RETRIES, DEFAULT_WAIT_TIME, ant_mode, DEFAULT_THREADS, self.retention_days
        )
        result = self.send_jfrog_cli_command(command=command)
        self.check_results(result, "upload")

    def download_artifacts(self, artifactory_src_folder_path, workspace, is_flat):
        """
        Downloads artifacts from the specified Artifactory source folder path to the local workspace.

        Parameters
        ----------
        artifactory_src_folder_path : str
            The path in the Artifactory from where the artifacts are to be downloaded.
        workspace : str
            The local path where the artifacts are to be downloaded.
        is_flat : bool
            A flag indicating whether the repository structure is flat or not.

        Returns
        -------
        None
        """

        command = '{} rt dl \"{}\" \"{}\" --server-id {} --recursive --flat={} --threads={} --retries={} --retry-wait-time={}'.format(
            JF_TOOL_PATH,
            artifactory_src_folder_path,
            workspace, self.jf_repo, is_flat, DEFAULT_THREADS, DEFAULT_RETRIES, DEFAULT_WAIT_TIME)
        result = self.send_jfrog_cli_command(command=command)
        self.check_results(result, "download")

    def get_latest_ci_build_completed_folder(self, artifactory_path):
        """
        Retrieves the latest CI build completed folder from the specified Artifactory path.

        Parameters
        ----------
        artifactory_path : str
            The path in the Artifactory where the CI build completed folders are located.

        Returns
        -------
        tuple
            A tuple containing the name and path of the latest CI build completed folder. If no such folder is found, returns (None, None).
        """
        # Command to list directories in the given Artifactory path
        command = '"{}" rt s "{}*/build_completed" --server-id {} --recursive=false --count=0 --include-dirs'.format(
            JF_TOOL_PATH, artifactory_path, self.jf_repo)

        # Send the command and get the result
        result = self.send_jfrog_cli_command(command=command)

        # If the command was successful and found some directories
        if len(result) > 0:
            # Sort the directories by creation date (newest first)
            sorted_dirs = sorted(result, key=lambda x: x['created'], reverse=True)

            latest_ci_build_path = sorted_dirs[0]['path'].replace('/build_completed', '')
            latest_ci_build_name = sorted_dirs[0]['path'].replace('/build_completed', '').replace(artifactory_path, '')

            return latest_ci_build_name, latest_ci_build_path
        else:
            print(f'Could not find any matches for path: {artifactory_path}')

        # If no directory containing the "build_completed" file was found, return None
        return None, None

    def upload_file(self, local_file_path, artifactory_dest_path):
        """
        Uploads a single file to the Artifactory

        Parameters
        ----------
            local_file_path : str
                the local path of the file to be uploaded
            artifactory_dest_path : str
                the destination path in the Artifactory
        """
        command = '"{}" rt u {} {}/{}'.format(JF_TOOL_PATH, local_file_path, self.jf_repo, artifactory_dest_path)
        result = self.send_jfrog_cli_command(command)
        self.check_results(result, "upload")

    def download_file(self, artifactory_src_path, local_dest_path):
        """
        Downloads a single file from the Artifactory

        Parameters
        ----------
            artifactory_src_path : str
                the source path in the Artifactory of the file to be downloaded
            local_dest_path : str
                the local destination path where the file will be downloaded
        """
        command = f"download {self.jf_repo}/{artifactory_src_path} {local_dest_path} --flat={str(self.is_flat).lower()}"
        result = self.send_jfrog_cli_command(command)
        self.check_results(result, "download")

    def search_latest_artifact(self, path):
        command = 'jf rt s "{}/*/" --sort-by created '.format(path)
        result = self.send_jfrog_cli_command(command)
        try:
            latest = result[-1]['path']
        except:
            print('\033[91mFailed to found latest artifact\033[0m')
            sys.exit(1)
        return os.path.dirname(latest)


def copy_ci_files_from_laas_automation(ci_name, ci_temp_dir, project):
    bkc_local_path = f'{BKC_LOCAL_DIR}/{project.upper()}/'
    ci_namber = ci_name.split('-')[-1]
    flag = False
    for dir in os.listdir(bkc_local_path):
        if ci_namber in dir:
            try:
                flag = True
                os.makedirs(f'{ci_temp_dir}/unzip_automation_files', exist_ok=True)
                cmd = f'cp -rf {bkc_local_path}/{dir}/* {ci_temp_dir}/unzip_automation_files/'
                subprocess.call(cmd, shell=True)
                print(f'\033[95mAutomation files copied successfully from {bkc_local_path}/{dir}\033[0m')
            except:
                print('\033[91mFailed to copy unzip file from automation\033[0m')
            finally:
                break
    if not flag:
        print(f'\033[93mWarning: There is not automation files in BKC dir for CI {ci_name}\033[0m')


argument_parser = argparse.ArgumentParser(prog="artifactory", description="CLI for upload and download ci from artifactory")
action_type = argument_parser.add_argument_group(title="Actions")

action_type.add_argument("-u", "--upload", action="store_true", default=False, help="Upload Artifact")
action_type.add_argument("-d", "--download", action="store_true", default=False, help="Download Artifact")

argument_parser.add_argument("-p", "--project", choices=['mev', 'mev-ts', 'mmg'], required=True, help=" name of project")
argument_parser.add_argument("-ci", "--ci", help='Ci folder to upload/download', required=True)
args = argument_parser.parse_args()

if not (args.upload or args.download):
    print("\033[91mError: You must specify either --upload or --download\033[0m")
    sys.exit(1)


if args.upload:
    # download official ci from mountevans_sw artifactory
    ci_path = args.ci.replace('https://ubit-artifactory-or.intel.com/artifactory/','')
    if not ci_path.endswith('/'):
        ci_path = ci_path + '/'
    if not ci_path.endswith('deploy/'):
        ci_path = ci_path + 'deploy/'
    ci_name = ci_path.split('/')[-3]
    temp_dir_path = f"{os.path.expanduser('~/')}/Downloads/{ci_name}/"
    print(f'\033[94mDownload CI {ci_name} from SW artifactory to temp dir \033[0m')
    os.mkdir(temp_dir_path)
    try:
        ci_images_artifact = ArtifactoryController(fernet_key, 'mountevans_sw_bsp-or-local')
        if args.project == 'mev':
            ci_images_artifact.download_artifacts(ci_path+'ipu*', temp_dir_path, is_flat=True)
            ci_images_artifact.download_artifacts(ci_path + '*hw*', temp_dir_path, is_flat=True)
        elif args.project == 'mev-ts':
            ci_images_artifact.download_artifacts(ci_path + 'internal_only/hw-flash*', temp_dir_path, is_flat=True)
            ci_images_artifact.download_artifacts(ci_path + 'oem-generic/intel-ipu-eval*', temp_dir_path, is_flat=True)
    except Exception as e:
        if os.path.exists(temp_dir_path):
            shutil.rmtree(temp_dir_path)
        print(f'\033[91mFailed download ci from sw artifactory\033[0m')
        print(e)

    # copy automation files for temp folder
    copy_ci_files_from_laas_automation(ci_name, temp_dir_path, args.project)

    # upload temp folder
    artifact = ArtifactoryController(fernet_key, 'ipu-sv-bkc-il-local', is_flat=False)
    artifact_path = os.path.join(artifact.jf_repo, args.project.upper())
    print(f'\033[94mUpload temp ci folder to BKC artifactory\033[0m')
    artifact.upload_artifacts(temp_dir_path, artifact_path)

    # delete temp folder
    if os.path.exists(temp_dir_path):
        shutil.rmtree(temp_dir_path)
    ci_url = f'{ARTIFACTORY_KEYS[artifact.jf_repo]["url"]}/{artifact.jf_repo}/{args.project.upper()}/{ci_name}'
    print(f'\033[92mUpload ci {ci_name} successfully completed\033[0m')
    print(f'\033[92m{ci_url}\033[0m')

if args.download:
    artifact = ArtifactoryController(fernet_key, 'ipu-sv-bkc-il-local')
    if args.ci == 'latest':
        ci = artifact.search_latest_artifact(os.path.join(artifact.jf_repo, args.project.upper()))
        ci = os.path.basename(ci)
    else:
        ci = args.ci
    ci_path = os.path.join(artifact.jf_repo, args.project.upper(), ci)
    print(f'\033[94mDownload {ci} from artifactory\033[0m')
    download_dest = '/home/laduser/Downloads/{}/'.format(ci)
    if not os.path.exists(download_dest):
        os.mkdir(download_dest)
    artifact.download_artifacts(ci_path+'/', download_dest, is_flat=False)
    print('Download done in {}'.format(ci_path))
