"""generate_docker_label.py

Creates a docker label for use with the XNAT container service.

This script is for generating a label which you manually add to the Dockerfile.
You do not need to use this script if your labels are automatically generated
as part of the automated GitHub Actions automated Docker image build process.

Before using this script you must have one or more JSON command definition
files which describe the commands that will run with your docker image.
See the XNAT documentation:
https://wiki.xnat.org/container-service/json-command-definition

Run this script in the directory containing all your JSON command definition
files:

python ./generate_docker_label.py

This will output to the command line a LABEL statement which can be added to
your Dockerfile.

"""

import json
import os


def main():
    repo_dir = os.getcwd()

    command_list = []
    for file in os.listdir(repo_dir):
        if file.endswith(".json"):
            with open(file) as f:
                command_object = json.load(f)
                command_string = json.dumps(command_object).\
                    replace('"', r'\"').replace('$', r'\$')
                command_list.append(command_string)

    commands = ', \\\n\t'.join(command_list)
    label = f'org.nrg.commands="[{commands}]"'
    print(f"LABEL {label}")


if __name__ == '__main__':
    main()
