from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage


def send_mail(subject, tomail, part_content, tourl):
    from_email = 'Ezgobuyusa@gmail.com'
    text_content = f'''
            親愛的電商系統會員您好：
            {part_content}：
            {tourl}
            '''

    html_content = ''
    with open('./api/mail/index.html') as f:
        html_content = f.read()

    html_content = html_content.replace('{{URL}}', tourl)
    html_content = html_content.replace('{{CONTENT}}', part_content)

    msg = EmailMultiAlternatives(subject, text_content, from_email, [tomail])
    msg.attach_alternative(html_content, "text/html")

    with open('./api/mail/images/亞帆_200x64px.png', mode='rb') as f:
        image = MIMEImage(f.read())
        image.add_header('Content-Id', '<logoimg>')  # angle brackets are important
        image.add_header("Content-Disposition", "inline", filename="logoimg")
        msg.attach(image)

    msg.send()
