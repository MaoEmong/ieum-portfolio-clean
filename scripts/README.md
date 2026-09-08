# PDF 생성과 공개 범위 검사

완성 PDF: [`output/pdf/ieum-v1-portfolio.pdf`](../output/pdf/ieum-v1-portfolio.pdf). A4 세로 5페이지이며 백엔드 개요, 오류 계약, 기동 검사, AI 협업 근거, 재현·검증 범위를 순서대로 읽도록 구성했습니다.

이 폴더의 Python은 포트폴리오 제작·검사용 보조 도구이며 실제 서비스 백엔드의 실행 언어가 아닙니다. 서비스 백엔드는 Java·Spring이고, 별도의 `red_green.py`도 포트폴리오 예제의 결함 검출 시연만 실행합니다.

## 재생성

Python 3.12와 Noto Sans KR의 TrueType 가변 서체가 필요합니다. [공식 Noto 프로젝트](https://github.com/notofonts/noto-cjk)에서 서체를 준비하세요. 서체 경로는 실행 인자로 전달하며 이 저장소에 서체 파일을 넣지 않습니다.

```sh
python -m pip install -r scripts/pdf-requirements.txt
python scripts/build_pdf.py --font /path/to/NotoSansKR-VF.ttf
python scripts/verify_pdf.py
```

`build_pdf.py`는 이 저장소의 합성 화면과 선별 내용만 읽습니다. 서비스 소스, 환경변수 파일, 로그인 계정, DB에 접근하지 않습니다. 중간 서체는 무시된 `tmp/pdfs/fonts/`에 생성합니다.

## 시각 검증

Poppler를 준비한 뒤 최신 PDF의 모든 페이지를 PNG로 렌더링합니다.

```sh
pdftoppm -r 120 -png output/pdf/ieum-v1-portfolio.pdf tmp/pdfs/page
```

모든 페이지의 한글·줄바꿈·겹침·여백·페이지 번호·화면 이미지를 직접 확인합니다. `verify_pdf.py`의 텍스트·폰트 검사는 레이아웃 검토를 대신하지 않습니다.

## 공개 범위 검사

```sh
python -m pip install -r scripts/check-requirements.txt
python -m unittest discover -s scripts/tests
python scripts/check_disclosure.py
python scripts/check_disclosure.py --history
```

허용 경로를 `disclosure-allowlist.txt`에 명시하며, 새 파일을 넣기 전 그 내용과 공개 의도를 사람이 먼저 검토해야 합니다. allowlist 변경 자체가 안전성을 보장하지 않습니다.

CI는 검사·예제 실행만 합니다. PDF는 검토한 산출물을 보관하며 CI에서 자동 재생성하거나 외부 호스팅하지 않습니다. public 전환도 자동화하지 않습니다.
