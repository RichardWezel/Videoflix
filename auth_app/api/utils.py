from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

def _build_email(user, subject, fallback_body):
    return EmailMultiAlternatives(
        subject=subject,
        body=fallback_body,  # Fallback für E-Mail-Clients ohne HTML
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )

def send_activation_email(user, uid, token):
    activation_link = f"http://127.0.0.1:5500/pages/auth/activate.html?uid={uid}&token={token}"

    html_content = render_to_string('activate_mail.html', {
        'username': user.email,
        'activation_url': activation_link
    })

    email = _build_email(user, 'Activate your Videoflix account', 'Please activate your account')
    email.attach_alternative(html_content, "text/html")
    email.send()

def send_password_reset_email(user, uid, token):
    reset_link = f"http://127.0.0.1:5500/pages/auth/confirm_password.html?uid={uid}&token={token}"

    html_content = render_to_string('password_reset_mail.html', {
        'username': user.email,
        'reset_url': reset_link
    })

    email = _build_email(user, 'Reset your Password', 'Please reset your password')
    email.attach_alternative(html_content, "text/html")
    email.send()