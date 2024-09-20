import sys
from dataclasses import dataclass

from pyxnat import Interface

from drc_containers.xnat_utils.email import send_email
from drc_containers.xnat_utils.xnat_credentials import (
    XnatContainerCredentials,
    XnatCredentials,
    open_pyxnat_session,
)


@dataclass(frozen=True)
class SessionRecord:
    """Store data from sessions requiring a Radiological Read.
    The frozen dataclass allows this to be used in a set to ensure no sessions
    are repeated"""

    id: str
    label: str
    subject_id: str


def session_prefix(session_1_label: str) -> str:
    """Return session label excluding _EARLY or _LATE suffixe"""
    return session_1_label.removesuffix("_EARLY").removesuffix("_LATE")


def filter_sessions(
    pyxnat_interface: Interface,
    project_name: str,
    datatype: str,
    exclude_ids: set[str],
    exclude_session_substrings: list[str],
) -> set[SessionRecord]:
    """Return a set of SessionRecords, one for each session of the
    specified datatype which exists in the specified project and contains at
    least one scan of type T1, T2 or FLAIR, determined by examining the
    scan Type fields. Sessions are excluded from the output list if their ID
    appears in the specified exclude_ids set

    Args:
        pyxnat_interface: PyXnat interface
        project_name: Name of project to search
        datatype: Datatype of session to search for
        exclude_ids: set of session IDs to exclude from output
        exclude_session_substrings: ignore sessions with labels containing any
            of these substrings

    Returns:
        set of SessionRecords, one for each session
    """
    sessions = set()
    condition = [(datatype + "/PROJECT", "=", project_name), "AND"]
    columns = [
        datatype + "/SESSION_ID",
        datatype + "/SUBJECT_ID",
        datatype + "/LABEL",
        datatype + "/PROJECT",
    ]
    image_sessions = pyxnat_interface.select(datatype, columns).where(condition)

    exclude_labels = []
    for session in image_sessions.data:
        session_id = session["session_id"]
        session_label = session["label"]
        if session_id in exclude_ids:
            exclude_labels.append(session_prefix(session_label))

    for session in image_sessions.data:
        session_id = session["session_id"]
        session_label = session["label"]
        subject_id = session["subject_id"]

        # Exclude any sessions exactly matching IDs in the exclude_ids list
        if session_prefix(session_label) not in exclude_labels:
            # Exclude any sessions whose label contains any of the label
            # patterns in the exclude_label_patterns list
            exclude = False
            for label_pattern in exclude_session_substrings:
                if label_pattern in session_label:
                    exclude = True
            if not exclude:
                scans = (
                    pyxnat_interface.select.project(project_name)
                    .subject(subject_id)
                    .experiment(session_id)
                    .scans()
                )
                scan_found = False
                for scan in scans:
                    scan_type = scan.attrs.get("type")
                    if "FLAIR" in scan_type or "T1" in scan_type or "T2" in scan_type:
                        scan_found = True
                        break

                if scan_found:
                    print(f"FLAIR, T1, or T2 found in session {session_id}")
                    sessions.add(
                        SessionRecord(
                            id=session_id, label=session_label, subject_id=subject_id
                        )
                    )

    return sessions


def get_sessions_needing_radread(
    pyxnat_interface: Interface,
    project_name: str,
    exclude_session_substrings: list[str],
) -> set[SessionRecord]:
    """Return list of sessions which require a Radiological Read

    Args:
        pyxnat_interface: pyxnat interface
        project_name: name of XNAT project to search
        exclude_session_substrings: ignore sessions with labels containing any
            of these substrings

    Returns:
        set of SessionRecords, one for each session which requires a read
    """

    session_datatypes = [
        "xnat:mrSessionData",
        "xnat:petSessionData",
        "xnat:petmrSessionData",
    ]
    constraints = [("nshdni:radRead/project", "=", project_name)]
    rr_sessions = pyxnat_interface.select(
        "nshdni:radRead", ["nshdni:radRead/imagesession_id"]
    ).where(constraints)
    sessions_with_radread = set(
        r["nshdni_col_radreadimagesession_id"] for r in rr_sessions.data
    )

    # Iterate through all session datatypes
    session_list = set()
    for datatype in session_datatypes:
        # Get IDs of sessions which are not in the sessions_with_radread set
        sessions = filter_sessions(
            pyxnat_interface=pyxnat_interface,
            project_name=project_name,
            datatype=datatype,
            exclude_ids=sessions_with_radread,
            exclude_session_substrings=exclude_session_substrings,
        )
        session_list |= sessions

    return session_list


