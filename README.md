# drc-containers

Custom Docker images for use with the XNAT Container Service

---

## How to add a new python command to the Docker image

### 1. Create an executable python script

See
[share_subject_to_genetic_project.py](src/drc_containers/share_subject_to_genetic_project.py)
for an example.

The hostname and login credentials are provided by the XNAT container service
through environment variables `XNAT_HOME`, `XNAT_USER` and `XNAT_PASSWORD`. You
can use the XnatContainerCredentials class as a convenient way of fetching these
automatically.

If your script requires additional inputs, you can provide these as command line
arguments. These can be read in using Python's `sys.argv`. Note that this is an
array and the first argument is the function being executed

If you need to add additional python module dependencies, you will need to
configure these in `pyproject.toml` in the `[project]` section, e.g.:
```toml
[project]
dependencies = [
    "pandas",
    "pyxnat",
    "xnat",
]
```

To test your script locally, you can either run it on the command line with the
above XNAT environment variables set for your XNAT server and user name and
password. Or, following the example of share_subject_to_genetic_project.py, you
can create a method within your script which takes all the necessary arguments
and you can call this from within a python shell or test function.

### 2. Add a python entrypoint

This is not strictly necessary, but it is convenient to add a python entrypoint
to the `pyproject.toml`. This will create an executable alias to your python
script when the python code is installed.

To do this, add an additional line to `pyproject.toml` under the
`project.scripts` section:

```toml
[project.scripts]
share_subject_to_genetic_project = "drc_containers:share_subject_to_genetic_project.main"
your_new_command_alias = "drc_containers:your_new_command_module.main"
```

Note that in the above syntax, `your_new_command_alias` will be the alias that
is generated, and `"drc_containers:your_new_command_module.main"` points to the
entry function for your script. In this case it is the `main` function in the
module `your_new_command_module` which is part of the package `drc_containers`.

### 3. Add a JSON Command Definition file

This is a file describing the commands you wish to add to XNAT that will call
your container.

- See
  [share_subject_to_genetic_project.json](share_subject_to_genetic_project.json)
  for an example.
- See
  [XNAT documentation](https://wiki.xnat.org/container-service/json-command-definition)
  for full details.

### 4. Run `generate_docker_label.py`

This generates a Docker label for the XNAT container service.

Add this to the end of the Dockerfile (including the `LABEL` statement and
replacing any existing label).

### 5. Commit and push the changes to the repository

---

## How to run the commands on XNAT

### 1. Pull the image

If the image is not currently installed:

- Go to Administer > Plugin Settings > Container Service > Images & Commands
- Click `New Image`
- Under Select Image Host, select `GitHub`
- For Image Name, enter `ghcr.io/ucl-mirsg/drc-containers`
- Click `Pull Image`

If a previous version of this image already exists, you may need to pull the
update on the Docker server to update it

Your commands should now appear in the list of `Installed Images and Commands`

:warning: if your image and commands do not appear, click on the
`x Images Hidden` at the bottom of the panel. If they appear as hidden images,
it means XNAT could not find or process the Docker image label which defines the
commands. This indicates there may be an error in your JSON command file
configurations or in the Docker label generated from those command file
configurations, or the label may have not been added to the Docker image.

### 2. Enable the commands

- Go to Administer > Plugin Settings > Container Service > Command
  Configurations
- Enable all the commands you wish to use

### 3. Configure Event Service automation

If you want containers to run automatically in response to new events (such as
creating a project or subject), you can configure this using the Event Service,

- Go to Administer > Event Service > Event Setup
- Ensure `Enable Event Service` is enabled
- Click `Add New Event Subscription`
- Under `Label` write a description of what the event will do
- Under `Select Event` choose the trigger (for example `Subject -- Created`)
- Check `Apply to All Projects`, unless you wish to apply this only to selected
  projects
- Under `Select Action` choose your command. See below if your command does not
  appear.
- Switch `Status` to `Enabled`
- Click `OK`

Note: you do not need to enable commands in each project settings to use event
service automation.

#### Troubleshooting

If you cannot add your commands, or they do not appear on XNAT where expected:

- Ensure the JSON command file is correct
- Ensure the JSON command file has the correct context for the trigger (for
  example, `xnat:subjectData` context can be triggered at the Create Subject
  level)
- Ensure the JSON command files have been correctly converted to a Docker label
  and added to the Dockerfile (using `generate_docker_label.py`) - unless this
  is done automatically using GitHub Actions, in which case ensure the created
  package on the GitHub container registry has the correct label

### 4. Enable commands at a project level

You only need to do this if you would like users to be able to trigger
containers from the user interface

- Go to an XNAT project
- In the Actions menu on the right, click `Project Settings`
- Under `Configure Commands` enable the commands you wish to make available to
  users

The enabled commands will be available on the Actions menu under
`Run Containers` at the context relevant to the command. For example, subject
commands will be available on subject pages.

---

## Copyright

2024 University College London

## Licence

See [LICENSE.txt](`./LICENSE.txt`)
