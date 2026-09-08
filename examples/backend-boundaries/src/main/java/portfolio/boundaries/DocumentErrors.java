package portfolio.boundaries;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public final class DocumentErrors {
    public record ErrorBody(String code) {}

    @ExceptionHandler(DocumentStorage.Failure.class)
    public ResponseEntity<ErrorBody> storage(DocumentStorage.Failure failure) {
        // Storage DENIED means this backend cannot read its provider, not caller denial.
        return switch (failure.kind()) {
            case MISSING -> response(404, "DOCUMENT_MISSING");
            case DENIED -> response(502, "STORAGE_ACCESS_FAILED");
            case TRANSIENT -> response(503, "STORAGE_TEMPORARILY_UNAVAILABLE");
            case AMBIGUOUS -> response(502, "STORAGE_RESULT_UNKNOWN");
        };
    }

    @ExceptionHandler(DocumentController.RequestFailure.class)
    public ResponseEntity<ErrorBody> request(DocumentController.RequestFailure failure) {
        return response(failure.status, failure.code);
    }

    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<ErrorBody> unexpected(RuntimeException failure) {
        return response(500, "INTERNAL_FAILURE");
    }

    private ResponseEntity<ErrorBody> response(int status, String code) {
        // Do not serialize exception messages, causes, paths or provider response bodies.
        return ResponseEntity.status(status).contentType(MediaType.APPLICATION_JSON)
                .body(new ErrorBody(code));
    }
}
