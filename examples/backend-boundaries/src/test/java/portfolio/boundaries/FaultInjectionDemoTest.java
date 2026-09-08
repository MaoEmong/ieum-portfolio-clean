package portfolio.boundaries;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Deliberate teaching defects, created for this example; not a historical service revision. */
@EnabledIfSystemProperty(named = "sample.faultDemo", matches = "true")
class FaultInjectionDemoTest {
    private final boolean inject = Boolean.getBoolean("sample.injectFault");

    @Test
    void transientReadMustRemain503() throws Exception {
        Object advice = inject ? new DeliberatelyBrokenAdvice() : new DocumentErrors();
        DocumentHttpTest.mvc(key -> {
            throw new DocumentStorage.Failure(DocumentStorage.FailureKind.TRANSIENT,
                    new IllegalStateException("synthetic failure"));
        }, advice).perform(get("/documents/sample-note").principal(() -> "sample-owner"))
                .andExpect(status().isServiceUnavailable());
    }

    @Test
    void productionDeveloperAuthenticationMustPreventStartup() {
        Class<?> configuration = inject ? DeliberatelyUnguarded.class : StartupBoundary.class;
        new ApplicationContextRunner().withUserConfiguration(configuration)
                .withPropertyValues("sample.stage=PROD", "sample.developer-auth=true", "sample.storage=DURABLE")
                .run(ctx -> assertThat(ctx.getStartupFailure())
                        .as("production must reject developer authentication")
                        .hasRootCauseInstanceOf(IllegalStateException.class)
                        .hasRootCauseMessage("Production cannot enable developer authentication"));
    }

    @RestControllerAdvice
    static class DeliberatelyBrokenAdvice {
        @ExceptionHandler(DocumentStorage.Failure.class)
        ResponseEntity<Void> everyStorageFailureIsMissing(DocumentStorage.Failure ignored) {
            return ResponseEntity.notFound().build();
        }
    }

    @Configuration(proxyBeanMethods = false)
    @EnableConfigurationProperties(StartupBoundary.Settings.class)
    static class DeliberatelyUnguarded {
        // Intentionally omitted guard: valid binding alone does not enforce environment policy.
    }
}
