import 'dart:convert';
import 'dart:io';

import 'package:reliability_examples/reliability_examples.dart';

void main() {
  // Synthetic dates: both have a wall-clock time of 01:30 in the same zone,
  // but the explicit offsets identify two different instants at a DST overlap.
  final earlier = EventStamp(
    instant: DateTime.parse('2030-11-03T01:30:00-04:00'),
    zoneId: 'America/New_York',
  );
  final later = EventStamp(
    instant: DateTime.parse('2030-11-03T01:30:00-05:00'),
    zoneId: 'America/New_York',
  );
  final serialized = jsonEncode(earlier.toJson());
  final restored = EventStamp.fromJson(
    jsonDecode(serialized) as Map<String, Object?>,
  );
  stdout.writeln(serialized);
  stdout.writeln('restored zone: ${restored.zoneId}');
  stdout.writeln(
    'difference between explicit instants: ${later.instant.difference(restored.instant).inMinutes} minutes',
  );
}
