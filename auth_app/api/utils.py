from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

def send_activation_email(user, uid, token):
    activation_link = f"http://127.0.0.1:5500/pages/auth/activate.html/{uid}/{token}/"
    
    # HTML Template rendern
    html_content = render_to_string('activate_mail.html', {
        'username': user.email,
        'activation_url': activation_link
    })
    
    # E-Mail mit HTML versenden
    email = EmailMultiAlternatives(
        subject='Activate your Videoflix account',
        body='Please activate your account',  # Fallback für E-Mail-Clients ohne HTML
        from_email='noreply@videoflix.com',
        to=[user.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()