from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage
from mimetypes import guess_type


def send_mail(subject, tomail, part_content, tourl):
    """
    寄信功能
    :param subject: 主題
    :param tomail: user
    :param part_content: 部分內容，因為剩下內容有固定格式要組成
    :param tourl: 驗證網址等 傳給範例template
    :return:
    """
    from_email = 'Ezgobuyusa@gmail.com'
    text_content = f'''
            親愛的汴利購會員您好：
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

    with open('./api/mail/images/HFMU_200x64px.svg', 'rb') as f:
        image = f.read()
        image = MIMEImage(image, **{'_subtype': subtype})
        image.add_header('Content-Id', '<logoimg>')  # angle brackets are important
        image.add_header("Content-Disposition", "inline", filename="logoimg")
        msg.attach(image)

    msg.send()
