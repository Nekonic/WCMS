from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.models import EnrollmentToken


class Command(BaseCommand):
    help = "관리자 계정을 만들고 비밀번호·인증 앱 등록 링크를 출력한다. 첫 관리자를 만들 때 쓴다."

    def add_arguments(self, parser) -> None:
        parser.add_argument("username")

    def handle(self, *args, username: str, **options) -> None:
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            raise CommandError("이미 있는 아이디입니다.")
        user = User.objects.create_user(username=username, is_staff=True)
        _, token = EnrollmentToken.issue(user=user, purpose=EnrollmentToken.NEW, created_by=None)
        self.stdout.write(f"/enroll/{token}")
