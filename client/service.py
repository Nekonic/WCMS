import sys

if sys.platform == 'win32':
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    import threading
    import subprocess
    import ctypes
    import os
    import logging
    from logging.handlers import RotatingFileHandler

    SERVICE_NAME = "WCMS-Client"

    def setup_install_logging():
        try:
            log_dir = os.path.join(os.environ.get('PROGRAMDATA', os.getcwd()), 'WCMS', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, 'installer.log')
            logger = logging.getLogger('installer')
            logger.setLevel(logging.INFO)
            if not logger.handlers:
                handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
                formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            return logger
        except Exception:
            return logging.getLogger('installer')

    def is_admin() -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def is_service_installed() -> bool:
        try:
            win32serviceutil.QueryServiceStatus(SERVICE_NAME)
            return True
        except Exception:
            return False

    class WCMSClientService(win32serviceutil.ServiceFramework):
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = "WCMS Client Service"
        _svc_description_ = "WCMS 원격 관리 클라이언트. 부팅 시 자동 시작되어 서버와 통신합니다."

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hStopEvent = win32event.CreateEvent(None, 0, 0, None)
            self.stop_event = threading.Event()

        def GetAcceptedControls(self):
            # PreShutdown 이벤트 수락 선언
            rc = win32serviceutil.ServiceFramework.GetAcceptedControls(self)
            rc |= win32service.SERVICE_ACCEPT_PRESHUTDOWN
            return rc

        def SvcOtherEx(self, control, event_type, data):
            # PreShutdown 이벤트 핸들링
            if control == win32service.SERVICE_CONTROL_PRESHUTDOWN:
                import logging
                logger = logging.getLogger('service_runtime')
                logger.info("PreShutdown 이벤트 감지! 서버에 종료 신호를 보냅니다.")
                
                try:
                    from main import send_shutdown_signal
                    send_shutdown_signal()
                except Exception as e:
                    logger.error(f"종료 신호 전송 중 오류: {e}")
                
                self.SvcStop() # 서비스 종료 절차 시작
            return win32service.NO_ERROR

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            try:
                self.stop_event.set()
                win32event.SetEvent(self.hStopEvent)
            finally:
                self.ReportServiceStatus(win32service.SERVICE_STOPPED)

        def SvcDoRun(self):
            servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                  servicemanager.PYS_SERVICE_STARTED,
                                  (self._svc_name_, "started"))

            # 서비스 로거 추가 (installer.log에 기록)
            import logging
            svc_logger = logging.getLogger('service_runtime')
            svc_logger.setLevel(logging.INFO)
            try:
                log_dir = os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'WCMS', 'logs')
                os.makedirs(log_dir, exist_ok=True)
                fh = logging.FileHandler(os.path.join(log_dir, 'service_runtime.log'), encoding='utf-8')
                fh.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
                svc_logger.addHandler(fh)
            except:
                pass

            try:
                svc_logger.info('======= 서비스 시작 =======')
                svc_logger.info(f'Python 실행 파일: {sys.executable}')
                svc_logger.info(f'작업 디렉토리: {os.getcwd()}')
                svc_logger.info('main 모듈 임포트 시도...')

                from main import run_client
                svc_logger.info('main 모듈 임포트 성공')
                svc_logger.info('run_client 실행 시작...')

                run_client(self.stop_event)

                svc_logger.info('run_client 정상 종료')
            except ImportError as e:
                error_msg = f"모듈 임포트 실패: {e}"
                svc_logger.error(error_msg)
                import traceback
                svc_logger.error(traceback.format_exc())
                servicemanager.LogErrorMsg(error_msg)
            except Exception as e:
                error_msg = f"WCMS Client Service error: {e}"
                svc_logger.error(error_msg)
                import traceback
                svc_logger.error(traceback.format_exc())
                servicemanager.LogErrorMsg(error_msg)

    if __name__ == '__main__':
        logger = setup_install_logging()
        if len(sys.argv) > 1:
            # 명시적 관리 명령 전달 (install/start/stop/remove/status ...)
            win32serviceutil.HandleCommandLine(WCMSClientService)
        else:
            # 인자 없이 실행되면: 사용법 출력 후 종료 (중복 실행 방지)
            logger.error('사용법: WCMS-Client.exe [install|start|stop|remove]')
            print('\n사용법: WCMS-Client.exe [install|start|stop|remove|restart]')
            print('  install - 서비스 설치')
            print('  start   - 서비스 시작')
            print('  stop    - 서비스 중지')
            print('  remove  - 서비스 제거')
            sys.exit(1)
else:
    if __name__ == '__main__':
        print('WCMS Client Service는 Windows에서만 지원됩니다.')
