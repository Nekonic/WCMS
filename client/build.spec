# -*- mode: python ; coding: utf-8 -*-
import os

# 데이터 파일 경로 설정
data_files = []
if os.path.exists('data/system_processes.json'):
    data_files.append(('data/system_processes.json', 'data'))

a = Analysis(
    ['service.py', 'main.py', 'collector.py', 'executor.py', 'config.py', 'utils.py'],  # 모든 소스 파일 명시
    pathex=[],
    binaries=[],
    datas=data_files,
    hiddenimports=[
        'psutil',
        'psutil._pswindows',
        'psutil._psutil_windows',
        'wmi',
        'win32com',
        'win32com.client',
        'pythoncom',
        'pywintypes',
        'requests',
        'urllib3',
        'charset_normalizer',
        'idna',
        'certifi',
        'win32service',
        'win32serviceutil',
        'win32event',
        'servicemanager',
        'win32timezone',
        'win32api',
        'win32con',
        'win32file',
        'win32pipe',
        'win32process',
        'win32security',
        'ntsecuritycon',
        'commctrl',
        'winerror',
        'winreg'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='WCMS-Client',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX 압축 비활성화 (pywin32 DLL 호환성 문제 방지)
    upx_exclude=[
        'pythoncom*.dll',
        'pywintypes*.dll',
        'mfc*.dll',
        'vcruntime*.dll',
        'python*.dll'
    ],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    uac_admin=True  # 관리자 권한 요구
)
