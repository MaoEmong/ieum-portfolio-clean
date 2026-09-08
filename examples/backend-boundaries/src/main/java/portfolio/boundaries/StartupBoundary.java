package portfolio.boundaries;

import org.springframework.beans.factory.InitializingBean;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(StartupBoundary.Settings.class)
public class StartupBoundary {
    public enum Stage { DEV, PROD }
    public enum StorageMode { EPHEMERAL, DURABLE }

    @ConfigurationProperties("sample")
    public record Settings(Stage stage, boolean developerAuth, StorageMode storage) {
        public Settings {
            if (stage == null || storage == null) {
                throw new IllegalArgumentException("sample.stage and sample.storage are required");
            }
        }
    }

    @Bean
    InitializingBean rejectUnsafeProduction(Settings settings) {
        return () -> {
            if (settings.stage() == Stage.PROD && settings.developerAuth()) {
                throw new IllegalStateException("Production cannot enable developer authentication");
            }
            if (settings.stage() == Stage.PROD && settings.storage() == StorageMode.EPHEMERAL) {
                throw new IllegalStateException("Production requires durable storage");
            }
        };
    }
}
