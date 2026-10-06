"""Collect validated cumulative customs exports; never overwrite prior reports."""
import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from minjung.AXPORT_widget._axport_semiconductor_widgets.app_connection import load_root_env
from minjung.AXPORT_widget._axport_semiconductor_widgets.sx_widgets.weather import build_report, validate_report

ROOT = Path(__file__).resolve().parent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--month', type=int, required=True)
    args = parser.parse_args(argv)
    load_root_env(ROOT)
    key = os.getenv('CUSTOMS_API_KEY', '').strip()
    if not key:
        print('프로젝트 최상위 .env에 CUSTOMS_API_KEY를 설정하세요.')
        return 1
    print(f'{args.year}년 및 {args.year - 1}년 1~{args.month}월 누계 조회 중…')
    try:
        report = build_report(key=key, year=args.year, month=args.month)
        validate_report(report)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        output = ROOT / f'axport_weather_{args.year}{args.month:02}_{stamp}.json'
        with output.open('x', encoding='utf-8') as file:
            json.dump(report, file, ensure_ascii=False, indent=2, allow_nan=False)
    except Exception as error:
        # Upstream exception strings can contain the service key.
        print(f'수집·검증·저장 실패 ({type(error).__name__}). 승인, 호출 한도, 기간, 파일 권한을 확인하세요.')
        return 1
    print(f'생성 완료. .env에 반영 후 서버를 재시작하세요.\nAXPORT_WEATHER_JSON={output.as_posix()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
