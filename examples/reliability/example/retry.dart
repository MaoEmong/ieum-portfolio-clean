import 'dart:io';

import 'package:reliability_examples/reliability_examples.dart';

Future<void> main() async {
  final policy = BoundedRetry();
  var attempts = 0;
  final result = await policy.run(
    () async {
      attempts++;
      if (attempts < 3) {
        throw const ReadFailure(ReadFailureKind.connectionInterrupted);
      }
      return 'synthetic read succeeded';
    },
    wait: (delay) async =>
        stdout.writeln('scheduled wait: ${delay.inMilliseconds} ms'),
  );
  stdout.writeln('$result; attempts: $attempts');

  final permanent = policy.delayAfter(
    const ReadFailure(ReadFailureKind.missingResource),
    retriesCompleted: 0,
  );
  stdout.writeln('missing resource: ${permanent == null ? "stop" : "retry"}');
}
