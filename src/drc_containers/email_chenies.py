from argparse import ArgumentParser
from dataclasses import dataclass

from pyxnat import Interface
from pyxnat.core.resources import Experiments

from drc_containers.xnat_utils.command_line import string_to_list
from drc_containers.xnat_utils.email import send_email
from drc_containers.xnat_utils.xnat_credentials import (
    open_pyxnat_session,
    XnatContainerCredentials,
    XnatCredentials,
)


@dataclass(frozen=True)
class PetmrSessionRecord:
    """Store data from sessions missing Chenies Mews MR data
    The frozen dataclass allows this to be used in a set to ensure no sessions
    are repeated"""

    id: str
    label: str
    subject_label: str
    date: str


def get_sessions_for_phase(
    pyxnat_interface: Interface, datatype: str, project_name: str, phase: int
) -> Experiments:
    """Return sessions in this project for the specified datatype which
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
    return sessions


def get_subject_labels(
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
    columns = [datatype + "/SUBJECT_LABEL", datatype + "/PROJECT"]
    constraints = [(datatype + "/project", "=", project_name), "AND"]
    sessions = pyxnat_interface.select(datatype, columns).where(constraints)
    subjects = set(
        [session["subject_label"].split("_", 1)[0] for session in sessions.data]
    )

    return subjects


def construct_email(
    server_url: str, project_name: str, sessions_to_do: set[PetmrSessionRecord]
) -> str:
    """Assemble the email html content with links to the subjects

    Args:
        server_url: Full URL of the XNAT server
        project_name: ID of the XNAT project
        sessions_to_do: set of PetmrSessionRecords to be linked in the email

    Returns:
        String containing the email body as HTML
    """
    body_html = (
        "<p>The following subjects have phase 3 PET-MR sessions but "
        "do not have corresponding Chenies Mews MR data:"
    )
    body_html += "<p>"

    for session in sessions_to_do:
        link_form = (
            f"{server_url}/data/projects/{project_name}"
            f"/subjects/{session.subject_label}"
        )
        body_html += (
            f'<a href="{link_form}">Subject:{session.subject_label}'
            f"</a> &nbsp; phase 3 session date: {session.date}<br><br>"
        )

    return body_html


def run_email_chenies(
    credentials: XnatCredentials,
    project_name: str,
    mr_projects: list[str],
    email_subject: str,
    to_emails: list[str],
    cc_emails: list[str] = None,
    bcc_emails: list[str] = None,
):
    """Email notification about subjects which are missing phase 3 Chenies Mews
     data

    The XNAT project "project_name" is searched for PET-MR sessions
    containing "_03_" in the session label, indicating phase 3 data.
    These subject labels are checked against the subject names in all projects
    specified by the list "mr_projects".

    Any subjects which have phase 3 PET-MR data but no corresponding MR data
    are listed in an email sent to the email addresses. Email addresses must
    correspond to registered XNAT users.

    Args:
        credentials: XNAT host name and user login details
        project_name: The project to search for PETMR sessions
        mr_projects: List of projects to search for MR sessions
        email_subject: subject line of email
        to_emails: list of email addresses. XNAT will only send emails
            to addresses which already correspond to XNAT users on the server
        cc_emails: list of email addresses for cc. XNAT will only send emails
            to addresses which already correspond to XNAT users on the server
        bcc_emails: list of email addresses for bcc. XNAT will only send emails
            to addresses which already correspond to XNAT users on the server
    """

    with open_pyxnat_session(credentials=credentials) as pyxnat_interface:
        # Get list of subjects containing phase 3 PET-MR sessions
        phase3_petmr_sessions = get_sessions_for_phase(
            pyxnat_interface=pyxnat_interface,
            datatype="xnat:petmrSessionData",
            phase=3,
            project_name=project_name,
        )
        subjects_with_mr = set()
        for mr_project in mr_projects:
            subjects_with_mr = subjects_with_mr | get_subject_labels(
                pyxnat_interface=pyxnat_interface,
                datatype="xnat:mrSessionData",
                project_name=mr_project,
            )
        subjects_already_added = set()
        sessions = set()
        for session in phase3_petmr_sessions:
            session_id = session["session_id"]
            session_label = session["label"]
            session_date = session["date"]
            subject_label = session_label.split("_", 1)[0]
            if subject_label not in subjects_with_mr:
                print(f"Phase 3 subject missing MR data: {subject_label}")

                # Only store the first session found for each subject
                if subject_label not in subjects_already_added:
                    sessions.add(
                        PetmrSessionRecord(
                            id=session_id,
                            label=session_label,
                            subject_label=subject_label,
                            date=session_date,
                        )
                    )
                    subjects_already_added.add(subject_label)

        if len(sessions) > 0:
            # Construct email html body
            body_html = construct_email(
                server_url=credentials.host,
                project_name=project_name,
                sessions_to_do=sessions,
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


def main(args=None):
    """Entrypoint for email_chenies, as listed in pyproject.toml.

    Args:
        args: list of arguments. If not set these will be read from the
            command-line

    When called by the container, this method is called with no arguments, so
    args is set to None. ArgParser will read arguments from the command line.

    The command-lone arguments are:
        email_chenies petmr_project mr_projects email_list

        where:
            petmr_project is the ID of the project containing the PET-MR
                sessions
            mr_projects is a comma-delimited string containing the project IDs
                of all the projects containing the MR data
            email_list is a comma-delimited string containing the email
                addresses where the email will be sent

        For example:
            email_chenies "PETMRPROJ" "MRPROJECT1,MRPROJECT2" "user1@foo.org,user2@foo.org"

    For testing, main() can be called with an argument list to simulate
    command-line arguments, eg:
        main(['PETMRPROJ', 'MRPROJECT1,MRPROJECT2', 'user1@foo.org,user2@foo.org'])

    """
    parser = ArgumentParser()
    parser.add_argument("petmr_project")
    parser.add_argument("mr_projects")
    parser.add_argument("email_list")
    parsed = parser.parse_args(args)

    project_name = parsed.petmr_project
    mr_projects = string_to_list(parsed.mr_projects)
    to_emails = string_to_list(parsed.email_list)

    credentials = XnatContainerCredentials()

    run_email_chenies(
        credentials=credentials,
        project_name=project_name,
        mr_projects=mr_projects,
        email_subject="1946 update: Chenies Mews phase 3 data",
        to_emails=to_emails,
    )


if __name__ == "__main__":
    main()
