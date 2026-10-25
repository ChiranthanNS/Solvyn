import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_service.dart';

class AuthService {
  static Future<Map<String, dynamic>> register(String email, String password, {String? name}) async {
    final url = Uri.parse('${ApiService.baseUrl}/auth/register');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password, if (name != null) 'name': name}),
    );
    await ApiService.ensureSuccess(response, 'Registration failed.');
    if (response.statusCode == 200 || response.statusCode == 201) {
      return jsonDecode(response.body);
    }
    throw Exception('The authentication API returned an unexpected response.');
  }

  static Future<Map<String, dynamic>> login(String email, String password) async {
    final url = Uri.parse('${ApiService.baseUrl}/auth/login');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    await ApiService.ensureSuccess(response, 'Sign-in failed.');
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('The authentication API returned an unexpected response.');
  }

  static Future<Map<String, dynamic>> loginWithGoogle(String idToken) async {
    final url = Uri.parse('${ApiService.baseUrl}/auth/google');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'id_token': idToken}),
    );
    await ApiService.ensureSuccess(response, 'Google sign-in failed.');
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('The authentication API returned an unexpected response.');
  }

  static Future<Map<String, dynamic>> loginWithGoogleAccessToken(String accessToken) async {
    final url = Uri.parse('${ApiService.baseUrl}/auth/google-token');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'access_token': accessToken}),
    );
    await ApiService.ensureSuccess(response, 'Google sign-in failed.');
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('The authentication API returned an unexpected response.');
  }
}
