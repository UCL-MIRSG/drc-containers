import re
import sys

from drc_containers.xnat_utils.xnat_credentials import open_xnat_session, \
    XnatContainerCredentials, XnatCredentials


def share_to_project(subject, other_project_id, debug=False):
    try:
        shared_to_project = [x for x in subject.sharing.values() if
                             x.id == other_project_id]
        if shared_to_project:
            print(f"{subject.label} is already shared with project "
                  f"{other_project_id}")
        if not shared_to_project:
            print(f"Sharing {subject.label} to {other_project_id}")
            if debug:
                print(f"DEBUG MODE: no actual sharing will be performed")
            else:
                subject.share(other_project_id, label=subject.label)
    except Exception as ex:
        raise RuntimeError(f"Exception {str(ex)} while trying to share "
                           f"subject {subject.label}")


def share_subject_to_genetic_project(credentials: XnatCredentials,
                                     subject_id: str):
    """Share the specified subject to the corresponding genetic project

    Args:
        credentials: XNAT host name and user login details
        subject_id: ID of the subject to share
    """
    site_pattern = re.compile("^GENFI_\d\d$")

    with open_xnat_session(credentials) as xnat_session:
        if subject_id not in xnat_session.subjects:
            raise ValueError(f"Subject {subject_id} not found")
        subject = xnat_session.subjects[subject_id]
        project_id = subject.project

        # If this project has a GENFI3 naming convention then share to the
        # genetic project
        if site_pattern.match(project_id):
            genetic_project_id = project_id + "_GEN"
            if genetic_project_id not in xnat_session.projects:
                print(
                    f"Not sharing subject {subject_id} because no genetic "
                    f"project {genetic_project_id} was found")
            else:
                share_to_project(
                    subject=subject,
                    other_project_id=genetic_project_id
                )
        else:
            print(f"Not sharing subject {subject_id} because parent project "
                  f"{project_id} is not a GENFI3 project")


def main():
    if len(sys.argv) < 2:
        raise ValueError("No subject label specified")
    credentials = XnatContainerCredentials()
    share_subject_to_genetic_project(
        credentials=credentials, subject_id=sys.argv[1])


if __name__ == '__main__':
    main()
