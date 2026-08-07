def build_password_reset_otp_email(otp_code, expires_in_minutes):
    """Returns (subject, plain_text_body) for the "Forgot password?" OTP
    email - plain text, matching build_customization_interest_email's
    convention of a bare formatter function, not a class."""
    subject = "Your VStitch password reset code"
    body = (
        f"Your one-time code to reset your VStitch password is: {otp_code}\n\n"
        f"This code expires in {expires_in_minutes} minutes.\n\n"
        "If you didn't request this, you can safely ignore this email - your "
        "password will not be changed.\n\n"
        "— VStitch by Anjali Nanda"
    )
    return subject, body
