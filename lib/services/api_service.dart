import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  // Override per build, for example:
  // flutter run --dart-define=SOLVYN_API_URL=https://your-api.example
  static const String baseUrl = String.fromEnvironment(
    'SOLVYN_API_URL',
    defaultValue: 'http://127.0.0.1:5000',
  );

  static Future<Map<String, String>> getHeaders() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }
}
