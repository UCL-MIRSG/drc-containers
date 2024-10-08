import sys

from pyxnat import Interface

from drc_containers.xnat_utils.email import send_email
from drc_containers.xnat_utils.xnat_credentials import (
    open_pyxnat_session,
    XnatContainerCredentials,
    XnatCredentials,
)


def get_subject_labels_for_phase(
    pyxnat_interface: Interface, datatype: str, project_name: str, phase: int
) -> set[str]:
    """Return list of sessions in this project for the specified datatype which
    have a label matching the specified phase number

    Args:
        pyxnat_interface:  PyXnat session interface
        datatype: data type to search for
        project_name: project to search in
        phase: phase number to search for in the session label

    Returns:
        set of subject labels
    """
    columns = [
        datatype + "/SESSION_ID",
        datatype + "/SUBJECT_LABEL",
        datatype + "/DATE",
        datatype + "/LABEL",
        datatype + "/PROJECT",
    ]
    label_pattern = f"%\\_{phase:02d}\\_%"
    constraints = [
        (datatype + "/project", "=", project_name),
        (datatype + "/label", "LIKE", label_pattern),
        "AND",
    ]
    sessions = pyxnat_interface.select(datatype, columns).where(constraints)
    subject_labels = set(session["label"].split("_", 1)[0] for session in sessions.data)
    return subject_labels


def get_session_labels(
    pyxnat_interface: Interface, datatype: str, project_name: str
) -> set[str]:
    """Return list of subject labels in this project

    Args:
        pyxnat_interface: PyXnat session interface
        datatype: data type to search for
        project_name: project to search in

    Returns:
        set of subject labels from datatypes in matching project
    """
    columns = [datatype + "/LABEL", datatype + "/SUBJECT_LABEL", datatype + "/PROJECT"]
    constraints = [(datatype + "/project", "=", project_name), "AND"]
    sessions = pyxnat_interface.select(datatype, columns).where(constraints)
    subjects = set(
        [session["subject_label"].split("_", 1)[0] for session in sessions.data]
    )

    return subjects


def construct_email(server_url: str, project: str, subjects_to_do: set[str]) -> str:
    body_html = (
        "<p>The following subjects have phase 3 PET-MR sessions but "
        "do not have corresponding Chenies Mews MR data:"
    )
    body_html += "<p>"

    for subject_label in subjects_to_do:
        link_form = f"{server_url}/data/projects/{project}/subjects/{subject_label}"
        body_html += f'Subject: <a href="{link_form}">{subject_label}</a> Project: {project}<br><br>'

    return body_html


def email_chenies(
    credentials: XnatCredentials,
    project_name: str,
    email_subject: str,
    to_emails: list[str],
    cc_emails: list[str] = None,
    bcc_emails: list[str] = None,
):
    """Email notification about image sessions without radreads

    Args:
        credentials: XNAT host name and user login details
        project_name: The project to search for PETMR sessions
        email_subject: subject line of email
        to_emails: list of email addresses. XNAT will only send emails
            to addresses which already correspond to XNAT users on the server
        cc_emails: list of email addresses for cc. XNAT will only send emails
            to addresses which already correspond to XNAT users on the server
        bcc_emails: list of email addresses for bcc. XNAT will only send emails
            to addresses which already correspond to XNAT users on the server
    """

    mr_projects = ["CHENIES_TRANSFER", "CHENIES_MRI"]
    with open_pyxnat_session(credentials=credentials) as pyxnat_interface:
        # Get list of subjects containing phase 3 PET-MR sessions
        phase3_petmr_subjects = get_subject_labels_for_phase(
            pyxnat_interface=pyxnat_interface,
            datatype="xnat:petmrSessionData",
            phase=3,
            project_name=project_name,
        )
        subjects_with_mr = set()
        for mr_project in mr_projects:
            subjects_with_mr = subjects_with_mr | get_session_labels(
                pyxnat_interface=pyxnat_interface,
                datatype="xnat:mrSessionData",
                project_name=mr_project,
            )
        subjects_to_do = set()
        for subject_label in phase3_petmr_subjects:
            if subject_label not in subjects_with_mr:
                print(f"NOT FOUND: {subject_label}")
                subjects_to_do.add(subject_label)

        if len(subjects_to_do) > 0:
            # Construct email html body
            body_html = construct_email(
                server_url=credentials.host,
                project=project_name,
                subjects_to_do=subjects_to_do,
            )

            # Send the email via XNAT
            send_email(
                session=pyxnat_interface,
                subject=email_subject,
                to=to_emails,
                cc=cc_emails,
                bcc=bcc_emails,
                content_html=body_html,
            )


def main():
    if len(sys.argv) < 3:
        raise ValueError("No email list specified")
    if len(sys.argv) < 2:
        raise ValueError("No project name specified")

    credentials = XnatContainerCredentials()

    email_chenies(
        credentials=credentials,
        project_name=sys.argv[1],
        email_subject="1946 update: Chenies Mews phase 3 data",
        to_emails=sys.argv[2].split(","),
    )


if __name__ == "__main__":
    main()
