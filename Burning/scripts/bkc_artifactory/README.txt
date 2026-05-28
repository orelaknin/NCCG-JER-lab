CLI for upload and download ci from artifactory

usage: 
artifactory [-h] [-u] [-d] [-p {mev,mev-ts,mmg}] [-f FOLDER]

options:
  -h, --help            show this help message and exit
  -p {mev,mev-ts,mmg}, --project {mev,mev-ts,mmg}
                        name of project
  -f FOLDER, --folder FOLDER
                        Ci folder to upload/download

Actions:
  -u, --upload          Upload Artifact
  -d, --download        Download Artifact

