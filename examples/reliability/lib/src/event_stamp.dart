/// An instant and its original named-zone context, stored as separate facts.
///
/// No device-local timezone is consulted during serialization or restoration.
/// Zone validation is structural only: this example does not ship an IANA DB.
final class EventStamp {
  EventStamp({required DateTime instant, required String zoneId})
    : instant = _requireUtc(instant),
      zoneId = _requireZoneId(zoneId);

  final DateTime instant;
  final String zoneId;

  Map<String, Object> toJson() => {
    'version': 1,
    'instantUtc': instant.toIso8601String(),
    'zoneId': zoneId,
  };

  factory EventStamp.fromJson(Map<String, Object?> json) {
    if (json['version'] is! int || json['version'] != 1) {
      throw const FormatException('Unsupported event stamp version.');
    }
    final rawInstant = json['instantUtc'];
    final rawZone = json['zoneId'];
    if (rawInstant is! String || rawZone is! String) {
      throw const FormatException('instantUtc and zoneId must be strings.');
    }
    final parsed = DateTime.tryParse(rawInstant);
    // Canonical round-trip validation also rejects silently normalized dates.
    if (parsed == null ||
        !parsed.isUtc ||
        parsed.toIso8601String() != rawInstant) {
      throw const FormatException('Expected a canonical UTC timestamp.');
    }
    try {
      return EventStamp(instant: parsed, zoneId: rawZone);
    } on ArgumentError {
      throw const FormatException('Expected a named zone identifier.');
    }
  }

  static DateTime _requireUtc(DateTime value) {
    if (!value.isUtc) {
      throw ArgumentError.value(
        value,
        'instant',
        'An explicit UTC instant is required.',
      );
    }
    return value;
  }

  static String _requireZoneId(String value) {
    final namedZone = RegExp(
      r'^[A-Za-z][A-Za-z0-9_+-]*(/[A-Za-z][A-Za-z0-9_+-]*)+$',
    );
    if (value != 'UTC' && !namedZone.hasMatch(value)) {
      throw ArgumentError.value(value, 'zoneId', 'Use UTC or a named zone.');
    }
    return value;
  }
}
