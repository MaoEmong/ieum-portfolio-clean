package portfolio.boundaries;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import static org.assertj.core.api.Assertions.assertThat;

class StartupBoundaryTest {
    static ApplicationContextRunner context(String... properties) {
        return new ApplicationContextRunner().withUserConfiguration(StartupBoundary.class)
                .withPropertyValues(properties);
    }

    @ParameterizedTest
    @CsvSource({"true,DURABLE", "false,EPHEMERAL", "true,EPHEMERAL"})
    void unsafeProductionFailsDuringContextStartup(boolean developerAuth, String storage) {
        context("sample.stage=PROD", "sample.developer-auth=" + developerAuth, "sample.storage=" + storage)
                .run(ctx -> {
                    assertThat(ctx).hasFailed();
                    assertThat(ctx.getStartupFailure()).hasRootCauseInstanceOf(IllegalStateException.class)
                            .hasRootCauseMessage(developerAuth
                                    ? "Production cannot enable developer authentication"
                                    : "Production requires durable storage");
                });
    }

    @ParameterizedTest
    @CsvSource({"DEV,true,EPHEMERAL", "DEV,false,DURABLE", "PROD,false,DURABLE"})
    void explicitlySupportedConfigurationsStart(String stage, boolean developerAuth, String storage) {
        context("sample.stage=" + stage, "sample.developer-auth=" + developerAuth, "sample.storage=" + storage)
                .run(ctx -> {
                    assertThat(ctx).hasNotFailed().hasSingleBean(StartupBoundary.Settings.class);
                    assertThat(ctx.getBean(StartupBoundary.Settings.class).stage().name()).isEqualTo(stage);
                    assertThat(ctx).hasBean("rejectUnsafeProduction");
                });
    }

    @ParameterizedTest
    @CsvSource({"sample.stage=UNKNOWN", "sample.storage=UNKNOWN", "sample.developer-auth=perhaps"})
    void invalidConfigurationCannotSilentlyFallBack(String malformed) {
        context("sample.stage=PROD", "sample.storage=DURABLE", "sample.developer-auth=false", malformed)
                .run(ctx -> assertThat(ctx).hasFailed());
    }

    @Test
    void missingStageFailsClosed() {
        context("sample.storage=DURABLE").run(ctx -> assertThat(ctx).hasFailed());
    }

    @Test
    void missingStorageModeFailsClosed() {
        context("sample.stage=PROD").run(ctx -> assertThat(ctx).hasFailed());
    }
}
