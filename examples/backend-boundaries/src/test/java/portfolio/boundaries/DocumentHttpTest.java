package portfolio.boundaries;

import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class DocumentHttpTest {
    static MockMvc mvc(DocumentStorage storage, Object advice) {
        var catalog = Map.of("sample-note", new DocumentController.Reference("sample-owner", "synthetic-object"));
        return MockMvcBuilders.standaloneSetup(new DocumentController(catalog, storage))
                .setControllerAdvice(advice).build();
    }

    @Test
    void ownerReceivesTheExactStoredBytes() throws Exception {
        byte[] bytes = "synthetic document\nsecond line".getBytes(StandardCharsets.UTF_8);
        mvc(key -> {
            assertThat(key).isEqualTo("synthetic-object");
            return bytes;
        }, new DocumentErrors()).perform(get("/documents/sample-note").principal(() -> "sample-owner"))
                .andExpect(status().isOk()).andExpect(content().contentType("application/octet-stream"))
                .andExpect(content().bytes(bytes));
    }

    @ParameterizedTest
    @CsvSource({
        "MISSING,404,DOCUMENT_MISSING",
        "DENIED,502,STORAGE_ACCESS_FAILED",
        "TRANSIENT,503,STORAGE_TEMPORARILY_UNAVAILABLE",
        "AMBIGUOUS,502,STORAGE_RESULT_UNKNOWN"
    })
    void classifiesStorageEvidenceWithoutLeakingCause(DocumentStorage.FailureKind kind,
                                                      int expectedStatus, String expectedCode) throws Exception {
        var response = mvc(key -> {
            throw new DocumentStorage.Failure(kind, new IllegalStateException("synthetic-internal-detail"));
        }, new DocumentErrors()).perform(get("/documents/sample-note").principal(() -> "sample-owner"))
                .andExpect(status().is(expectedStatus)).andExpect(content().contentType("application/json"))
                .andExpect(jsonPath("$.code").value(expectedCode)).andReturn().getResponse();
        assertThat(response.getContentAsString()).isEqualTo("{\"code\":\"" + expectedCode + "\"}");
        assertThat(response.getContentAsString()).doesNotContain("synthetic-internal-detail", "cause", "stackTrace");
    }

    @Test
    void unexpectedFailureIsNotInventedAsMissing() throws Exception {
        mvc(key -> { throw new IllegalStateException("synthetic-internal-detail"); }, new DocumentErrors())
                .perform(get("/documents/sample-note").principal(() -> "sample-owner"))
                .andExpect(status().isInternalServerError())
                .andExpect(content().string("{\"code\":\"INTERNAL_FAILURE\"}"));
    }

    @ParameterizedTest
    @CsvSource({"sample-other,403,DOCUMENT_ACCESS_DENIED", "NONE,401,AUTHENTICATION_REQUIRED"})
    void callerBoundaryPrecedesStorage(String caller, int expectedStatus, String expectedCode) throws Exception {
        var calls = new AtomicInteger();
        var request = get("/documents/sample-note");
        if (!caller.equals("NONE")) request.principal(() -> caller);
        mvc(key -> { calls.incrementAndGet(); return new byte[]{1}; }, new DocumentErrors())
                .perform(request).andExpect(status().is(expectedStatus))
                .andExpect(jsonPath("$.code").value(expectedCode));
        assertThat(calls.get()).isZero();
    }

    @Test
    void absentCatalogReferenceDoesNotReadStorage() throws Exception {
        var calls = new AtomicInteger();
        mvc(key -> { calls.incrementAndGet(); return new byte[]{1}; }, new DocumentErrors())
                .perform(get("/documents/absent-note").principal(() -> "sample-owner"))
                .andExpect(status().isNotFound()).andExpect(jsonPath("$.code").value("DOCUMENT_MISSING"));
        assertThat(calls.get()).isZero();
    }
}
