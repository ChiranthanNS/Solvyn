import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_service.dart';
import '../models/chat_message.dart';

class ChatService {
  static Future<List<ChatMessage>> getHistory() async {
    final url = Uri.parse('${ApiService.baseUrl}/ai/chat/history');
    final headers = await ApiService.getHeaders();
    final response = await http.get(url, headers: headers);
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => ChatMessage.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load chat history');
    }
  }

  static Future<Map<String, dynamic>> sendMessage(String content) async {
    final url = Uri.parse('${ApiService.baseUrl}/ai/chat');
    final headers = await ApiService.getHeaders();
    final response = await http.post(url, headers: headers, body: jsonEncode({'content': content}));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to send message');
    }
  }
}
