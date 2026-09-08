"""Build the curated five-page resume attachment; never reads service files."""

from __future__ import annotations

import argparse
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf/ieum-v1-portfolio.pdf"
W, H = A4
M = 42
CW = W - M * 2
INK = colors.HexColor("#223246")
MUTED = colors.HexColor("#607186")
BLUE = colors.HexColor("#3D658B")
PALE = colors.HexColor("#EDF2F7")
LINE = colors.HexColor("#DCE4EC")
WHITE = colors.white
REPO = "https://github.com/MaoEmong/ieum-portfolio-clean"


class Portfolio:
    def __init__(self, out: Path):
        out.parent.mkdir(parents=True, exist_ok=True)
        self.c = canvas.Canvas(str(out), pagesize=A4, pageCompression=1, invariant=1)
        self.c.setTitle("이음 v1 | 백엔드 구현과 AI 협업")
        self.c.setAuthor("MaoEmong")
        self.c.setSubject("Java·Spring 백엔드 구현, 회귀 검증과 AI 협업 근거")
        self.c.setCreator("IEUM portfolio builder")
        self.c.setKeywords("이음, Flutter, Spring, portfolio, v1")

    def para(self, text, x, top, width, size=10, color=INK, bold=False, max_h=None):
        style = ParagraphStyle(
            "p", fontName="KRB" if bold else "KR", fontSize=size,
            leading=size * 1.55, textColor=color, alignment=TA_LEFT,
            wordWrap="CJK", splitLongWords=True, spaceAfter=0,
        )
        p = Paragraph(text, style)
        _, height = p.wrap(width, H)
        if max_h is not None and height > max_h + .1:
            raise ValueError(f"Paragraph exceeded its layout slot: {height:.1f} > {max_h}")
        if top + height > H - 45:
            raise ValueError("Content overlaps the footer")
        p.drawOn(self.c, x, H - top - height)
        return top + height

    def text(self, value, x, top, size=10, color=INK, bold=False):
        self.c.setFillColor(color)
        self.c.setFont("KRB" if bold else "KR", size)
        self.c.drawString(x, H - top - size, value)

    def rect(self, x, top, width, height, fill=PALE, radius=8, stroke=None):
        self.c.setFillColor(fill)
        self.c.setStrokeColor(stroke or fill)
        self.c.roundRect(x, H - top - height, width, height, radius,
                         fill=1, stroke=bool(stroke))

    def line(self, x1, top1, x2, top2, color=LINE, width=.8):
        self.c.setStrokeColor(color)
        self.c.setLineWidth(width)
        self.c.line(x1, H - top1, x2, H - top2)

    def arrow(self, x1, top1, x2, top2):
        self.line(x1, top1, x2, top2, BLUE, 1)
        if top1 == top2:
            self.line(x2 - 4, top2 - 3, x2, top2, BLUE, 1)
            self.line(x2 - 4, top2 + 3, x2, top2, BLUE, 1)
        else:
            self.line(x2 - 3, top2 - 4, x2, top2, BLUE, 1)
            self.line(x2 + 3, top2 - 4, x2, top2, BLUE, 1)

    def image(self, path, x, top, width, height):
        self.c.drawImage(str(ROOT / path), x, H - top - height, width, height,
                         preserveAspectRatio=True, mask="auto", anchor="c")

    def start(self, number, section):
        self.text("IEUM  /  BACKEND ENGINEERING", M, 25, 8, BLUE, True)
        self.text(section, W - 167, 25, 8, MUTED)
        self.line(M, 45, W - M, 45)
        self.line(M, H - 36, W - M, H - 36)
        self.text("MaoEmong  ·  v1  ·  2026.09", M, H - 27, 7.5, MUTED)
        self.text(f"{number:02d} / 05", W - M - 39, H - 27, 7.5, MUTED)

    def end(self):
        self.c.showPage()

    def title(self, kicker, title, description):
        self.text(kicker, M, 66, 9, BLUE, True)
        self.para(title, M, 89, CW, 25, bold=True, max_h=40)
        self.para(description, M, 137, CW, 10.2, MUTED, max_h=49)

    def code(self, lines, top, label, size=9.3):
        height = 43 + len(lines) * 14
        self.rect(M, top, CW, height, colors.HexColor("#17283A"))
        self.text(label, M + 14, top + 10, 8, colors.HexColor("#AFC8E0"), True)
        self.c.setFont("Courier-Bold", size)
        self.c.setFillColor(WHITE)
        for n, value in enumerate(lines):
            if pdfmetrics.stringWidth(value, "Courier-Bold", size) > CW - 28:
                raise ValueError("Code line exceeds printable width")
            self.c.drawString(M + 14, H - top - 41 - n * 14, value)
        return top + height

    def cover(self):
        self.start(1, "01  BACKEND")
        self.title("JAVA / SPRING / AI-ASSISTED DEVELOPMENT", "이음 | 백엔드 개발",
                   "서버의 실패 처리와 환경 격리를 구현하고, AI 협업 과정을 코드·테스트·기록으로 연결합니다.")
        self.rect(M, 198, CW, 45)
        self.text("Java 21 · Spring · JPA · PostgreSQL · Flyway", M + 14, 211, 11, BLUE, True)
        self.text("서비스 흐름과 서버의 경계", M, 272, 14, bold=True)
        boxes = [("Flutter 앱", "입력·검수"), ("Spring API", "사용자별 접근"),
                 ("저장 인터페이스", "실패 의미 분류"), ("Private Storage", "원본 파일")]
        for n, (title, desc) in enumerate(boxes):
            x = M + n * 131
            self.rect(x, 300, 118, 60, WHITE, 6, LINE)
            self.text(title, x + 10, 312, 10, BLUE, True)
            self.text(desc, x + 10, 338, 8.5, MUTED)
            if n < 3:
                self.arrow(x + 120, 331, x + 128, 331)
        self.arrow(M + 190, 361, M + 190, 373)
        self.rect(M + 131, 375, 118, 27, WHITE, 5, LINE)
        self.text("PostgreSQL / JPA", M + 141, 381, 8.8, BLUE, True)
        self.text("검토할 구현", M, 412, 14, bold=True)
        self.para("<b>01. 파일 부재와 장애를 구분하는 오류 계약</b><br/>확정 부재만 404로 변환. 실패 종류·내부 정보 비노출·정상 바이트를 HTTP 계층에서 검사합니다.",
                  M, 450, CW, 10.5, max_h=58)
        self.line(M, 516, W - M, 516)
        self.para("<b>02. 위험한 배포 설정의 기동 차단</b><br/>개발 편의 기능은 유지하되 배포 환경에서는 거부. 실제 Spring 컨텍스트와 정상 대조군으로 확인합니다.",
                  M, 536, CW, 10.5, max_h=58)
        self.line(M, 602, W - M, 602)
        self.text("프로젝트와 역할", M, 625, 12, bold=True)
        self.para("사람별 기록과 확인한 약속을 연결하는 모바일 서비스입니다. 1인 주도로 요구사항·수정 승인·사용자 시나리오를 정하고 AI 코딩 에이전트를 분석·구현·테스트 실행에 활용했습니다.",
                  M, 655, CW - 99, 9.4, max_h=76)
        self.para("현재 경험 범위: Render·Supabase 스테이징, Flutter 앱. 외부 STT를 사용하며 AWS 운영·스토어 출시는 포함하지 않습니다.",
                  M, 730, CW - 99, 8.5, MUTED, max_h=46)
        self.image("assets/screens/01-home.png", W - M - 69, 623, 69, 149)
        self.text("합성 위젯 화면", W - M - 69, 775, 6.7, MUTED)
        self.end()

    def storage(self):
        self.start(2, "02  ERROR CONTRACT")
        self.title("CASE 01 / STORAGE → HTTP", "404로 숨기면 안 되는 장애",
                   "DB 참조가 남아 있어도 원본이 없을 수 있습니다. 반대로 읽기 실패가 곧 원본 유실을 뜻하지는 않습니다.")
        self.text("원인 분석과 선택", M, 202, 13, bold=True)
        self.para("서버 경로의 원본 부재와 일반 I/O 오류가 같은 실패로 전달됐습니다. 원본은 private 객체 저장소로 분리하고, 확정된 부재만 404로 매핑했습니다. 정확한 유실 시점까지 입증한 것은 아닙니다.",
                  M, 232, CW, 10, max_h=63)
        rows = [("모든 오류를 404로", "권한·연결 장애도 유실처럼 보이므로 채택하지 않음"),
                ("공급자 상태만 확인", "불명확한 404는 객체 부재로 단정할 수 없음"),
                ("의미가 확정된 부재만", "선택: 어댑터의 판정과 HTTP 응답을 분리")]
        for n, (label, detail) in enumerate(rows):
            top = 310 + n * 32
            self.text(label, M, top, 9.2, BLUE, True)
            self.text(detail, M + 135, top, 8.7)
        self.code([
            "return switch (failure.kind()) {",
            '    case MISSING -> response(404, "DOCUMENT_MISSING");',
            '    case DENIED -> response(502, "STORAGE_ACCESS_FAILED");',
            '    case TRANSIENT -> response(503, "STORAGE_TEMPORARILY_UNAVAILABLE");',
            '    case AMBIGUOUS -> response(502, "STORAGE_RESULT_UNKNOWN");',
            "};",
        ], 427, "PUBLIC EXAMPLE / DocumentErrors.java", 9.3)
        self.para("위 코드는 공개용 독립 예제의 발췌입니다. 실제 서비스는 확정 부재 외 오류를 500으로 유지했고, 예제의 502·503 세분화는 설명용 계약입니다.",
                  M, 562, CW, 8.7, MUTED, max_h=43)
        self.text("회귀 테스트가 확인하는 경계", M, 618, 12, bold=True)
        self.para("• MockMvc로 컨트롤러·예외 처리·JSON 응답까지 통과<br/>• 정상 바이트, 실패 종류별 상태·코드, 내부 원인 비노출<br/>• 예제의 미인증·다른 사용자 요청은 저장소 호출 전에 차단",
                  M, 648, CW, 9.5, max_h=58)
        self.para("당시 사후 기록: 신규 회귀 22개 중 6개가 기대 404·실제 500으로 실패. 수정 후 기존 저장소 검사와 함께 28개 통과. 서로 다른 검사 범위이며 오늘 예제 실행 결과와 구분합니다.",
                  M, 734, CW, 8.6, MUTED, max_h=45)
        self.end()

    def startup(self):
        self.start(3, "03  STARTUP GUARD")
        self.title("CASE 02 / CONFIGURATION → LIFECYCLE", "테스트가 가드를 실행했는가",
                   "위험한 배포 설정을 기동 단계에서 거부합니다. 설정값뿐 아니라 가드의 실제 실행까지 검사합니다.")
        self.code([
            "@Bean",
            "InitializingBean rejectUnsafeProduction(Settings settings) {",
            "    return () -> {",
            "        if (settings.stage() == Stage.PROD",
            "                && settings.developerAuth()) {",
            '            throw new IllegalStateException("...");',
            "        }",
            "        // Also reject EPHEMERAL storage in PROD.",
            "    };",
            "}",
        ], 207, "PUBLIC EXAMPLE / StartupBoundary.java / abbreviated")
        self.para("공개 예제의 축약 표현입니다. 운영 키·DB·실제 인증 구현은 없으며, DURABLE은 예제에 선언한 모드이지 실제 영속성 보증이 아닙니다.",
                  M, 404, CW, 8.7, MUTED, max_h=42)
        self.code([
            "assertThat(ctx).hasFailed();",
            "assertThat(ctx.getStartupFailure())",
            "    .hasRootCauseInstanceOf(IllegalStateException.class);",
            "// Positive control in supported DEV / PROD configurations:",
            'assertThat(ctx).hasNotFailed().hasBean("rejectUnsafeProduction");',
        ], 464, "TEST CONTRACT / abbreviated")
        self.text("당시 테스트에서 드러난 함정", M, 598, 12, bold=True)
        self.para("<b>설정 우선순위:</b> 테스트 입력이 앱 설정에 덮이면 위험 조건을 시험하지 않습니다.<br/><b>지연 초기화:</b> 가드 빈이 생성되지 않으면 검사 자체가 실행되지 않습니다.<br/><b>다른 기동 오류:</b> DB 배선 오류로 실패해도 가드가 작동한 것은 아닙니다.",
                  M, 629, CW, 9.5, max_h=79)
        self.para("대응: 의도한 입력과 실패의 최하위 원인을 확인하고, 정상 환경에서는 컨텍스트 활성·가드 빈 존재를 대조합니다. 공개 예제는 DB 없는 작은 컨텍스트로 정책 생명주기만 검사합니다.",
                  M, 738, CW, 8.6, MUTED, max_h=44)
        self.end()

    def collaboration(self):
        self.start(4, "04  AI COLLABORATION")
        self.title("REQUIREMENTS → IMPLEMENTATION → VERIFICATION", "AI 협업 기반의 개발과 검증",
                   "요구사항과 검증 범위를 정하고, AI를 원인 분석·구현·회귀 테스트 실행에 활용했습니다.")
        self.rect(M, 204, CW, 73)
        self.text("개발·배포 환경 분리 | 요구사항 요약", M + 14, 216, 8.5, BLUE, True)
        self.para("개발 환경에서는 SNS 로그인 없이 작업하고,<br/>배포 환경에서는 실제 인증·검증을 거친 뒤 배포하도록 흐름을 정했습니다.",
                  M + 14, 240, CW - 28, 10.2, bold=True, max_h=33)
        blocks = [
            ("01  주도자의 역할: 요구와 검증 범위 설정", "개발·배포 환경의 분리를 요구하고, 환경 상태를 제공하며 수정 범위를 승인했습니다. 실제 앱 사용 순서에 따른 시나리오 점검도 요청했습니다."),
            ("02  AI의 역할: 분석·구현·테스트 실행", "AI 코딩 도구로 잘못된 설정의 실패 조건을 재현하고, 저장소 오류 분류와 기동 검사를 구현·보완했습니다. 수정 후에는 관련 회귀 테스트를 실행했습니다."),
            ("03  확인한 결과: 실패 응답에서 회귀 검증까지", "파일 부재의 기대 응답 404와 실제 응답 500의 차이를 확인하고 수정했습니다. 당시 백엔드 전체 회귀 210개 통과 기록은 보관된 테스트 XML 집계와 대조했습니다."),
        ]
        for n, (label, body) in enumerate(blocks):
            top = 297 + n * 91
            self.text(label, M, top, 10.5, BLUE, True)
            self.para(body, M, top + 26, CW, 9.8, max_h=49)
            self.line(M, top + 78, W - M, top + 78)
        self.rect(M, 589, CW, 85)
        self.text("사용자 시나리오 기반 검증 | 요청 요약", M + 14, 600, 8.5, BLUE, True)
        self.para("기능별 성공 여부뿐 아니라 실제 사용 흐름을 따라 점검하도록 요청했습니다. 자동 테스트와 실기기 재시험의 범위를 구분해 결과를 정리했습니다.",
                  M + 14, 625, CW - 28, 10, max_h=38)
        self.para("실제 개발 대화와 2026-09-08 검증 기록을 바탕으로 다듬은 설명입니다. 직접 인용이나 당시 AI 답변의 재현은 아닙니다. 현재 독립 예제의 실행 결과는 과거 서비스 검증과 구분합니다.",
                  M, 694, CW, 8.8, MUTED, max_h=43)
        self.para("<b>근거 문서:</b> docs/ai-assisted-development.md<br/>docs/evidence/ai-collaboration-summary.md",
                  M, 751, CW, 8.5, BLUE, max_h=29)
        self.end()

    def evidence(self):
        self.start(5, "05  REPRODUCE")
        self.title("READ THE CODE / RUN THE CONTRACTS", "직접 실행하고 판단할 수 있게",
                   "서비스 전체를 복제하지 않고, 공개 가능한 두 경계를 작은 Spring 예제와 테스트로 검토할 수 있도록 구성했습니다.")
        self.code([
            "cd examples/backend-boundaries",
            "mvn --batch-mode verify",
            "# Optional: run the fault-detection demo",
            "python scripts/red_green.py",
        ], 209, "JAVA 21 + MAVEN / Optional Python verification helper")
        self.para("서비스 백엔드는 Java·Spring입니다. Python은 포트폴리오의 PDF 생성·검사와 결함 검출 시연을 돕는 도구입니다.",
                  M, 316, CW, 8.5, MUTED, max_h=27)
        self.text("읽을 코드와 테스트", M, 349, 13, bold=True)
        rows = [
            ("DocumentErrors", "실패 종류 → HTTP 상태·안정된 오류 코드"),
            ("DocumentHttpTest", "MockMvc 응답·정상 바이트·접근 차단"),
            ("StartupBoundaryTest", "실제 컨텍스트·실패 원인·정상 대조군"),
            ("red_green.py", "의도적 결함 2개 탐지 → 같은 정상 계약 통과"),
        ]
        for n, (name, detail) in enumerate(rows):
            top = 384 + n * 35
            self.text(name, M, top, 9.2, BLUE, True)
            self.text(detail, M + 170, top, 9)
        self.para("결함 주입은 이번 공개 예제를 위한 실험이며 과거 서비스 수정 전 코드가 아닙니다. MockMvc·작은 Spring 컨텍스트를 사용하고 실제 클라우드·DB·JWT·HTTP 소켓은 검증하지 않습니다.",
                  M, 524, CW, 8.8, MUTED, max_h=43)
        self.line(M, 580, W - M, 580)
        self.text("서비스 v1의 별도 검증 기록", M, 598, 12, bold=True)
        self.para("백엔드 210개 · 앱 834개 통과, 앱 조건부 스킵 17개는 별도 구분. 새 합성 사진 1개의 재배포 후 보존을 확인했습니다. 현재 공개 예제 테스트 수와 합산하지 않습니다.",
                  M, 629, CW, 9.4, max_h=46)
        self.para("미완료·미측정: 기존 누락 원본 복구, 실제 AI 정확도, AI 생성 코드 비율·시간 절감률, 최대 사용자 수, iOS·스토어 출시. 코드 이해와 실제 역할은 문서·테스트 및 면접 설명으로 함께 확인해야 합니다.",
                  M, 690, CW, 8.8, MUTED, max_h=44)
        self.text(REPO.removeprefix("https://"), M, 750, 10.5, BLUE, True)
        self.c.linkURL(REPO, (M, H - 770, W - M, H - 746), relative=0, thickness=0)
        self.text("현재 PRIVATE · 소유자 검토 후 공개 결정 · 외부 제출 전 링크 접근 확인", M, 775, 7.5, MUTED)
        self.end()

    def build(self):
        self.cover()
        self.storage()
        self.startup()
        self.collaboration()
        self.evidence()
        self.c.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, required=True,
                        help="Noto Sans KR TrueType variable font (not copied to the repository)")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    # Instantiation is a generated build intermediate, not a distributed font.
    from fontTools.ttLib import TTFont as FontToolsFont
    from fontTools.varLib.instancer import instantiateVariableFont
    font_dir = ROOT / "tmp/pdfs/fonts"
    font_dir.mkdir(parents=True, exist_ok=True)
    for name, weight in [("KR", 400), ("KRB", 600)]:
        font = FontToolsFont(args.font)
        if "fvar" in font:
            font = instantiateVariableFont(font, {"wght": weight}, inplace=True)
        # Some variable fonts lack a STAT name for intermediate weights. Assign
        # distinct derivative names so ReportLab cannot merge the two faces.
        style = "Regular" if weight == 400 else "SemiBold"
        names = {1: "IeumPortfolioSans", 2: style,
                 3: f"IeumPortfolioSans-{style}",
                 4: f"IeumPortfolioSans {style}",
                 6: f"IeumPortfolioSans-{style}",
                 16: "IeumPortfolioSans", 17: style}
        for record in font["name"].names:
            if record.nameID in names:
                record.string = names[record.nameID].encode(record.getEncoding())
        target = font_dir / f"{name}.ttf"
        font.save(target)
        font.close()
        pdfmetrics.registerFont(TTFont(name, str(target)))
    pdfmetrics.registerFontFamily("KR", normal="KR", bold="KRB", italic="KR", boldItalic="KRB")
    Portfolio(args.output).build()
    print(f"Built 5-page portfolio: {args.output.name}")


if __name__ == "__main__":
    main()
