import 'dart:convert';

import 'package:reliability_examples/reliability_examples.dart';
import 'package:test/test.dart';

void main() {
  Map<String, Object?> validJson() => {
    'version': 1,
    'instantUtc': '2030-06-15T06:00:00.000Z',
    'zoneId': 'Asia/Tokyo',
  };

  test('JSON round trip preserves both the instant and source zone', () {
    final stamp = EventStamp(
      instant: DateTime.parse('2030-06-15T15:00:00+09:00'),
      zoneId: 'Asia/Tokyo',
    );
    final encoded = jsonEncode(stamp.toJson());
    final restored = EventStamp.fromJson(
      jsonDecode(encoded) as Map<String, Object?>,
    );
    expect(restored.instant, DateTime.utc(2030, 6, 15, 6));
    expect(restored.instant.isUtc, isTrue);
    expect(restored.zoneId, 'Asia/Tokyo');
    expect(restored.toJson(), validJson());
  });

  test('two explicit offsets keep repeated wall-clock times distinct', () {
    final first = EventStamp(
      instant: DateTime.parse('2030-11-03T01:30:00-04:00'),
      zoneId: 'America/New_York',
    );
    final second = EventStamp(
      instant: DateTime.parse('2030-11-03T01:30:00-05:00'),
      zoneId: 'America/New_York',
    );
    expect(second.instant.difference(first.instant), const Duration(hours: 1));
    expect(first.zoneId, second.zoneId);
    expect(first.toJson()['instantUtc'], isNot(second.toJson()['instantUtc']));
  });

  test('microsecond precision survives persistence', () {
    final instant = DateTime.utc(2030, 6, 15, 6, 0, 0, 123, 456);
    final stamp = EventStamp(instant: instant, zoneId: 'UTC');
    expect(EventStamp.fromJson(stamp.toJson()).instant, instant);
  });

  test('leap day is preserved without device-local interpretation', () {
    final stamp = EventStamp(
      instant: DateTime.utc(2032, 2, 29, 23, 59),
      zoneId: 'UTC',
    );
    expect(
      EventStamp.fromJson(stamp.toJson()).instant,
      DateTime.utc(2032, 2, 29, 23, 59),
    );
  });

  test('local DateTime must be explicitly resolved before construction', () {
    expect(
      () => EventStamp(instant: DateTime(2030, 6, 15), zoneId: 'UTC'),
      throwsArgumentError,
    );
  });

  for (final value in ['', '   ', '+09:00', 'Tokyo', '../UTC', 'Asia/Tokyo ']) {
    test('invalid zone shape "$value" is rejected', () {
      expect(
        () => EventStamp(instant: DateTime.utc(2030), zoneId: value),
        throwsArgumentError,
      );
      expect(
        () => EventStamp.fromJson({...validJson(), 'zoneId': value}),
        throwsFormatException,
      );
    });
  }

  for (final value in [
    '2030-06-15T06:00:00.000',
    '2030-06-15T15:00:00.000+09:00',
    '2030-02-30T06:00:00.000Z',
    '2030-06-15T24:00:00.000Z',
    'not-a-date',
  ]) {
    test(
      'invalid or noncanonical persisted timestamp "$value" is rejected',
      () {
        expect(
          () => EventStamp.fromJson({...validJson(), 'instantUtc': value}),
          throwsFormatException,
        );
      },
    );
  }

  test('missing fields and wrong field types are rejected', () {
    for (final json in <Map<String, Object?>>[
      {},
      {...validJson()}..remove('zoneId'),
      {...validJson(), 'instantUtc': 123},
      {...validJson(), 'zoneId': null},
    ]) {
      expect(() => EventStamp.fromJson(json), throwsFormatException);
    }
  });

  test('unknown schema versions are rejected', () {
    expect(
      () => EventStamp.fromJson({...validJson(), 'version': 2}),
      throwsFormatException,
    );
  });

  test('schema version must be an integer', () {
    for (final version in <Object>['1', 1.0, true]) {
      expect(
        () => EventStamp.fromJson({...validJson(), 'version': version}),
        throwsFormatException,
      );
    }
  });

  test('additional fields do not alter known time fields', () {
    final stamp = EventStamp.fromJson({
      ...validJson(),
      'syntheticNote': 'ignored',
    });
    expect(stamp.toJson(), validJson());
  });
}
