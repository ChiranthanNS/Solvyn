import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';

class ChatService {
  static Future<String> sendMessage(String message) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString("token");

    if (token == null) {
      return "Error: User not logged in.";
    }

    final url = Uri.parse("${ApiConfig.baseUrl}/ai/chat");

    final response = await http.post(
      url,
      headers: {
        "Content-Type": "application/json",
        "token": token,
      },
      body: jsonEncode({"content": message}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data["reply"];
    } else {
      return "Server Error: ${response.body}";
    }
  }
}
