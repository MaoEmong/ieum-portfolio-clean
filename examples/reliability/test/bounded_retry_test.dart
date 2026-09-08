import 'package:reliability_examples/reliability_examples.dart';
import 'package:test/test.dart';

void main() {
  group('classification and bounds', () {
    final policy = BoundedRetry();

    for (final kind in [
      ReadFailureKind.connectionInterrupted,
      ReadFailureKind.serviceUnavailable,
      ReadFailureKind.throttled,
      ReadFailureKind.credentialsPending,
    ]) {
      test('$kind retries twice and then stops', () {
        final failure = ReadFailure(kind);
        expect(
          policy.delayAfter(failure, retriesCompleted: 0),
          const Duration(milliseconds: 250),
        );
        expect(
          policy.delayAfter(failure, retriesCompleted: 1),
          const Duration(milliseconds: 750),
        );
        expect(policy.delayAfter(failure, retriesCompleted: 2), isNull);
        expect(policy.delayAfter(failure, retriesCompleted: 100), isNull);
      });
    }

    for (final kind in [
      ReadFailureKind.invalidRequest,
      ReadFailureKind.accessDenied,
      ReadFailureKind.missingResource,
    ]) {
      test('$kind stops on the first failure', () {
        expect(
          policy.delayAfter(ReadFailure(kind), retriesCompleted: 0),
          isNull,
        );
      });
    }

    test('unknown exceptions and programming errors stop', () {
      expect(
        policy.delayAfter(Exception('synthetic'), retriesCompleted: 0),
        isNull,
      );
      expect(
        policy.delayAfter(StateError('synthetic'), retriesCompleted: 0),
        isNull,
      );
    });

    test('negative retry counts are rejected', () {
      expect(
        () => policy.delayAfter(
          const ReadFailure(ReadFailureKind.throttled),
          retriesCompleted: -1,
        ),
        throwsRangeError,
      );
    });

    test('scheduled wait has an explicit total', () {
      expect(policy.maximumScheduledWait, const Duration(seconds: 1));
    });

    test('schedule is copied and cannot be mutated', () {
      final schedule = [const Duration(milliseconds: 10)];
      final custom = BoundedRetry(delays: schedule);
      schedule.clear();
      expect(custom.delays, [const Duration(milliseconds: 10)]);
      expect(() => custom.delays.clear(), throwsUnsupportedError);
    });

    test('zero and negative delays are rejected', () {
      expect(() => BoundedRetry(delays: [Duration.zero]), throwsArgumentError);
      expect(
        () => BoundedRetry(delays: [const Duration(milliseconds: -1)]),
        throwsArgumentError,
      );
    });
  });

  group('execution', () {
    test('immediate success does not schedule a wait', () async {
      final waits = <Duration>[];
      final result = await BoundedRetry().run(
        () async => 42,
        wait: (delay) async {
          waits.add(delay);
        },
      );
      expect(result, 42);
      expect(waits, isEmpty);
    });

    test('transient failures recover on the third call', () async {
      var calls = 0;
      final waits = <Duration>[];
      final result = await BoundedRetry().run(
        () async {
          calls++;
          if (calls < 3)
            throw const ReadFailure(ReadFailureKind.serviceUnavailable);
          return 'ready';
        },
        wait: (delay) async {
          waits.add(delay);
        },
      );
      expect(result, 'ready');
      expect(calls, 3);
      expect(waits, [
        const Duration(milliseconds: 250),
        const Duration(milliseconds: 750),
      ]);
    });

    test('exhaustion rethrows the original final failure', () async {
      const failure = ReadFailure(ReadFailureKind.connectionInterrupted);
      var calls = 0;
      final waits = <Duration>[];
      await expectLater(
        BoundedRetry().run<int>(
          () async {
            calls++;
            throw failure;
          },
          wait: (delay) async {
            waits.add(delay);
          },
        ),
        throwsA(same(failure)),
      );
      expect(calls, 3);
      expect(waits.length, 2);
    });

    test('a permanent failure after a retry stops immediately', () async {
      var calls = 0;
      final waits = <Duration>[];
      const permanent = ReadFailure(ReadFailureKind.accessDenied);
      await expectLater(
        BoundedRetry().run<int>(
          () async {
            calls++;
            if (calls == 1)
              throw const ReadFailure(ReadFailureKind.credentialsPending);
            throw permanent;
          },
          wait: (delay) async {
            waits.add(delay);
          },
        ),
        throwsA(same(permanent)),
      );
      expect(calls, 2);
      expect(waits.length, 1);
    });

    test('an empty schedule permits only the initial call', () async {
      var calls = 0;
      await expectLater(
        BoundedRetry(delays: []).run<int>(() async {
          calls++;
          throw const ReadFailure(ReadFailureKind.throttled);
        }),
        throwsA(isA<ReadFailure>()),
      );
      expect(calls, 1);
    });

    test('a wait failure is propagated without another operation', () async {
      var calls = 0;
      final cancelled = StateError('synthetic wait cancellation');
      await expectLater(
        BoundedRetry().run<int>(
          () async {
            calls++;
            throw const ReadFailure(ReadFailureKind.throttled);
          },
          wait: (_) async {
            throw cancelled;
          },
        ),
        throwsA(same(cancelled)),
      );
      expect(calls, 1);
    });
  });
}
