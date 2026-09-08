import 'dart:async';

/// Explicit failure categories for a read-only operation.
enum ReadFailureKind {
  connectionInterrupted,
  serviceUnavailable,
  throttled,
  credentialsPending,
  invalidRequest,
  accessDenied,
  missingResource,
}

final class ReadFailure implements Exception {
  const ReadFailure(this.kind);

  final ReadFailureKind kind;
}

/// A finite retry schedule. Attempt timeouts belong to the caller.
///
/// This policy is intended for reads or operations known to be idempotent.
/// Unknown exceptions stop immediately so caller mistakes are not hidden.
final class BoundedRetry {
  BoundedRetry({
    List<Duration> delays = const [
      Duration(milliseconds: 250),
      Duration(milliseconds: 750),
    ],
  }) : delays = List<Duration>.unmodifiable(delays) {
    if (this.delays.any((delay) => delay <= Duration.zero)) {
      throw ArgumentError.value(delays, 'delays', 'Must be positive.');
    }
  }

  final List<Duration> delays;

  Duration get maximumScheduledWait =>
      delays.fold(Duration.zero, (total, delay) => total + delay);

  /// [retriesCompleted] is zero after the initial operation fails.
  Duration? delayAfter(Object failure, {required int retriesCompleted}) {
    if (retriesCompleted < 0) {
      throw RangeError.range(retriesCompleted, 0, null, 'retriesCompleted');
    }
    if (retriesCompleted >= delays.length || failure is! ReadFailure) {
      return null;
    }
    return switch (failure.kind) {
      ReadFailureKind.connectionInterrupted ||
      ReadFailureKind.serviceUnavailable ||
      ReadFailureKind.throttled ||
      ReadFailureKind.credentialsPending => delays[retriesCompleted],
      ReadFailureKind.invalidRequest ||
      ReadFailureKind.accessDenied ||
      ReadFailureKind.missingResource => null,
    };
  }

  /// Executes at most `delays.length + 1` calls.
  ///
  /// [wait] is injectable so tests and the CLI do not need wall-clock sleeps.
  Future<T> run<T>(
    Future<T> Function() read, {
    Future<void> Function(Duration) wait = Future<void>.delayed,
  }) async {
    var retriesCompleted = 0;
    while (true) {
      try {
        return await read();
      } catch (failure) {
        final delay = delayAfter(failure, retriesCompleted: retriesCompleted);
        if (delay == null) rethrow;
        await wait(delay);
        retriesCompleted++;
      }
    }
  }
}
