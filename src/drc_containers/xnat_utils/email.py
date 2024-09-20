from pyxnat import Interface


def send_email(
    session: Interface,
    subject: str,
    content_html: str,
    to: list[str],
    cc: list[str] = None,
    bcc: list[str] = None,
    debug_output: bool = True,
):
    """Use XNAT API to send an email

    Args:
        session: pyXnat session
        subject: email subject
        content_html: string containing HTML email body text
        to: list of strings, each containing an email address. XNAT will only
            send the email to addresses which correspond to registered users
        cc: list of strings, each containing an email address. XNAT will only
            send the email to addresses which correspond to registered users
        bcc: list of strings, each containing an email address. XNAT will only
            send the email to addresses which correspond to registered users
        debug_output: set to True to output the email text to the console in
            addition to sending the email
    """
    if debug_output:
        # Print email content so it is visible in the container log
        print("Sending email to with the following content:")
        print(f"To: {to}")
        print(f"cc: {cc}")
        print(f"bcc: {bcc}")
        print(f"Subject: {subject}")
        print(content_html)

    url = "/data/services/mail/send"
    body = {"to": to, "cc": cc, "bcc": bcc, "subject": subject, "html": content_html}
    session._exec(uri=url, method="POST", body=body)
