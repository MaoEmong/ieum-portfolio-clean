package portfolio.boundaries;

import java.security.Principal;
import java.util.Map;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

@RestController
public final class DocumentController {
    public record Reference(String owner, String objectKey) {}

    private final Map<String, Reference> catalog;
    private final DocumentStorage storage;

    public DocumentController(Map<String, Reference> catalog, DocumentStorage storage) {
        this.catalog = Map.copyOf(catalog);
        this.storage = storage;
    }

    @GetMapping(value = "/documents/{id}", produces = MediaType.APPLICATION_OCTET_STREAM_VALUE)
    public byte[] read(@PathVariable("id") String id, Principal principal) {
        // Principal must already be authenticated upstream; never accept an owner header.
        if (principal == null) throw new RequestFailure(401, "AUTHENTICATION_REQUIRED");
        Reference reference = catalog.get(id);
        if (reference == null) throw new RequestFailure(404, "DOCUMENT_MISSING");
        if (!reference.owner().equals(principal.getName())) {
            throw new RequestFailure(403, "DOCUMENT_ACCESS_DENIED");
        }
        return storage.read(reference.objectKey());
    }

    static final class RequestFailure extends RuntimeException {
        final int status;
        final String code;

        RequestFailure(int status, String code) {
            this.status = status;
            this.code = code;
        }
    }
}
