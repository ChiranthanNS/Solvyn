import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'google_auth_service.dart';

class ApiService {
  ApiService._privateConstructor();
  static final ApiService instance = ApiService._privateConstructor();

  static const String _baseUrl = "http://127.0.0.1:8000";
  static const String _tokenKey = "jwt_token";

  Future<void> saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
  }

  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  Future<void> clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
  }

  Future<Map<String, dynamic>?> post(
    String path, {
    Map<String, dynamic>? body,
    bool auth = false,
  }) async {
    final headers = <String, String>{
      "Content-Type": "application/json",
    };

    if (auth) {
      final token = await getToken();
      if (token != null) {
        headers["Authorization"] = "Bearer $token";
      }
    }

    try {
      final response = await http.post(
        Uri.parse("$_baseUrl$path"),
        headers: headers,
        body: jsonEncode(body ?? {}),
      );

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return jsonDecode(response.body);
      }

      print("POST $path failed [${response.statusCode}]: ${response.body}");
      return null;
    } catch (e) {
      print("POST $path error: $e");
      return null;
    }
  }

  Future<dynamic> get(
    String path, {
    bool auth = false,
  }) async {
    final headers = <String, String>{};

    if (auth) {
      final token = await getToken();
      if (token != null) {
        headers["Authorization"] = "Bearer $token";
      }
    }

    try {
      final response = await http.get(
        Uri.parse("$_baseUrl$path"),
        headers: headers,
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }

      print("GET $path failed [${response.statusCode}]: ${response.body}");
      return null;
    } catch (e) {
      print("GET $path error: $e");
      return null;
    }
  }

  Future<bool> login(String email, String password) async {
    final res = await post(
      "/auth/login",
      body: {
        "email": email,
        "password": password,
      },
    );

    final token = res?["access_token"];
    if (token != null) {
      await saveToken(token);
      return true;
    }

    return false;
  }

  Future<bool> signup(String name, String email, String password) async {
    final res = await post(
      "/auth/signup",
      body: {
        "name": name,
        "email": email,
        "password": password,
      },
    );

    return res != null;
  }

  Future<bool> loginWithGoogle() async {
    try {
      final result = await GoogleAuthService.signIn();

      if (result == null || !result.hasToken) {
        print("Google sign-in was cancelled or returned no token");
        return false;
      }

      Map<String, dynamic>? res;

      if (result.idToken != null) {
        print("Using idToken path");
        res = await post(
          "/auth/google",
          body: {"id_token": result.idToken},
        );
      }

      if ((res == null || res["access_token"] == null) && result.accessToken != null) {
        print("Falling back to accessToken path");
        res = await post(
          "/auth/google-token",
          body: {"access_token": result.accessToken},
        );
      }

      if (res == null || res["access_token"] == null) {
        print("Backend rejected Google token");
        return false;
      }

      await saveToken(res["access_token"]);
      return true;
    } catch (e) {
      print("Google login error: $e");
      return false;
    }
  }

  Future<List<dynamic>?> getDiaries() async {
    final result = await get("/diary", auth: true);
    return result as List<dynamic>?;
  }

  // Helper method used in some parts
  static Future<List<dynamic>> getDiary() async {
    final result = await instance.get("/diary", auth: true);
    return (result as List<dynamic>?) ?? [];
  }

  Future<bool> createDiary(String content) async {
    final res = await post(
      "/diary",
      body: {
        "content": content,
      },
      auth: true,
    );

    return res != null;
  }

  Future<String?> aiChat(String message) async {
    final res = await post(
      "/ai/chat",
      body: {
        "content": message,
      },
      auth: true,
    );

    return res?["reply"];
  }
}
