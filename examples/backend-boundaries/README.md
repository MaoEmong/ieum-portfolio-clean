# 실패를 사실대로 분류하고 잘못된 환경 설정을 시작 전에 막기

Java 21 · Spring Boot 3.5.16으로 새로 작성한 독립 예제입니다. 비공개 서비스의 파일 저장 오류 분류와 환경 격리라는 일반적인 설계 판단을 재구성했습니다. 실제 서비스 코드의 발췌·축소 실행본이나 당시 수정 전후의 커밋이 아닙니다.

실제 서비스의 Spring Boot 4 구성과 달리 이 예제는 Spring Boot 3.5 계열을 선택했습니다. 저장소 어댑터, 응답 형식, 설정 이름과 테스트 구성을 새로 만들었습니다. 실제 서비스의 패키지 이름, 설정, 연결 주소, 데이터와 핵심 구현은 포함하지 않습니다. 소유자별 접근 경계는 설명을 위해 추가한 예제이며 원래 저장소 단위 테스트의 내용을 그대로 옮긴 것이 아닙니다.

## 실행

JDK 21, Maven 3.9.16을 준비합니다. Wrapper 바이너리는 포함하지 않습니다.

```sh
cd examples/backend-boundaries
mvn --batch-mode --no-transfer-progress test
python scripts/red_green.py
```

Windows에서 Maven이 PATH에 없으면 `python scripts/red_green.py --maven "설치폴더/bin/mvn.cmd"`처럼 경로를 지정합니다. Python은 결함 주입 데모에만 필요하며 표준 라이브러리만 사용합니다. 최초 실행은 Maven Central에서 공개 의존성을 받습니다. 테스트는 외부 DB·저장소·계정·비밀키·Docker를 사용하지 않고 서버 포트를 열지 않습니다. 이 프로젝트는 테스트로 실행하는 예제이며 실제 서비스를 시작하는 실행 파일은 제공하지 않습니다.

2026-09-08, Temurin JDK 21.0.10 + Maven 3.9.16에서 정상 테스트 **20개 통과, 데모 2개 조건부 스킵**을 확인했습니다. 별도 결함 주입은 기대한 계약 실패 2개를 확인한 뒤 정상 구현에서 같은 계약 2개가 통과했습니다. 이 수치는 실제 서비스의 테스트 수와 별개입니다.

## 1. 파일 부재와 저장소 장애는 다른 실패

`DocumentStorage`는 저장소가 확인한 결과를 네 가지로 분류합니다. 어댑터가 파일 부재를 확정한 경우에만 `MISSING`을 사용해야 합니다. 이 예제는 실제 저장소 SDK의 응답을 판별하는 어댑터를 포함하지 않습니다.

| 저장소 결과 | HTTP | 공개 코드 |
|---|---|---|
| 확정된 원본 부재 | 404 | `DOCUMENT_MISSING` |
| 백엔드의 저장소 접근 거부 | 502 | `STORAGE_ACCESS_FAILED` |
| 일시 장애 | 503 | `STORAGE_TEMPORARILY_UNAVAILABLE` |
| 원인을 확정하지 못함 | 502 | `STORAGE_RESULT_UNKNOWN` |

백엔드가 저장소에서 접근을 거절당한 것은 앱 사용자의 접근 권한 부족과 구분합니다. 원인을 모르는 일반 실행 예외는 500이며 파일 없음으로 바꾸지 않습니다. 응답에는 안정된 코드만 넣고 예외 메시지·원인·저장 키를 직렬화하지 않습니다. 응답 매핑은 이 예제의 계약이며 모든 서비스에 적용해야 하는 표준을 주장하지 않습니다.

컨트롤러는 이미 인증된 `Principal`과 메모리의 소유자 정보를 비교한 뒤 저장소를 읽습니다. 다른 사용자는 403, 인증 주체가 없으면 401로 차단하며 저장소는 호출하지 않습니다. 목록에 참조가 없는 경우도 확인된 부재로 404를 반환합니다. 이 설계는 403과 404를 구분하므로 문서 존재 여부를 숨기는 정책은 구현하지 않습니다.

