"""명령별 실행 모듈. 각 모듈은 execute(data: dict) -> str 함수를 제공."""
from .shutdown import execute as shutdown
from .restart import execute as restart
from .show_message import execute as show_message
from .kill_process import execute as kill_process
from .install import execute as install
from .uninstall import execute as uninstall
from .create_user import execute as create_user
from .delete_user import execute as delete_user
from .change_password import execute as change_password
from .execute_cmd import execute as execute_cmd
from .download import execute as download

HANDLERS: dict[str, callable] = {
    'shutdown':       shutdown,
    'restart':        restart,
    'reboot':         restart,  # 하위 호환
    'show_message':   show_message,
    'message':        show_message,  # 하위 호환
    'kill_process':   kill_process,
    'install':        install,
    'uninstall':      uninstall,
    'create_user':    create_user,
    'delete_user':    delete_user,
    'change_password': change_password,
    'execute':        execute_cmd,
    'download':       download,
}