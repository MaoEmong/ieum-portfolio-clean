import 'dart:io';

import 'event_time.dart' as event_time;
import 'retry.dart' as retry;

Future<void> main() async {
  stdout.writeln('== Bounded retry ==');
  await retry.main();
  stdout.writeln('\n== UTC and zone persistence ==');
  event_time.main();
}
