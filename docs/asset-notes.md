# 이미지와 서체

## 화면 이미지

`assets/screens/`의 세 PNG는 이음 v1의 **실제 Flutter 화면 위젯을 합성 데이터로 렌더링**한 결과입니다. 실기기 촬영, 운영 데이터 화면, 새 디자인 제안 이미지가 아닙니다.

- 논리 크기 390 × 844, PNG 크기 780 × 1688.
- 현재 파란 주머니·C안 타이포와 앱에 포함된 Pretendard를 사용했습니다.
- 홈, 사람 상세, 월간 달력의 실제 위젯을 간소화한 테스트 라우터로 실행했습니다.
- 인물·소속·메모·기록·일정은 모두 이번 포트폴리오를 위해 새로 만든 예시입니다.
- 외부 API 전송을 차단한 캡처 테스트가 통과했고 API 전송 시도 0회를 확인했습니다.
- 기기 상태바, 계정 정보, 실제 음성·사진은 포함하지 않습니다.

운영 코드와 캡처용 테스트 도구는 이 저장소에 복사하지 않았습니다. 따라서 이 저장소만으로 화면 위젯 전체를 재실행할 수는 없습니다. Dart 예제의 실행 가능 범위와 구분합니다.

## 브랜드 이미지

`assets/brand/pocket-blue.png`는 이음에서 사용 중인 파란 기억 주머니의 기존 Android 런처용 생성 자산입니다. AI 이미지 도구로 제작한 승인 시안에서 생성된 파일을 그대로 사용했습니다. 제작 메타데이터가 포함된 고해상도 원본은 이 저장소에 넣지 않았습니다. `assets/cover.svg`는 이 포트폴리오용 텍스트 배너입니다.

## 서체와 제3자 안내

- 화면: [Pretendard](https://github.com/orioncactus/pretendard), SIL Open Font License 1.1. [원문 라이선스](https://github.com/orioncactus/pretendard/blob/main/LICENSE).
- PDF: [Noto Sans KR](https://github.com/notofonts/noto-cjk), SIL Open Font License 1.1. [원문 라이선스](https://github.com/notofonts/noto-cjk/blob/main/Sans/LICENSE).
- 서체 파일 자체는 이 저장소에 배포하지 않습니다. PDF는 Noto Sans KR의 400·600 굵기를 정적으로 만든 서브셋을 포함합니다. 두 굵기가 같은 폰트로 합쳐지지 않도록 PDF 내부 파생 서체명은 `IeumPortfolioSans-Regular`와 `IeumPortfolioSans-SemiBold`로 구분했습니다. 서체의 원래 권리·라이선스 정보는 유지합니다.
- 외부 Dart 패키지는 `pubspec.lock`, Java 예제의 직접 의존성과 플러그인은 `pom.xml`에 기록합니다. Maven 전이 의존성은 해당 POM/BOM의 해석을 따르며 Dart lockfile과 같은 잠금 보장을 주장하지 않습니다. 각각의 권리는 해당 패키지 라이선스를 따릅니다.

이미지의 개인정보와 의미상 공개 범위는 육안으로 확인했습니다. 자동 메타데이터 검사만으로 이미지 내용의 안전성을 보증하지는 않습니다.