def construct_email_body(
    server_url: str, project_name: str, session_records: set[SessionRecord]
) -> str:
    """Assemble the email html content with links to the sessions

    Args:
        server_url: URL of the XNAT server
        project_name: name of the XNAT project
        session_records: set of SessionRecords describing sessions which shoulf
            be linked in the email

    Returns:
        str containing the email body as HTML
    """
    body_html = (
        "<p>The following sessions in the 1946 XNAT database require "
        "radiology reads:"
    )

    for session in session_records:
        session_id = session.id
        session_label = session.label
        link_form = f"{server_url}/app/action/DisplayItemAction/search_value&#47;{session_id}&#47;search_element&#47;xnat:petmrSessionData&#47;search_field&#47;xnat:petmrSessionData.ID&#47;project&#47;{project_name}"

        body_html += f"<p>{session_label}<br>"
        body_html += (
            f'<a href="{link_form}">Electronic form for reporting '
            f"radiology read</a><br>"
        )
    return body_html


def email_radreads(
    credentials: XnatCredentials,
    project_name: str,
    email_subject: str,
    to_emails: list[str],
    cc_emails: list[str] = None,
    bcc_emails: list[str] = None,
    exclude_session_substrings: list[str] = [],
    debug_output: bool = True,
):
    """Email notification about image sessions without radreads

    Args:
        credentials: XNAT host name and user login details
        project_name: The project to search for sessions
        email_subject: subject line of email
        to_emails: list of email addresses. XNAT will only send emails
            to addresses which already correspond to XNAT users on the server
        cc_emails: list of email addresses for cc. XNAT will only send emails
            to addresses which already correspond to XNAT users on the server
        bcc_emails: list of email addresses for bcc. XNAT will only send emails
            to addresses which already correspond to XNAT users on the server
        exclude_session_substrings: ignore sessions with labels containing any
            of these substrings
        debug_output: set to True to output debugging data to the console
    """

    with open_pyxnat_session(credentials=credentials) as xnat_session:
        # Get list of SessionRecords describing sessions which require radread
        sessions_needing_radread = get_sessions_needing_radread(
            pyxnat_interface=xnat_session,
            project_name=project_name,
            exclude_session_substrings=exclude_session_substrings,
        )
        if debug_output:
            print("Sessions requiring radread:")
            if len(sessions_needing_radread) > 0:
                for s in sessions_needing_radread:
                    print(s)
            else:
                print("None found")

        if len(sessions_needing_radread) > 0:
            # Construct email html body
            body_html = construct_email_body(
                server_url=credentials.host,
                project_name=project_name,
                session_records=sessions_needing_radread,
            )

            # Send the email via XNAT
            send_email(
                session=xnat_session,
                subject=email_subject,
                to=to_emails,
                cc=cc_emails,
                bcc=bcc_emails,
                content_html=body_html,
                debug_output=debug_output,
            )


def main():
    if len(sys.argv) < 3:
        raise ValueError("No email list specified")
    if len(sys.argv) < 2:
        raise ValueError("No project name specified")

    credentials = XnatContainerCredentials()
    email_radreads(
        credentials=credentials,
        project_name=sys.argv[1],
        email_subject="1946 update: Weekly Radiology Reads Email",
        to_emails=sys.argv[2].split(","),
        exclude_session_substrings=["_MR_20151215", "_MR_20151111"],
    )


if __name__ == "__main__":
    main()