테스트는 실제 Spring MVC 요청 처리·컨트롤러·예외 처리·JSON 직렬화를 통과하는 `MockMvc`를 사용합니다. 합성 인증 주체와 저장소 대역을 주입하며 HTTP 소켓, JWT 검증, Spring Security 필터 체인, 실제 데이터베이스의 소유권 질의를 검증하지는 않습니다. 정상 소유자의 응답 바이트 일치, 오류 네 종류, 예상 밖 예외, 다른 사용자·미인증 차단, 참조 부재를 확인합니다.

## 2. 운영 모드의 개발 인증·임시 저장 설정을 거부

`StartupBoundary`는 Spring의 설정 바인딩과 빈 초기화 중 다음 조건을 검사합니다.

| 합성 설정 | 시작 결과 |
|---|---|
| DEV + 개발 인증 + 임시 저장 | 허용 |
| DEV + 일반 인증 + 영속 저장 | 허용 |
| PROD + 일반 인증 + 영속 저장 | 허용 |
| PROD + 개발 인증 | 실패 |
| PROD + 임시 저장 | 실패 |
| 단계·저장 방식 누락 또는 잘못된 값 | 실패 |

테스트는 실제 Spring ApplicationContext를 시작해 잘못된 조합의 시작 실패와 정상 dev/prod의 성공을 모두 확인합니다. `sample`로 시작하는 설정은 예제 전용입니다. 여기서 `DURABLE`은 선언된 모드일 뿐 실제 저장소의 영속성·접근 가능성을 보장하지 않습니다. 배포 시스템이 올바른 PROD 값을 제공하는지, 운영자가 DEV라고 잘못 선언했는지까지 탐지하는 코드는 아닙니다.

## 명시적 결함 주입 RED → GREEN

`scripts/red_green.py`는 같은 두 계약 테스트를 다음 구성으로 순서대로 실행합니다.

1. **RED:** 테스트 전용 예외 처리기가 모든 저장소 장애를 404로 바꾸고, 테스트 전용 context에서 시작 검사를 의도적으로 뺍니다. 503 계약과 운영 개발 인증 차단 계약이 각각 실패해야 합니다.
2. **GREEN:** 정상 `DocumentErrors`와 `StartupBoundary`로 같은 계약을 실행합니다. 둘 다 통과해야 합니다.

스크립트는 새 Surefire XML에서 정확한 테스트 이름, 실패·오류·스킵 개수와 기대한 단언 실패 원인을 확인합니다. 의존성 다운로드나 컴파일 실패를 RED 성공으로 인정하지 않습니다. 소스 파일을 변경하지 않으며, 결함 모델은 테스트 소스에만 있습니다. 기본 `mvn test`에서는 결함 데모 두 개가 스킵되고 정상 계약 테스트만 실행됩니다.

이것은 **이번 포트폴리오를 위해 만든 결함 검출 시연**입니다. 비공개 서비스의 역사적 수정 전 코드나 그때 실패했던 로그를 재현했다는 의미가 아닙니다. 시연 후 전체 정상 검증을 다시 하려면 `mvn test`를 실행합니다.

## 고정한 의존성과 근거

Spring Boot parent 3.5.16이 Spring MVC·테스트 라이브러리의 버전을 관리합니다. Compiler 3.16.0과 Surefire 3.6.0은 POM에서 별도로 고정했습니다. 다른 기본 Maven 플러그인은 고정된 parent가 관리합니다. Maven 실행 버전은 3.9.16으로 검증합니다.

- [Spring Boot 3.5 시스템 요구사항](https://docs.spring.io/spring-boot/3.5/system-requirements.html)
- [Spring MockMvc의 실제 검증 범위](https://docs.spring.io/spring-framework/reference/testing/mockmvc.html)
- [Maven 3.9.16 공식 배포](https://maven.apache.org/download.cgi)
- [Compiler 플러그인](https://maven.apache.org/plugins/maven-compiler-plugin/plugin-info.html)
- [Surefire 플러그인](https://maven.apache.org/surefire/maven-surefire-plugin/plugin-info.html)

이 예제의 통과 결과를 실제 서비스의 보안 감사, 전체 저장소 검증, 배포 성공이나 전체 앱 품질로 확대하지 않습니다.
