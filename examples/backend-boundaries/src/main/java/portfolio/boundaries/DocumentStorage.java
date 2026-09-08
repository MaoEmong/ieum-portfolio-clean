package portfolio.boundaries;

/** The adapter must classify evidence, not guess that every failed read is missing. */
public interface DocumentStorage {
    byte[] read(String objectKey);

    enum FailureKind { MISSING, DENIED, TRANSIENT, AMBIGUOUS }

    final class Failure extends RuntimeException {
        private final FailureKind kind;

        public Failure(FailureKind kind, Throwable internalCause) {
            super("Document storage failed", internalCause);
            this.kind = java.util.Objects.requireNonNull(kind);
        }

        public FailureKind kind() {
            return kind;
        }
    }
}
