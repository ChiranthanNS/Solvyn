import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  // Override per build, for example:
  // flutter run --dart-define=SOLVYN_API_URL=https://your-api.example
  static const String _configuredBaseUrl = String.fromEnvironment(
    'SOLVYN_API_URL',
  );

  static String get baseUrl {
    if (_configuredBaseUrl.isNotEmpty) return _configuredBaseUrl;
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:5000';
    }
    return 'http://127.0.0.1:5000';
  }

  static Future<void> Function()? onSessionExpired;

  static Future<void> ensureSuccess(
    http.Response response,
    String fallback, {
    Set<int> acceptedStatusCodes = const {},
  }) async {
    if ((response.statusCode >= 200 && response.statusCode < 300) ||
        acceptedStatusCodes.contains(response.statusCode)) {
      return;
    }
    if (response.statusCode == 401) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('auth_token');
      await onSessionExpired?.call();
    }
    var message = fallback;
    try {
      final payload = jsonDecode(response.body);
      if (payload is Map && payload['detail'] is String) {
        message = payload['detail'] as String;
      }
    } catch (_) {
      // Keep the safe operation-specific message when the API has no JSON body.
    }
    throw Exception('$message (HTTP ${response.statusCode})');
  }

  static Future<Map<String, String>> getHeaders() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }
}
