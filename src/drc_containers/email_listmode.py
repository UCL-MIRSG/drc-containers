from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import datetime, timedelta

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
class ListModeRecord:
    """Store data from sessions with listmode errors
    The frozen dataclass allows this to be used in a set to ensure no sessions
    are repeated"""

    id: str
    label: str
    subject_id: str
    date: str
    errors: str


def get_recent_sessions(
    pyxnat_interface: Interface, datatype: str, threshold_days: int, project_name: str
) -> Experiments:
    threshold_date = datetime.now() - timedelta(threshold_days)
    str_threshold_date = threshold_date.strftime("%Y-%m-%d")
    columns = [
        datatype + "/SESSION_ID",
        datatype + "/SUBJECT_ID",
        datatype + "/DATE",
        datatype + "/LABEL",
        datatype + "/PROJECT",
    ]
    constraints = [
        (datatype + "/project", "=", project_name),
        (datatype + "/date", ">=", str_threshold_date),
        "AND",
    ]
    return pyxnat_interface.select(datatype, columns).where(constraints)


def check_session(
    pyxnat_interface: Interface, session_id: str, project_name: str
) -> [str]:
    resources = (
        pyxnat_interface.select.project(project_name).experiment(session_id).resources()
    )

    num_lm_files = 0
    num_norm_files = 0
    lm_found = False
    norm_found = False
    errors = []

    for resource in resources:
        res_label = resource.label()
        if res_label == "LM":
            lm_found = True
            for file in resource.files():
                num_lm_files += 1
                file_label = file.label()
                try:
                    if ".bf" in file_label:
                        file_size = file.size()
                        if int(file_size) < 1000000:
                            errors.append(
                                f"LM File is too small " f"{file_label} - {file_size}"
                            )
                except:  # noqa: E722
                    pass
        elif res_label == "Norm":
            norm_found = True
            for _ in resource.files():
                num_norm_files += 1

    if not lm_found:
        errors.append("LM does not exist")
    elif num_lm_files != 2:
        errors.append(f"Wrong number of LM files {num_lm_files}")

    if not norm_found:
        errors.append("Norm does not exist")
    elif num_norm_files != 2:
        errors.append(f"Wrong number of Norm files: {num_lm_files}")
    return errors


def get_listmode_issues(
    pyxnat_interface: Interface, threshold_days: int, project_name: str
) -> set[ListModeRecord]:
    """Get list of sessions which have errors in the listmode data

    Args:
        pyxnat_interface: current pyxnat session
        threshold_days: check only sessions created within this number of days
        project_name: name of project in which to check sessions

    Returns:
        set of ListModeRecords, each describing a session with missing listmode
            data
    """
    session_datatypes = [
        "xnat:crSessionData",
        "xnat:mrSessionData",
        "xnat:otherDicomSessionData",
        "xnat:petSessionData",
        "xnat:petmrSessionData",
        "xnat:srSessionData",
    ]
    issue_list = set()

    for datatype in session_datatypes:
        sessions = get_recent_sessions(
            pyxnat_interface=pyxnat_interface,
            datatype=datatype,
            threshold_days=threshold_days,
            project_name=project_name,
        )
        for session in sessions.data:
            session_id = session["session_id"]
            session_label = session["label"]
            subject_id = session["subject_id"]
            session_date = session["date"]

            errors = check_session(
                pyxnat_interface=pyxnat_interface,
                session_id=session_id,
                project_name=project_name,
            )
            if len(errors) > 0:
                error_string = ", ".join(errors)
                message = (
                    f"Subject ID: {subject_id}   "
                    f"Scan Date: {session_date}   "
                    f"Errors: {error_string}<br>"
                )
                issue_list.add(
                    ListModeRecord(
                        id=session_id,
                        label=session_label,
                        subject_id=subject_id,
                        date=session_date,
                        errors=message,
                    )
                )

    return issue_list


def construct_email(
    server_url: str, project_name: str, list_mode_records: set[ListModeRecord]
) -> str:
    """Assemble the email html content with links to the subjects

    Args:
        server_url: Full URL of the XNAT server
        project_name: ID of the XNAT project
        list_mode_records: set of ListModeRecord to be linked in the email

    Returns:
        String containing the email body as HTML
    """
    body_html = "<p>"

    for session in list_mode_records:
        link_form = (
            f"{server_url}/data/projects/{project_name}"
            f"/subjects/{session.subject_id}"
        )

        body_html += f'<a href="{link_form}">Subject ID:{session.subject_id}</a> &nbsp; Scan Date:{session.date} Errors:{session.errors}<br>'
    return body_html


def email_listmode(
    credentials: XnatCredentials,
    project_name: str,
    email_subject: str,
    to_emails: list[str],
    threshold_days: int = 90,
    cc_emails: list[str] = None,
    bcc_emails: list[str] = None,
    debug_output: bool = True,
):
    """Email notification about image sessions with listmode errors

    Sessions created within the number of days set by threshold_days are
    checked for missing or incorrect listmode data. Any errors found are
    listed in an email sent to the specified email addresses.

    Args:
        credentials: XNAT host name and user login details
        project_name: The project to search for sessions
        threshold_days: check only sessions created within this number of days
        email_subject: subject line of email
        to_emails: list of email addresses. XNAT will only send emails
            to addresses which already correspond to XNAT users on the server
        cc_emails: list of email addresses for cc. XNAT will only send emails
            to addresses which already correspond to XNAT users on the server
        bcc_emails: list of email addresses for bcc. XNAT will only send emails
            to addresses which already correspond to XNAT users on the server
        debug_output: set to True to output debugging data to the console
    """

    with open_pyxnat_session(credentials=credentials) as xnat_session:
        # Get list of ListModeRecords
        sessions_to_report = get_listmode_issues(
            pyxnat_interface=xnat_session,
            threshold_days=threshold_days,
            project_name=project_name,
        )

        if debug_output:
            print("Sessions failing listmode checks:")
            if len(sessions_to_report) > 0:
                for s in sessions_to_report:
                    print(s)
            else:
                print("None found")

        if len(sessions_to_report) > 0:
            # Construct email html body
            body_html = construct_email(
                server_url=credentials.host,
                project_name=project_name,
                list_mode_records=sessions_to_report,
            )

            # Print email content so it is visible in the container log
            print("Sending email with the following content:")
            print(f"To: {to_emails}")
            print(f"cc: {cc_emails}")
            print(f"bcc: {bcc_emails}")
            print(f"Subject: {email_subject}")
            print(body_html)

            # Send the email via XNAT
            send_email(
                session=xnat_session,
                subject=email_subject,
                to=to_emails,
                cc=cc_emails,
                bcc=bcc_emails,
                content_html=body_html,
            )


def main(args=None):
    """Entrypoint for email_listmode, as listed in pyproject.toml.

    Args:
        args: list of arguments. If not set these wil be read from the
            command-line

    When called by the container, this method is called with no arguments, so
    args is set to None. ArgParser will read arguments from the command line.

    The command-lone arguments are:
        email_listmode project threshold_days email_list

        where:
            project is the ID of the project containing the PET-MR
                sessions
            threshold_days only recent sessions will be checked. This is the
                threshold for the number of days prior to the current date
            email_list is a comma-delimited string containing the email
                addresses where the email will be sent

        For example:
            email_listmode "PROJID" "90" "user1@foo.org,user2@foo.org"

    For testing, main() can be called with an argument list to simulate
    command-line arguments, eg:
        main(['PROJID', '90', 'user1@foo.org,user2@foo.org'])

    """
    parser = ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("threshold_days")
    parser.add_argument("email_list")
    parsed = parser.parse_args(args)

    project_name = parsed.project
    threshold_days_str = parsed.threshold_days
    to_emails = string_to_list(parsed.email_list)

    try:
        threshold_days = int(threshold_days_str)
    except ValueError:
        raise ValueError("Invalid input for threshold days: " "{threshold_days_str}")

    credentials = XnatContainerCredentials()

    email_listmode(
        credentials=credentials,
        project_name=project_name,
        threshold_days=threshold_days,
        email_subject="1946 Weekly Listmode Status Check",
        to_emails=to_emails,
    )


if __name__ == "__main__":
    main()
